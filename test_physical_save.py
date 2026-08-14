#!/usr/bin/env python3
"""
测试物理信息采集和保存
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

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_physical_collection():
    """测试物理信息采集"""
    logger.info("=" * 70)
    logger.info("测试物理信息采集和保存")
    logger.info("=" * 70)

    # 获取一个设备测试
    try:
        with DBHelper() as db:
            device_list = db.get_device_list()

        if not device_list:
            logger.error("没有可用的设备")
            return

        device = device_list[0]
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')

        logger.info(f"测试设备: {ip}")
        logger.info("")

        # 1. 测试采集
        logger.info("步骤1: 采集物理信息")
        physical = PhysicalInfo(ip, community, sys_type)
        physical_data = await physical.getPhysicalInfos()

        if not physical_data:
            logger.warning("未采集到物理信息")
            return

        logger.info(f"采集成功! 获取到 {len(physical_data)} 条物理信息")
        logger.info(f"数据示例: {physical_data[0] if physical_data else 'None'}")
        logger.info("")

        # 2. 测试队列写入
        logger.info("步骤2: 测试队列写入")

        # 启动队列
        queue = get_db_queue()
        await queue.start()
        logger.info("队列已启动")

        # 构造数据格式
        result = {
            'ip': ip,
            'sn_info': physical_data
        }

        # 加入队列
        await queue.put('physical', result)
        logger.info("数据已加入队列")

        # 获取队列统计
        stats = queue.get_stats()
        logger.info(f"队列统计: {stats}")
        logger.info("")

        # 3. 等待队列处理
        logger.info("步骤3: 等待队列处理")
        await asyncio.sleep(5)

        stats = queue.get_stats()
        logger.info(f"处理后统计: {stats}")
        logger.info("")

        # 4. 检查数据库
        logger.info("步骤4: 检查数据库中的数据")
        with DBHelper() as db:
            cursor = db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dev_sn WHERE ip = %s", (ip,))
            count = cursor.fetchone()[0]
            logger.info(f"数据库中设备 {ip} 的记录数: {count}")

            if count > 0:
                cursor.execute("SELECT * FROM dev_sn WHERE ip = %s LIMIT 1", (ip,))
                row = cursor.fetchone()
                logger.info(f"数据库记录示例: {row}")

        logger.info("")

        # 停止队列
        await queue.stop()
        logger.info("队列已停止")

        logger.info("=" * 70)
        logger.info("测试完成")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == '__main__':
    asyncio.run(test_physical_collection())
