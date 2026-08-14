#!/usr/bin/env python3
"""
诊断 MAC 地址采集卡住的问题
逐个设备采集，找出问题设备
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from Module.MAC import MACTable
from utils.db_helper import DBHelper
from utils.concurrency_limiter import get_concurrency_limiter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_single_device(ip: str, community: str, sys_type: str, timeout: int = 30):
    """测试单个设备采集，带超时"""
    start_time = time.time()
    try:
        logger.info(f"开始采集设备: {ip}")

        # 使用 asyncio.wait_for 添加超时控制
        limiter = get_concurrency_limiter()
        async with limiter:
            mac = MACTable(ip, community, sys_type)
            mac_data = await asyncio.wait_for(
                mac.getMACTables(),
                timeout=timeout
            )

        elapsed = time.time() - start_time
        mac_count = len(mac_data) if mac_data else 0
        logger.info(f"✓ {ip} 采集成功 - {mac_count} 条MAC记录 - 耗时: {elapsed:.2f}秒")
        return {
            'ip': ip,
            'status': 'success',
            'mac_count': mac_count,
            'elapsed': elapsed
        }

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"✗ {ip} 采集超时 (>{timeout}秒) - 耗时: {elapsed:.2f}秒")
        return {
            'ip': ip,
            'status': 'timeout',
            'elapsed': elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ {ip} 采集失败: {e} - 耗时: {elapsed:.2f}秒")
        return {
            'ip': ip,
            'status': 'error',
            'error': str(e),
            'elapsed': elapsed
        }


async def diagnose_mac_collection():
    """诊断 MAC 采集问题"""
    logger.info("=" * 70)
    logger.info("MAC 地址采集诊断工具")
    logger.info("=" * 70)

    # 获取设备列表
    try:
        with DBHelper() as db:
            device_list = db.get_device_list()

        total = len(device_list)
        logger.info(f"获取到 {total} 台设备")
        logger.info("")

    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        return

    # 统计结果
    results = {
        'success': [],
        'timeout': [],
        'error': []
    }

    # 逐个测试设备
    for i, device in enumerate(device_list, 1):
        ip = device.get('ip')
        community = device.get('community', 'public')
        sys_type = device.get('sys_type', 'default')

        logger.info(f"进度: {i}/{total}")

        result = await test_single_device(ip, community, sys_type, timeout=30)
        results[result['status']].append(result)

        # 每10个设备输出一次统计
        if i % 10 == 0:
            logger.info("")
            logger.info(f"--- 当前统计 ({i}/{total}) ---")
            logger.info(f"  成功: {len(results['success'])}")
            logger.info(f"  超时: {len(results['timeout'])}")
            logger.info(f"  错误: {len(results['error'])}")
            logger.info("")

    # 最终统计
    logger.info("")
    logger.info("=" * 70)
    logger.info("诊断完成 - 最终统计")
    logger.info("=" * 70)
    logger.info(f"总计设备: {total}")
    logger.info(f"成功: {len(results['success'])}")
    logger.info(f"超时: {len(results['timeout'])}")
    logger.info(f"错误: {len(results['error'])}")
    logger.info("")

    # 显示超时设备
    if results['timeout']:
        logger.info("超时设备列表:")
        for r in results['timeout']:
            logger.info(f"  - {r['ip']} (耗时: {r['elapsed']:.2f}秒)")
        logger.info("")

    # 显示错误设备（只显示前10个）
    if results['error']:
        logger.info(f"错误设备列表 (显示前10个，共{len(results['error'])}个):")
        for r in results['error'][:10]:
            error_msg = r.get('error', 'Unknown')
            logger.info(f"  - {r['ip']}: {error_msg}")
        logger.info("")

    # 显示最慢的5个设备
    all_results = results['success'] + results['timeout']
    if all_results:
        all_results.sort(key=lambda x: x['elapsed'], reverse=True)
        logger.info("采集最慢的5个设备:")
        for r in all_results[:5]:
            status_icon = "✓" if r['status'] == 'success' else "✗"
            logger.info(f"  {status_icon} {r['ip']} - {r['elapsed']:.2f}秒")
        logger.info("")

    logger.info("=" * 70)


if __name__ == '__main__':
    try:
        asyncio.run(diagnose_mac_collection())
    except KeyboardInterrupt:
        logger.info("\n诊断被用户中断")
    except Exception as e:
        logger.error(f"诊断失败: {e}", exc_info=True)
        sys.exit(1)
