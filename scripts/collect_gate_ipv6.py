"""
IPv6 网关信息采集脚本
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Module.Gate_ipv6 import Gate_ipv6
from utils.db_helper import DBHelper

logger = logging.getLogger(__name__)


async def collect_single_device_gate_ipv6(ip: str, community: str, sys_type: str):
    """采集单个设备的IPv6网关信息"""
    try:
        gate_ipv6 = Gate_ipv6(ip, community, sys_type)
        gate_ipv6_data = await gate_ipv6.getGates()
        return {
            'ip': ip,
            'gates_ipv6': gate_ipv6_data
        }
    except Exception as e:
        logger.error(f"采集设备 {ip} IPv6网关信息失败: {e}")
        return None


async def collect_and_save_batch(device_batch, batch_id):
    """采集一批设备并保存"""
    tasks = []
    for device in device_batch:
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')
        tasks.append(collect_single_device_gate_ipv6(ip, community, sys_type))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]

    if valid_results:
        try:
            db = DBHelper()
            save_batch_size = 200
            for i in range(0, len(valid_results), save_batch_size):
                save_batch = valid_results[i:i + save_batch_size]
                db.save_gate_ipv6_info(save_batch)
            db.close()
            logger.info(f"批次 {batch_id}: 采集 {len(device_batch)} 台设备，成功保存 {len(valid_results)} 台")
        except Exception as e:
            logger.error(f"批次 {batch_id}: 保存数据失败: {e}")

    return len(valid_results), len(device_batch) - len(valid_results)


async def run():
    """
    主执行函数 - 采集所有设备的IPv6网关信息
    分批采集和保存，避免等待时间过长
    """
    logger.info("开始执行IPv6网关信息采集任务")
    start_time = asyncio.get_event_loop().time()

    try:
        db = DBHelper()
        device_list = db.get_device_list()
        db.close()

        total_devices = len(device_list)
        logger.info(f"获取到 {total_devices} 台设备")

        batch_size = 20
        batches = [device_list[i:i + batch_size] for i in range(0, total_devices, batch_size)]
        logger.info(f"分为 {len(batches)} 个批次进行采集")

        batch_tasks = []
        for i, batch in enumerate(batches, 1):
            batch_tasks.append(collect_and_save_batch(batch, i))

        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        total_success = sum(r[0] for r in batch_results if isinstance(r, tuple))
        total_failed = sum(r[1] for r in batch_results if isinstance(r, tuple))

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        logger.info(f"IPv6网关信息采集完成 - 成功: {total_success}, 失败: {total_failed}, 耗时: {elapsed:.2f}秒")

    except Exception as e:
        logger.error(f"IPv6网关信息采集任务执行失败: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
