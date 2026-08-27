"""
SNMP Collector - 网络设备信息采集器
支持定时任务调度和并发采集
"""
import asyncio
import logging
import signal
import sys
import yaml
from pathlib import Path
from utils.scheduler import TaskScheduler
from utils.db_queue import get_db_queue

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CollectorApp:
    """采集器主程序"""

    def __init__(self, config_file='config/task_config.yaml'):
        self.config_file = config_file
        self.scheduler = TaskScheduler()
        self.db_queue = get_db_queue()  # 获取数据库写入队列实例
        self.running = False

    def load_task_config(self):
        """加载任务配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('tasks', [])
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return []

    def register_tasks(self):
        """注册所有任务"""
        tasks = self.load_task_config()

        for task in tasks:
            if not task.get('enabled', True):
                logger.info(f"任务 {task['id']} 已禁用，跳过")
                continue

            task_id = task['id']
            task_type = task['type']
            module = task['module']
            function = task['function']
            description = task.get('description', '')

            if task_type == 'cron':
                # Cron 任务
                schedule = task['schedule']
                success = self.scheduler.add_cron_task(
                    task_id=task_id,
                    module_path=module,
                    function_name=function,
                    cron_expr=schedule,
                    description=description
                )
                if success:
                    logger.info(f"注册 cron 任务成功: {task_id}")
                else:
                    logger.error(f"注册 cron 任务失败: {task_id}")

            elif task_type == 'interval':
                # 间隔任务
                schedule = task['schedule']
                hours = schedule.get('hours', 0)
                minutes = schedule.get('minutes', 0)
                seconds = schedule.get('seconds', 0)

                success = self.scheduler.add_interval_task(
                    task_id=task_id,
                    module_path=module,
                    function_name=function,
                    hours=hours,
                    minutes=minutes,
                    seconds=seconds,
                    description=description
                )
                if success:
                    logger.info(f"注册间隔任务成功: {task_id}")
                else:
                    logger.error(f"注册间隔任务失败: {task_id}")

    def start(self):
        """启动采集器"""
        logger.info("=" * 60)
        logger.info("SNMP 采集器启动中...")
        logger.info("=" * 60)

        # 创建必要的目录
        Path('logs').mkdir(exist_ok=True)

        # 注册任务
        self.register_tasks()

        # 启动调度器
        self.scheduler.start()
        self.running = True

        # 显示已注册的任务（在调度器启动后）
        tasks = self.scheduler.get_tasks()
        logger.info(f"\n共注册 {len(tasks)} 个任务:")
        for task in tasks:
            logger.info(f"  - {task['name']} ({task['type']}) - 下次运行: {task['next_run_time']}")

        logger.info("\n采集器已启动，按 Ctrl+C 退出")

    def stop(self):
        """停止采集器"""
        if self.running:
            logger.info("\n正在停止采集器...")
            self.scheduler.shutdown()
            self.running = False
            logger.info("采集器已停止")

    async def async_stop(self):
        """异步停止采集器（包含队列停止）"""
        if self.running:
            logger.info("\n正在停止采集器...")
            self.scheduler.shutdown()
            await self.db_queue.stop()
            self.running = False
            logger.info("采集器已停止")

    def signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"\n接收到信号 {signum}，准备退出...")
        self.stop()
        sys.exit(0)


async def main():
    """主函数"""
    # 创建应用实例
    app = CollectorApp()

    # 启动数据库写入队列
    logger.info("正在启动数据库写入队列...")
    await app.db_queue.start()

    # 注册信号处理
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)

    try:
        # 启动应用
        app.start()

        # 保持运行
        while app.running:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"程序运行异常: {e}")
        app.stop()
        sys.exit(1)
    finally:
        # 停止数据库写入队列
        logger.info("正在停止数据库写入队列...")
        await app.db_queue.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        sys.exit(1)
