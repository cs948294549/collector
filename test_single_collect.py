#!/usr/bin/env python3
"""
测试单个设备采集
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from Module.MAC import MACTable
from utils.db_helper import DBHelper
from utils.concurrency_limiter import get_concurrency_limiter

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_single_device():
    """测试单个设备采集"""
    # 先获取一个设备IP
    try:
        with DBHelper() as db:
            device_list = db.get_device_list()

        if not device_list:
            logger.error("没有可用的设备")
            return

        # 取第一个设备
        device = device_list[0]
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')

        logger.info(f"测试采集设备: {ip}, community: {community}, sys_type: {sys_type}")

        # 不使用并发限制器测试
        try:
            mac = MACTable(ip, community, sys_type)
            mac_data = await mac.getMACTables()
            logger.info(f"采集成功！获取到 {len(mac_data) if mac_data else 0} 条MAC记录")
            if mac_data:
                logger.info(f"第一条数据示例: {mac_data[0]}")
        except Exception as e:
            logger.error(f"采集失败: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == '__main__':
    asyncio.run(test_single_device())
