"""
ARP 表采集脚本（仅IPv4）
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Module.ARP import ARPTable
from utils.db_helper import DBHelper

logger = logging.getLogger(__name__)


async def collect_single_device_arp(ip: str, community: str, sys_type: str):
    """采集单个设备的ARP表"""
    try:
        arp = ARPTable(ip, community, sys_type)
        arp_data = await arp.getARPs()
        return {
            'ip': ip,
            'arp': arp_data
        }
    except Exception as e:
        logger.error(f"采集设备 {ip} ARP表失败: {e}")
        return None


async def collect_and_save_batch(device_batch, batch_id):
    """采集一批设备并保存"""
    tasks = []
    for device in device_batch:
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')
        tasks.append(collect_single_device_arp(ip, community, sys_type))

    # 等待这一批完成
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 过滤有效结果并保存
    valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]

    if valid_results:
        try:
            with DBHelper() as db:
                save_batch_size = 200
                for i in range(0, len(valid_results), save_batch_size):
                    save_batch = valid_results[i:i + save_batch_size]
                    db.save_arp_info(save_batch)
                logger.info(f"批次 {batch_id}: 采集 {len(device_batch)} 台设备，成功保存 {len(valid_results)} 台")
        except Exception as e:
            logger.error(f"批次 {batch_id}: 保存数据失败: {e}")

    success = len(valid_results)
    failed = len(device_batch) - success
    return success, failed


async def run():
    """
    主执行函数 - 采集所有设备的ARP表（IPv4）
    分批采集和保存，避免等待时间过长
    """
    logger.info("开始执行ARP表采集任务（IPv4）")
    start_time = asyncio.get_event_loop().time()

    try:
        # 从数据库获取设备列表
        with DBHelper() as db:
            device_list = db.get_device_list()

        total_devices = len(device_list)
        logger.info(f"获取到 {total_devices} 台设备")

        # 分批处理，每批20台设备
        batch_size = 20
        batches = [device_list[i:i + batch_size] for i in range(0, total_devices, batch_size)]

        logger.info(f"分为 {len(batches)} 个批次进行采集")

        # 并发执行所有批次
        batch_tasks = []
        for i, batch in enumerate(batches, 1):
            batch_tasks.append(collect_and_save_batch(batch, i))

        # 等待所有批次完成
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # 统计总结果
        total_success = 0
        total_failed = 0
        for result in batch_results:
            if isinstance(result, tuple):
                total_success += result[0]
                total_failed += result[1]

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        logger.info(f"ARP表采集完成 - 成功: {total_success}, 失败: {total_failed}, 耗时: {elapsed:.2f}秒")

    except Exception as e:
        logger.error(f"ARP表采集任务执行失败: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


