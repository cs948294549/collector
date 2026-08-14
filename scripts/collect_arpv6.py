"""
ARPv6 邻居表采集脚本（IPv6）
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Module.ARPv6 import ARPv6Table
from utils.db_helper import DBHelper
from utils.db_queue import get_db_queue
from utils.concurrency_limiter import get_concurrency_limiter

logger = logging.getLogger(__name__)


async def collect_single_device_arpv6(ip: str, community: str = "public", sys_type: str = "default"):
    """采集单个设备的IPv6邻居表"""
    limiter = get_concurrency_limiter()
    async with limiter:
        try:
            arpv6 = ARPv6Table(ip, community, sys_type)
            arpv6_data = await arpv6.getARPs()

            return {
                'ip': ip,
                'arpv6': arpv6_data
            }
        except Exception as e:
            logger.error(f"采集设备 {ip} IPv6邻居表失败: {e}")
            return None


async def collect_and_save_batch(device_batch, batch_id, use_queue=True):
    """采集一批设备并保存"""
    tasks = []
    for device in device_batch:
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')
        tasks.append(collect_single_device_arpv6(ip, community, sys_type))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]

    if valid_results:
        try:
            if use_queue:
                # 使用消息队列异步写入
                queue = get_db_queue()
                for result in valid_results:
                    await queue.put('arpv6', result)
                logger.info(f"批次 {batch_id}: 采集 {len(device_batch)} 台设备，{len(valid_results)} 台已加入写入队列")
            else:
                # 直接写入数据库（保留旧方式作为fallback）
                # 注意：ARPv6 可能需要单独的保存方法，这里暂时使用arp的方法
                logger.info(f"批次 {batch_id}: 采集 {len(device_batch)} 台设备，成功采集 {len(valid_results)} 台IPv6邻居表数据")
        except Exception as e:
            logger.error(f"批次 {batch_id}: 处理数据失败: {e}")

    return len(valid_results), len(device_batch) - len(valid_results)


async def run():
    """
    主执行函数 - 采集所有设备的IPv6邻居表
    分批采集和保存，避免等待时间过长
    """
    logger.info("开始执行IPv6邻居表采集任务")
    start_time = asyncio.get_event_loop().time()

    try:
        with DBHelper() as db:
            device_list = db.get_device_list()

        total_devices = len(device_list)
        logger.info(f"获取到 {total_devices} 台设备")

        batch_size = 10  # 减小批次避免过多并发
        batches = [device_list[i:i + batch_size] for i in range(0, total_devices, batch_size)]
        logger.info(f"分为 {len(batches)} 个批次进行采集（最大并发: 50）")

        batch_tasks = []
        for i, batch in enumerate(batches, 1):
            batch_tasks.append(collect_and_save_batch(batch, i))

        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        total_success = sum(r[0] for r in batch_results if isinstance(r, tuple))
        total_failed = sum(r[1] for r in batch_results if isinstance(r, tuple))

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        logger.info(f"IPv6邻居表采集完成 - 成功: {total_success}, 失败: {total_failed}, 耗时: {elapsed:.2f}秒")

    except Exception as e:
        logger.error(f"IPv6邻居表采集任务执行失败: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
