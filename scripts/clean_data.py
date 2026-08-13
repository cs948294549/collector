"""
数据清理脚本 - 清理过期的历史数据
"""
import asyncio
import logging
from datetime import datetime, timedelta
from utils.db_helper import DBHelper

logger = logging.getLogger(__name__)


async def run():
    """
    主执行函数 - 清理过期数据
    默认保留7天内的数据
    """
    logger.info("开始执行数据清理任务")

    try:
        db = DBHelper()

        # 计算清理日期（保留7天）
        retention_days = 7
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"清理 {cutoff_str} 之前的数据（保留最近{retention_days}天）")

        # 清理各类历史数据
        tables = [
            'arps',
            'macs',
            'ports',
            'routes',
            'lldps',
            'gates',
            'gates_ipv6'
        ]

        total_deleted = 0
        for table in tables:
            try:
                deleted_count = db.clean_old_data(table, cutoff_str)
                total_deleted += deleted_count
                logger.info(f"表 {table} 清理了 {deleted_count} 条记录")
            except Exception as e:
                logger.error(f"清理表 {table} 失败: {e}")

        logger.info(f"数据清理完成 - 共清理 {total_deleted} 条记录")

    except Exception as e:
        logger.error(f"数据清理任务执行失败: {e}")
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
