#!/usr/bin/env python3
"""
直接测试 save_dev_sn_info 方法
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

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_direct_save():
    """直接测试保存功能"""
    logger.info("=" * 70)
    logger.info("直接测试 save_dev_sn_info 方法")
    logger.info("=" * 70)

    # 获取一个设备
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

    # 采集数据
    logger.info("步骤1: 采集物理信息")
    physical = PhysicalInfo(ip, community, sys_type)
    physical_data = await physical.getPhysicalInfos()

    if not physical_data:
        logger.warning("未采集到物理信息")
        return

    logger.info(f"采集成功! 获取到 {len(physical_data)} 条记录")
    logger.info(f"数据类型: {type(physical_data)}")
    logger.info(f"第一条数据: {physical_data[0]}")
    logger.info("")

    # 构造保存格式
    logger.info("步骤2: 构造保存数据格式")
    save_data = [{
        'ip': ip,
        'sn_info': physical_data
    }]
    logger.info(f"保存数据格式: {save_data}")
    logger.info("")

    # 保存前检查
    logger.info("步骤3: 保存前数据库检查")
    with DBHelper() as db:
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dev_sn WHERE ip = %s", (ip,))
        count_before = cursor.fetchone()[0]
        logger.info(f"保存前记录数: {count_before}")
    logger.info("")

    # 直接保存
    logger.info("步骤4: 调用 save_dev_sn_info 保存")
    with DBHelper() as db:
        db.save_dev_sn_info(save_data)
    logger.info("保存完成")
    logger.info("")

    # 保存后检查
    logger.info("步骤5: 保存后数据库检查")
    with DBHelper() as db:
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dev_sn WHERE ip = %s", (ip,))
        count_after = cursor.fetchone()[0]
        logger.info(f"保存后记录数: {count_after}")

        if count_after > 0:
            cursor.execute("SELECT * FROM dev_sn WHERE ip = %s LIMIT 3", (ip,))
            rows = cursor.fetchall()
            logger.info(f"数据库中的记录:")
            for row in rows:
                logger.info(f"  {row}")

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"测试完成 - 新增 {count_after - count_before} 条记录")
    logger.info("=" * 70)


if __name__ == '__main__':
    asyncio.run(test_direct_save())
