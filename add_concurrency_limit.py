#!/usr/bin/env python3
"""
批量添加并发限制到所有采集脚本
"""
from pathlib import Path
import re

scripts = [
    ('scripts/collect_port.py', 'collect_single_device_port'),
    ('scripts/collect_arp.py', 'collect_single_device_arp'),
    ('scripts/collect_device.py', 'collect_single_device'),
    ('scripts/collect_lldp.py', 'collect_single_device_lldp'),
    ('scripts/collect_gate.py', 'collect_single_device_gate'),
    ('scripts/collect_physical.py', 'collect_single_device_physical'),
    ('scripts/collect_route.py', 'collect_single_device_route'),
    ('scripts/collect_arpv6.py', 'collect_single_device_arpv6'),
    ('scripts/collect_gate_ipv6.py', 'collect_single_device_gate_ipv6'),
]


def add_import(content):
    """添加并发限制器导入"""
    if 'from utils.concurrency_limiter import get_concurrency_limiter' in content:
        return content

    # 在 db_queue 导入后添加
    pattern = r'(from utils\.db_queue import get_db_queue)'
    replacement = r'\1\nfrom utils.concurrency_limiter import get_concurrency_limiter'
    return re.sub(pattern, replacement, content)


def add_limiter_to_function(content, func_name):
    """给采集函数添加并发限制"""
    # 查找函数定义
    pattern = rf'(async def {func_name}\([^)]+\):\n    """[^"]*"""\n)(\s+try:)'

    def replacer(match):
        func_def = match.group(1)
        try_indent = match.group(2)

        # 添加限制器代码
        limiter_code = f'{func_def}    limiter = get_concurrency_limiter()\n    async with limiter:\n    {try_indent}'
        return limiter_code

    return re.sub(pattern, replacer, content, flags=re.DOTALL)


def update_batch_size(content):
    """更新批次大小为10"""
    pattern = r'batch_size = 20'
    replacement = 'batch_size = 10  # 减小批次避免过多并发'
    content = re.sub(pattern, replacement, content)

    # 更新日志信息
    pattern = r'logger\.info\(f"分为 \{len\(batches\)\} 个批次进行采集"\)'
    replacement = 'logger.info(f"分为 {len(batches)} 个批次进行采集（最大并发: 50）")'
    content = re.sub(pattern, replacement, content)

    return content


def process_file(filepath, func_name):
    """处理单个文件"""
    path = Path(filepath)
    if not path.exists():
        print(f"⊘ 跳过: {filepath} (不存在)")
        return False

    print(f"处理: {filepath}")
    content = path.read_text(encoding='utf-8')
    original = content

    # 1. 添加导入
    content = add_import(content)

    # 2. 给采集函数添加限制器
    content = add_limiter_to_function(content, func_name)

    # 3. 更新批次大小
    content = update_batch_size(content)

    if content != original:
        path.write_text(content, encoding='utf-8')
        print(f"  ✓ 已修改")
        return True
    else:
        print(f"  - 无需修改")
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("批量添加并发限制")
    print("=" * 70)
    print()

    modified = 0
    for filepath, func_name in scripts:
        if process_file(filepath, func_name):
            modified += 1
        print()

    print("=" * 70)
    print(f"完成! 共修改 {modified} 个文件")
    print("=" * 70)
