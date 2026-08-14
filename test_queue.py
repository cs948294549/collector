#!/usr/bin/env python3
"""
测试数据库写入队列
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.db_queue import get_db_queue

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_queue():
    """测试队列基本功能"""
    logger.info("=" * 60)
    logger.info("测试数据库写入队列")
    logger.info("=" * 60)

    # 获取队列实例
    queue = get_db_queue()

    # 启动队列
    await queue.start()
    logger.info("队列已启动")

    # 模拟添加一些测试数据
    test_data = [
        {
            'ip': '192.168.1.1',
            'ports': [
                {
                    'port_id': '1',
                    'if_name': 'GigabitEthernet0/0',
                    'mac_address': '00:11:22:33:44:55',
                    'speed': 1000,
                    'admin_statu': 1,
                    'oper_statu': 1,
                    'alias': 'Test Port',
                    'timestamp': '2026-08-14 17:00:00'
                }
            ]
        }
    ]

    # 添加到队列
    logger.info("添加测试数据到队列...")
    for data in test_data:
        await queue.put('port', data)

    logger.info(f"已添加 {len(test_data)} 条数据到队列")

    # 等待队列处理
    logger.info("等待队列处理数据...")
    await asyncio.sleep(5)

    # 获取统计信息
    stats = queue.get_stats()
    logger.info("=" * 60)
    logger.info("队列统计信息:")
    logger.info(f"  - 队列大小: {stats['queue_size']}")
    logger.info(f"  - 已处理: {stats['total_processed']}")
    logger.info(f"  - 失败: {stats['total_failed']}")
    logger.info(f"  - 运行中: {stats['running']}")
    logger.info("=" * 60)

    # 停止队列
    logger.info("停止队列...")
    await queue.stop()
    logger.info("队列已停止")


if __name__ == '__main__':
    try:
        asyncio.run(test_queue())
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)
