"""
定时任务调度器
使用 APScheduler 管理所有的采集任务
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import importlib
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone='Asia/Shanghai')
        self.tasks = {}

        # 监听任务执行事件
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)

    def _job_executed_listener(self, event):
        """任务执行成功监听器"""
        logger.info(f"任务 {event.job_id} 执行成功")

    def _job_error_listener(self, event):
        """任务执行失败监听器"""
        logger.error(f"任务 {event.job_id} 执行失败: {event.exception}")

    def add_cron_task(self, task_id: str, module_path: str, function_name: str,
                      cron_expr: str, description: str = ""):
        """
        添加 cron 定时任务

        Args:
            task_id: 任务唯一标识
            module_path: 模块路径，如 'scripts.collect_device'
            function_name: 函数名称
            cron_expr: cron 表达式，如 '0 */1 * * *' (每小时执行)
            description: 任务描述
        """
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)

            # 解析 cron 表达式
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expr}")

            minute, hour, day, month, day_of_week = parts

            # 添加任务
            job = self.scheduler.add_job(
                func,
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id=task_id,
                name=description or task_id,
                replace_existing=True
            )

            self.tasks[task_id] = {
                'job': job,
                'module': module_path,
                'function': function_name,
                'type': 'cron',
                'schedule': cron_expr,
                'description': description
            }

            logger.info(f"添加 cron 任务: {task_id} - {description} - {cron_expr}")
            return True

        except Exception as e:
            logger.error(f"添加任务失败 {task_id}: {e}")
            return False

    def add_interval_task(self, task_id: str, module_path: str, function_name: str,
                         seconds: int = 0, minutes: int = 0, hours: int = 0,
                         description: str = ""):
        """
        添加间隔定时任务

        Args:
            task_id: 任务唯一标识
            module_path: 模块路径
            function_name: 函数名称
            seconds: 间隔秒数
            minutes: 间隔分钟数
            hours: 间隔小时数
            description: 任务描述
        """
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)

            # 添加任务
            job = self.scheduler.add_job(
                func,
                trigger=IntervalTrigger(
                    seconds=seconds,
                    minutes=minutes,
                    hours=hours
                ),
                id=task_id,
                name=description or task_id,
                replace_existing=True
            )

            self.tasks[task_id] = {
                'job': job,
                'module': module_path,
                'function': function_name,
                'type': 'interval',
                'schedule': f"{hours}h {minutes}m {seconds}s",
                'description': description
            }

            logger.info(f"添加间隔任务: {task_id} - {description} - 间隔 {hours}h {minutes}m {seconds}s")
            return True

        except Exception as e:
            logger.error(f"添加任务失败 {task_id}: {e}")
            return False

    def remove_task(self, task_id: str):
        """移除任务"""
        try:
            self.scheduler.remove_job(task_id)
            if task_id in self.tasks:
                del self.tasks[task_id]
            logger.info(f"移除任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"移除任务失败 {task_id}: {e}")
            return False

    def pause_task(self, task_id: str):
        """暂停任务"""
        try:
            self.scheduler.pause_job(task_id)
            logger.info(f"暂停任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"暂停任务失败 {task_id}: {e}")
            return False

    def resume_task(self, task_id: str):
        """恢复任务"""
        try:
            self.scheduler.resume_job(task_id)
            logger.info(f"恢复任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"恢复任务失败 {task_id}: {e}")
            return False

    def get_tasks(self):
        """获取所有任务信息"""
        task_info = []
        for task_id, task_data in self.tasks.items():
            info = {
                'id': task_id,
                'name': task_data.get('description', task_id),
                'type': task_data['type'],
                'schedule': task_data['schedule'],
                'description': task_data['description'],
                'next_run_time': 'N/A'
            }

            # 尝试从调度器获取实际的job对象
            try:
                job = self.scheduler.get_job(task_id)
                if job and hasattr(job, 'next_run_time') and job.next_run_time:
                    info['next_run_time'] = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass

            task_info.append(info)
        return task_info

    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            logger.info("调度器已启动")
        except Exception as e:
            logger.error(f"调度器启动失败: {e}")

    def shutdown(self):
        """关闭调度器"""
        try:
            self.scheduler.shutdown()
            logger.info("调度器已关闭")
        except Exception as e:
            logger.error(f"调度器关闭失败: {e}")
