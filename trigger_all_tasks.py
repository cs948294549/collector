#!/usr/bin/env python3
"""
手动触发所有采集任务
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入所有采集任务
from scripts import (
    collect_device,
    collect_arp,
    collect_mac,
    collect_port,
    collect_lldp,
    collect_gate,
    collect_physical,
)


async def run_all_tasks():
    """并行运行所有采集任务"""
    logger.info("=" * 60)
    logger.info("开始执行所有采集任务...")
    logger.info("=" * 60)

    start_time = asyncio.get_event_loop().time()

    # 创建所有任务
    tasks = [
        ("设备信息", collect_device.run()),
        ("ARP表", collect_arp.run()),
        ("MAC地址表", collect_mac.run()),
        ("端口状态", collect_port.run()),
        ("LLDP邻居", collect_lldp.run()),
        ("网关信息", collect_gate.run()),
        ("设备物理信息", collect_physical.run()),
    ]

    # 并行执行所有任务
    logger.info(f"共 {len(tasks)} 个任务并行执行中...\n")

    results = await asyncio.gather(
        *[task[1] for task in tasks],
        return_exceptions=True
    )

    # 统计结果
    logger.info("\n" + "=" * 60)
    logger.info("任务执行结果:")
    logger.info("=" * 60)

    success_count = 0
    failed_count = 0

    for i, (name, result) in enumerate(zip([t[0] for t in tasks], results)):
        if isinstance(result, Exception):
            logger.error(f"✗ {name}: 失败 - {result}")
            failed_count += 1
        else:
            logger.info(f"✓ {name}: 完成")
            success_count += 1

    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time

    logger.info("=" * 60)
    logger.info(f"全部任务完成 - 成功: {success_count}, 失败: {failed_count}")
    logger.info(f"总耗时: {elapsed:.2f}秒")
    logger.info("=" * 60)


async def run_tasks_sequential():
    """顺序运行所有采集任务（降低并发压力）"""
    logger.info("=" * 60)
    logger.info("开始顺序执行所有采集任务...")
    logger.info("=" * 60)

    start_time = asyncio.get_event_loop().time()

    tasks = [
        ("设备信息", collect_device.run),
        ("ARP表", collect_arp.run),
        ("MAC地址表", collect_mac.run),
        ("端口状态", collect_port.run),
        ("LLDP邻居", collect_lldp.run),
        ("网关信息", collect_gate.run),
        ("设备物理信息", collect_physical.run),
    ]

    success_count = 0
    failed_count = 0

    for i, (name, task_func) in enumerate(tasks, 1):
        logger.info(f"\n[{i}/{len(tasks)}] 执行: {name}")
        try:
            await task_func()
            logger.info(f"✓ {name}: 完成")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ {name}: 失败 - {e}")
            failed_count += 1

    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time

    logger.info("\n" + "=" * 60)
    logger.info(f"全部任务完成 - 成功: {success_count}, 失败: {failed_count}")
    logger.info(f"总耗时: {elapsed:.2f}秒")
    logger.info("=" * 60)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='手动触发所有采集任务')
    parser.add_argument(
        '--mode',
        choices=['parallel', 'sequential'],
        default='parallel',
        help='执行模式: parallel(并行) 或 sequential(顺序)'
    )

    args = parser.parse_args()

    try:
        if args.mode == 'parallel':
            asyncio.run(run_all_tasks())
        else:
            asyncio.run(run_tasks_sequential())
    except KeyboardInterrupt:
        logger.info("\n任务被用户中断")
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)
