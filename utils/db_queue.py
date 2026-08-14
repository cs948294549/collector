"""
数据库写入队列
使用单一数据库连接处理所有写入请求，避免并发连接过多
"""
import asyncio
import logging
from queue import Queue
from threading import Thread
from typing import Dict, List, Any, Optional
from utils.db_helper import DBHelper

logger = logging.getLogger(__name__)


class DBWriteQueue:
    """数据库写入队列 - 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.queue = asyncio.Queue(maxsize=10000)  # 最大队列长度
        self.running = False
        self.worker_task = None
        self.stats = {
            'total_processed': 0,
            'total_failed': 0,
            'queue_size': 0
        }
        self._initialized = True
        logger.info("数据库写入队列已初始化")

    async def start(self):
        """启动队列处理器"""
        if self.running:
            logger.warning("队列处理器已在运行")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("数据库写入队列处理器已启动")

    async def stop(self):
        """停止队列处理器"""
        if not self.running:
            return

        logger.info("正在停止数据库写入队列...")
        self.running = False

        # 等待队列处理完成
        await self.queue.join()

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info(f"队列处理器已停止 - 已处理: {self.stats['total_processed']}, 失败: {self.stats['total_failed']}")

    async def put(self, operation: str, data: Any, priority: int = 0):
        """
        添加写入任务到队列

        Args:
            operation: 操作类型 (port, mac, arp, device, lldp, gate, physical, route, gate_ipv6, arpv6)
            data: 要写入的数据
            priority: 优先级（暂未实现）
        """
        try:
            task = {
                'operation': operation,
                'data': data,
                'priority': priority
            }
            await self.queue.put(task)
            self.stats['queue_size'] = self.queue.qsize()
        except asyncio.QueueFull:
            logger.error(f"队列已满，丢弃 {operation} 写入任务")
            self.stats['total_failed'] += 1

    async def _worker(self):
        """队列处理工作线程"""
        logger.info("队列处理工作线程已启动")

        # 创建一个长连接的数据库实例
        db = None

        try:
            db = DBHelper()
            logger.info("数据库连接已建立")

            batch_size = 100  # 批量处理大小
            batch_timeout = 2.0  # 批量处理超时（秒）

            while self.running:
                try:
                    # 收集一批任务
                    batch = []
                    deadline = asyncio.get_event_loop().time() + batch_timeout

                    while len(batch) < batch_size:
                        timeout = max(0.1, deadline - asyncio.get_event_loop().time())

                        try:
                            task = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                            batch.append(task)
                        except asyncio.TimeoutError:
                            # 超时，处理当前批次
                            break

                    if batch:
                        await self._process_batch(db, batch)

                        # 标记任务完成
                        for _ in batch:
                            self.queue.task_done()

                        self.stats['queue_size'] = self.queue.qsize()

                except Exception as e:
                    logger.error(f"处理队列任务时出错: {e}")
                    await asyncio.sleep(1)  # 出错后等待一下

        except Exception as e:
            logger.error(f"队列处理工作线程异常: {e}")
        finally:
            if db:
                db.close()
                logger.info("数据库连接已关闭")

    async def _process_batch(self, db: DBHelper, batch: List[Dict]):
        """
        批量处理写入任务

        Args:
            db: 数据库连接实例
            batch: 任务批次
        """
        # 按操作类型分组
        grouped = {}
        for task in batch:
            op = task['operation']
            if op not in grouped:
                grouped[op] = []
            grouped[op].append(task['data'])

        # 执行写入
        for operation, data_list in grouped.items():
            try:
                await self._execute_write(db, operation, data_list)
                self.stats['total_processed'] += len(data_list)
            except Exception as e:
                logger.error(f"批量写入 {operation} 失败: {e}")
                self.stats['total_failed'] += len(data_list)

    async def _execute_write(self, db: DBHelper, operation: str, data_list: List[Any]):
        """
        执行具体的数据库写入操作

        Args:
            db: 数据库连接实例
            operation: 操作类型
            data_list: 数据列表
        """
        # 将同步数据库操作放到线程池执行，避免阻塞事件循环
        loop = asyncio.get_event_loop()

        def sync_write():
            if operation == 'port':
                db.save_port_info(data_list)
            elif operation == 'mac':
                db.save_mac_info(data_list)
            elif operation == 'arp':
                db.save_arp_info(data_list)
            elif operation == 'device':
                db.save_device_info(data_list)
            elif operation == 'lldp':
                db.save_lldp_info(data_list)
            elif operation == 'gate':
                db.save_gate_info(data_list)
            elif operation == 'physical':
                db.save_dev_sn_info(data_list)
            elif operation == 'route':
                db.save_route_info(data_list)
            elif operation == 'gate_ipv6':
                db.save_gate_ipv6_info(data_list)
            else:
                logger.warning(f"未知的操作类型: {operation}")

        await loop.run_in_executor(None, sync_write)
        logger.debug(f"批量写入 {operation}: {len(data_list)} 条记录")

    def get_stats(self) -> Dict:
        """获取队列统计信息"""
        return {
            'queue_size': self.stats['queue_size'],
            'total_processed': self.stats['total_processed'],
            'total_failed': self.stats['total_failed'],
            'running': self.running
        }


# 全局队列实例
_db_queue = None


def get_db_queue() -> DBWriteQueue:
    """获取全局数据库写入队列实例"""
    global _db_queue
    if _db_queue is None:
        _db_queue = DBWriteQueue()
    return _db_queue
