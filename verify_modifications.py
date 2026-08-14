#!/usr/bin/env python3
"""
验证所有采集脚本是否正确修改
"""
import re
from pathlib import Path

def check_script(script_path):
    """检查单个脚本"""
    path = Path(script_path)
    if not path.exists():
        return False, "文件不存在"

    content = path.read_text(encoding='utf-8')

    checks = {
        'import_db_queue': 'from utils.db_queue import get_db_queue' in content,
        'use_queue_param': 'use_queue=True' in content,
        'queue_put': 'await queue.put(' in content or 'queue = get_db_queue()' in content,
    }

    all_passed = all(checks.values())
    return all_passed, checks

def main():
    print("=" * 70)
    print("验证所有采集脚本修改情况")
    print("=" * 70)
    print()

    scripts = [
        'scripts/collect_port.py',
        'scripts/collect_mac.py',
        'scripts/collect_arp.py',
        'scripts/collect_device.py',
        'scripts/collect_lldp.py',
        'scripts/collect_gate.py',
        'scripts/collect_physical.py',
        'scripts/collect_route.py',
        'scripts/collect_arpv6.py',
        'scripts/collect_gate_ipv6.py',
    ]

    results = {}
    for script in scripts:
        passed, checks = check_script(script)
        results[script] = (passed, checks)

    # 显示结果
    for script, (passed, checks) in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {Path(script).name}")

        if not passed:
            print("  检查项:")
            for check_name, check_passed in checks.items():
                check_status = "✓" if check_passed else "✗"
                print(f"    {check_status} {check_name}")
            print()

    # 统计
    total = len(results)
    passed_count = sum(1 for p, _ in results.values() if p)

    print()
    print("=" * 70)
    print(f"总计: {passed_count}/{total} 个脚本已正确修改")

    if passed_count == total:
        print("✅ 所有采集脚本已成功修改！")
        return 0
    else:
        print(f"⚠️  还有 {total - passed_count} 个脚本需要修改")
        return 1

    print("=" * 70)

if __name__ == '__main__':
    exit(main())
