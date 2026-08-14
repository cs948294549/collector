"""
并发控制工具
使用信号量限制并发数量，避免打开过多文件描述符
"""
import asyncio
from typing import Optional


class ConcurrencyLimiter:
    """并发限制器 - 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls, max_concurrent: int = 50):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_concurrent: int = 50):
        if self._initialized:
            return

        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self._initialized = True

    async def acquire(self):
        """获取许可"""
        await self.semaphore.acquire()

    def release(self):
        """释放许可"""
        self.semaphore.release()

    async def __aenter__(self):
        """上下文管理器入口"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False

    def update_limit(self, max_concurrent: int):
        """动态更新并发限制"""
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent


# 全局并发限制器实例
_limiter = None


def get_concurrency_limiter(max_concurrent: int = 50) -> ConcurrencyLimiter:
    """
    获取全局并发限制器实例

    Args:
        max_concurrent: 最大并发数（默认50）

    Returns:
        ConcurrencyLimiter实例
    """
    global _limiter
    if _limiter is None:
        _limiter = ConcurrencyLimiter(max_concurrent)
    return _limiter
