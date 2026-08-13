"""
批量更新所有采集脚本，添加 sys_type 参数支持
"""

import os
import re

# 脚本目录
scripts_dir = "/Users/weidian/netops/projects/collector/scripts"

# 需要更新的脚本列表（不包括 collect_device.py 和 clean_data.py）
scripts_to_update = [
    "collect_arp.py",
    "collect_arpv6.py",
    "collect_mac.py",
    "collect_port.py",
    "collect_route.py",
    "collect_lldp.py",
    "collect_gate.py",
    "collect_gate_ipv6.py",
    "collect_physical.py"
]

for script_name in scripts_to_update:
    script_path = os.path.join(scripts_dir, script_name)

    if not os.path.exists(script_path):
        print(f"⚠️  跳过不存在的文件: {script_name}")
        continue

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 更新函数签名，添加 sys_type 参数
    content = re.sub(
        r'async def collect_single_device_\w+\(ip: str, community: str = "public"\):',
        r'async def collect_single_device_\g<0>'.replace(
            'community: str = "public")',
            'community: str = "public", sys_type: str = "default"):'
        ),
        content
    )

    # 简单替换方式
    content = content.replace(
        'community: str = "public"):',
        'community: str = "public", sys_type: str = "default"):'
    )

    # 2. 更新 Module 类实例化，添加 sys_type 参数
    # 匹配模式: ClassName(ip, community)
    module_classes = [
        'ARPTable', 'ARPv6Table', 'MACTable', 'PortInfo',
        'RouteInfo', 'LLDPInfo', 'Gate', 'Gate_ipv6', 'PhysicalInfo'
    ]

    for class_name in module_classes:
        # 替换: ClassName(ip, community) -> ClassName(ip, community, sys_type)
        pattern = f'{class_name}\\(ip, community\\)'
        replacement = f'{class_name}(ip, community, sys_type)'
        content = content.replace(pattern, replacement)

    # 3. 在 run() 函数中添加 sys_type 获取
    # 查找: community = device.get('community', 'public')
    # 添加: sys_type = device.get('sys_type', 'default')
    if "sys_type = device.get('sys_type'" not in content:
        content = content.replace(
            "community = device.get('community', 'public')",
            "community = device.get('community', 'public')\n            sys_type = device.get('sys_type', 'default')  # 获取设备类型"
        )

    # 4. 更新任务调用，添加 sys_type 参数
    # 查找类似: tasks.append(collect_single_device_xxx(ip, community))
    # 替换为: tasks.append(collect_single_device_xxx(ip, community, sys_type))
    content = re.sub(
        r'tasks\.append\(collect_single_device_\w+\(ip, community\)\)',
        lambda m: m.group(0).replace('community)', 'community, sys_type)'),
        content
    )

    # 写回文件
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已更新: {script_name}")

print("\n✅ 所有脚本更新完成！")
