#!/usr/bin/env python3
"""
修复被破坏的采集脚本
"""
import os
import re

scripts_dir = "/Users/weidian/netops/projects/collector/scripts"

# 需要修复的脚本
scripts_to_fix = [
    "collect_mac.py",
    "collect_port.py",
    "collect_route.py",
    "collect_lldp.py",
    "collect_gate.py",
    "collect_gate_ipv6.py",
    "collect_physical.py"
]

for script_name in scripts_to_fix:
    script_path = os.path.join(scripts_dir, script_name)

    if not os.path.exists(script_path):
        print(f"⚠️  文件不存在: {script_name}")
        continue

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复重复的 async def
    content = re.sub(
        r'async def collect_single_device_async def collect_single_device_',
        r'async def collect_single_device_',
        content
    )

    # 写回文件
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已修复: {script_name}")

print("\n✅ 修复完成！")
