"""
Wi-Fi 快照采集脚本
按 AC 的管理 IP 采集 AP / 射频 / SSID / 终端，每台 AC 原子替换一次快照
单台 AC 内串行采集，多台 AC 之间并发采集
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Module.WlanAP import WlanAP
from Module.WlanRadio import WlanRadio
from Module.WlanSSID import WlanSSID
from Module.WlanClient import WlanClient
from utils.db_helper import DBHelper
from utils.db_queue import get_db_queue

logger = logging.getLogger(__name__)

# 多台 AC 并发上限 10；单台串行实测约 106 秒（AP 7 / 射频 14 / SSID 13 / 终端 72），超时给到 180 秒
AC_CONCURRENCY = 10
AC_TIMEOUT = 180


async def collect_single_ac(ac: dict):
    """串行采集单台 AC 下的 AP / 射频 / SSID / 终端，AP 取不到时直接返回 None"""
    ac_id = ac.get('ac_id')
    ip = ac.get('mgmt_ip')
    community = ac.get('community') or 'public'
    vendor = ac.get('vendor', 'huawei')

    aps = await WlanAP(ip, community, vendor, ac_id).getAPs()
    if aps is None:
        return None
    radios = await WlanRadio(ip, community, vendor, ac_id).getRadios()
    ssids = await WlanSSID(ip, community, vendor, ac_id).getSSIDs()
    clients = await WlanClient(ip, community, vendor, ac_id).getClients()

    return {
        'aps': aps,
        'radios': radios or [],
        'ssids': ssids or [],
        'clients': clients or [],
    }


async def collect_and_save_ac(ac: dict, semaphore: asyncio.Semaphore):
    """采集单台 AC 并替换快照，返回是否成功；失败只回写 last_status"""
    ac_id = ac.get('ac_id')
    ac_name = ac.get('ac_name')
    ip = ac.get('mgmt_ip')

    async with semaphore:
        try:
            result = await asyncio.wait_for(collect_single_ac(ac), timeout=AC_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"AC {ac_name}({ip}) 采集超时（{AC_TIMEOUT}秒）")
            result = None
        except Exception as e:
            logger.error(f"AC {ac_name}({ip}) 采集异常: {e}")
            result = None

    try:
        with DBHelper() as db:
            # 超时、认证失败、OID 无返回、厂商未支持都视为失败，保留旧快照
            if result is None:
                logger.warning(f"AC {ac_name}({ip}) 采集失败，vendor={ac.get('vendor')}，标记为 offline")
                db.update_wifi_ac_status(ac_id, 'offline')
                return False

            ok = db.replace_wifi_snapshot(
                ac_id,
                result['aps'],
                result['radios'],
                result['ssids'],
                result['clients'],
            )
            db.update_wifi_ac_status(ac_id, 'online' if ok else 'offline')
            return ok
    except Exception as e:
        logger.error(f"AC {ac_name}({ip}) 保存快照失败: {e}")
        return False


async def run():
    """
    主执行函数 - 采集所有 AC 的 Wi-Fi 快照
    注意：此函数不管理队列生命周期，由调用方负责
    """
    logger.info("开始执行Wi-Fi快照采集任务")
    start_time = asyncio.get_event_loop().time()

    try:
        with DBHelper() as db:
            ac_list = db.get_wifi_ac_list()

        logger.info(f"获取到 {len(ac_list)} 台AC（最大并发: {AC_CONCURRENCY}）")

        semaphore = asyncio.Semaphore(AC_CONCURRENCY)
        tasks = [collect_and_save_ac(ac, semaphore) for ac in ac_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_success = 0
        total_failed = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                total_failed += 1
                logger.error(f"AC {ac_list[i].get('mgmt_ip')} 采集异常: {result}")
            elif result:
                total_success += 1
            else:
                total_failed += 1

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        logger.info(f"Wi-Fi快照采集完成 - 成功: {total_success}, 失败: {total_failed}, 耗时: {elapsed:.2f}秒")

    except Exception as e:
        logger.error(f"Wi-Fi快照采集任务执行失败: {e}")


async def main():
    """独立运行时的入口函数，管理队列生命周期"""
    queue = get_db_queue()
    await queue.start()
    logger.info("数据库写入队列已启动")

    try:
        await run()
    finally:
        logger.info("等待队列处理完成...")
        await queue.stop()
        logger.info("数据库写入队列已停止")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
