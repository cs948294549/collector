"""
验证所有采集脚本的导入是否正确
"""
import sys
import importlib

scripts = [
    'scripts.collect_device',
    'scripts.collect_arp',
    'scripts.collect_arpv6',
    'scripts.collect_mac',
    'scripts.collect_port',
    'scripts.collect_route',
    'scripts.collect_lldp',
    'scripts.collect_gate',
    'scripts.collect_physical',
    'scripts.clean_data'
]

print("=" * 60)
print("验证脚本导入")
print("=" * 60)

failed = []
for script in scripts:
    try:
        module = importlib.import_module(script)
        # 检查是否有 run 函数
        if hasattr(module, 'run'):
            print(f"✓ {script:30s} - OK")
        else:
            print(f"✗ {script:30s} - 缺少 run() 函数")
            failed.append(script)
    except Exception as e:
        print(f"✗ {script:30s} - {str(e)}")
        failed.append(script)

print("=" * 60)
if failed:
    print(f"失败: {len(failed)}/{len(scripts)}")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"全部通过: {len(scripts)}/{len(scripts)}")
    sys.exit(0)
