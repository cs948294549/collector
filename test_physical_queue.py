#!/usr/bin/env python3
"""
测试 physical 采集通过队列保存
模拟 main.py 的方式
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from Module.Physical import PhysicalInfo
from utils.db_helper import DBHelper
from utils.db_queue import get_db_queue
from utils.concurrency_limiter import get_concurrency_limiter

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_queue_workflow():
    """测试完整的队列工作流程"""
    logger.info("=" * 70)
    logger.info("测试 physical 数据通过队列保存的完整流程")
    logger.info("=" * 70)

    # 获取设备
    with DBHelper() as db:
        device_list = db.get_device_list()[:3]  # 只测试3个设备

    logger.info(f"测试 {len(device_list)} 个设备")
    logger.info("")

    # 1. 启动队列
    logger.info("步骤1: 启动队列")
    queue = get_db_queue()
    await queue.start()
    logger.info("队列已启动")
    logger.info("")

    # 2. 采集并加入队列（模拟 collect_physical.py 的方式）
    logger.info("步骤2: 采集设备并加入队列")
    for device in device_list:
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')

        try:
            limiter = get_concurrency_limiter()
            async with limiter:
                physical = PhysicalInfo(ip, community, sys_type)
                physical_data = await physical.getPhysicalInfos()

                if physical_data:
                    result = {
                        'ip': ip,
                        'sn_info': physical_data
                    }
                    await queue.put('physical', result)
                    logger.info(f"  ✓ {ip} - {len(physical_data)} 条记录已加入队列")
                else:
                    logger.warning(f"  ✗ {ip} - 未采集到数据")

        except Exception as e:
            logger.error(f"  ✗ {ip} - 采集失败: {e}")

    logger.info("")

    # 3. 查看队列统计
    stats = queue.get_stats()
    logger.info(f"步骤3: 队列统计")
    logger.info(f"  队列大小: {stats['queue_size']}")
    logger.info(f"  已处理: {stats['total_processed']}")
    logger.info(f"  失败: {stats['total_failed']}")
    logger.info("")

    # 4. 等待队列处理完成
    logger.info("步骤4: 等待队列处理（最多等待30秒）")
    for i in range(30):
        await asyncio.sleep(1)
        stats = queue.get_stats()
        if stats['queue_size'] == 0:
            logger.info(f"  队列已清空 (等待了 {i+1} 秒)")
            break
        if i % 5 == 0:
            logger.info(f"  队列剩余: {stats['queue_size']}, 已处理: {stats['total_processed']}")

    logger.info("")

    # 5. 最终统计
    stats = queue.get_stats()
    logger.info(f"步骤5: 最终队列统计")
    logger.info(f"  队列大小: {stats['queue_size']}")
    logger.info(f"  已处理: {stats['total_processed']}")
    logger.info(f"  失败: {stats['total_failed']}")
    logger.info("")

    # 6. 检查数据库
    logger.info("步骤6: 检查数据库")
    with DBHelper() as db:
        cursor = db.conn.cursor()
        for device in device_list:
            ip = device.get('ip')
            cursor.execute("SELECT COUNT(*) FROM dev_sn WHERE ip = %s", (ip,))
            count = cursor.fetchone()[0]
            logger.info(f"  {ip}: {count} 条记录")

    logger.info("")

    # 7. 停止队列
    logger.info("步骤7: 停止队列")
    await queue.stop()
    logger.info("队列已停止")

    logger.info("")
    logger.info("=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)


if __name__ == '__main__':
    try:
        asyncio.run(test_queue_workflow())
    except KeyboardInterrupt:
        logger.info("\n测试被中断")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
