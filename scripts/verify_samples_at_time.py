#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证指定时间点的历史采样数据完整性

用法:
  python3 verify_samples_at_time.py <group_name> --time "2026-10-31 03:40:20" --month 2026-10

对比当时记录的采样点数和现在重新查询该时间点的实际采样点数
"""

import sys
import argparse
import requests
from datetime import datetime
import calendar
import json
from pathlib import Path

# 导入原脚本的函数以确保计算逻辑一致
sys.path.insert(0, str(Path(__file__).parent))
from zabbix_check_monthly_95th_quota import (
    get_auth_headers,
    get_hostid,
    get_item_info,
    get_item_history,
    bucket_samples,
    sum_across_interfaces,
    merge_direction_totals,
    summarize_quota,
    parse_delay_to_seconds,
    INTERFACE_PAIRS,
    ZABBIX_API_URL
)


def verify_at_time(group_name, target_time, target_month):
    """验证指定时间点的采样数据（使用原脚本完全相同的计算逻辑）"""
    if group_name not in INTERFACE_PAIRS:
        print(f"ERROR: Unknown group '{group_name}'. Available: {list(INTERFACE_PAIRS.keys())}", file=sys.stderr)
        sys.exit(1)

    cfg = INTERFACE_PAIRS[group_name]
    interfaces = cfg["interfaces"]
    thresholds_bps = [t * 1_000_000 for t in cfg["thresholds_mbps"]]

    # 解析目标时间
    verify_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")

    # 解析统计月份
    year, month = map(int, target_month.split("-"))
    month_start = datetime(year, month, 1, 0, 0, 0)
    days_in_month = calendar.monthrange(year, month)[1]

    time_from = int(month_start.timestamp())
    time_till = int(verify_time.timestamp())

    print(f"=" * 80)
    print(f"验证时间: {target_time}")
    print(f"统计月份: {target_month}")
    print(f"查询范围: {month_start.strftime('%Y-%m-%d %H:%M:%S')} ~ {target_time}")
    print(f"=" * 80)
    print()

    # 获取 token 和 headers（从原脚本）
    from zabbix_check_monthly_95th_quota import ZABBIX_TOKEN
    headers = get_auth_headers(ZABBIX_TOKEN)

    # 拉取每个接口的数据（完全复用原脚本逻辑）
    in_per_interface = []
    out_per_interface = []
    delay_seconds = None

    for iface in interfaces:
        host = iface["host"]
        port_id = iface["port_id"]

        print(f"[{host}] 正在拉取数据...")

        hostid = get_hostid(ZABBIX_API_URL, headers, host)

        item_infos = {}
        for direction in ("in", "out"):
            key = f"net.if.{direction}[{port_id}]"
            item_infos[direction] = get_item_info(ZABBIX_API_URL, headers, hostid, host, key)

        if delay_seconds is None:
            delay_seconds = item_infos["in"]["delay_seconds"]

        history_in = get_item_history(
            ZABBIX_API_URL, headers,
            item_infos["in"]["itemid"],
            item_infos["in"]["value_type"],
            time_from, time_till
        )
        history_out = get_item_history(
            ZABBIX_API_URL, headers,
            item_infos["out"]["itemid"],
            item_infos["out"]["value_type"],
            time_from, time_till
        )

        print(f"  - in:  {len(history_in)} 条原始记录")
        print(f"  - out: {len(history_out)} 条原始记录")

        # 使用原脚本的 bucket_samples 函数
        in_per_interface.append(bucket_samples(history_in, delay_seconds))
        out_per_interface.append(bucket_samples(history_out, delay_seconds))

    print()
    print(f"-" * 80)

    # 使用原脚本的合并函数
    in_totals = sum_across_interfaces(in_per_interface)
    out_totals = sum_across_interfaces(out_per_interface)
    combined_samples = merge_direction_totals(in_totals, out_totals)
    combined_values = [v for _, v in combined_samples]

    # 使用原脚本的统计函数
    output = summarize_quota(combined_values, thresholds_bps, delay_seconds, days_in_month)

    print(f"[合并统计结果（使用原脚本计算逻辑）]")
    print(f"  采集间隔:              {delay_seconds}s")
    print(f"  合并后采样点数:        {output['total_samples']} 个")
    print(f"  当月总采样点:          {output['total_points_in_month']} 个")
    print(f"  95% 配额上限:          {output['quota_total']} 次")
    print()

    for threshold_bps in sorted(thresholds_bps, reverse=True):
        label = int(threshold_bps // 1_000_000)
        over_key = f"over_count_{label}"
        remaining_key = f"remaining_{label}"
        print(f"  超过 {label}M 的点数:      {output[over_key]:4d} 个")
        print(f"  剩余配额 ({label}M):        {output[remaining_key]:4d} 次")

    if output['percentile_95th_bps']:
        pv = output['percentile_95th_bps']
        print(f"\n  95 峰值:               {pv:,.0f} bps ({pv/1e9:.3f} Gbps)")

    print(f"=" * 80)

    # 输出完整 JSON
    output['verify_time'] = target_time
    print("\nJSON 输出(便于对比):")
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(description="验证指定时间点的历史采样完整性")
    parser.add_argument("group_name", help="接口组名(dc07/dc09/dc03)")
    parser.add_argument("--time", required=True, help="验证时间点(格式: 2026-10-31 03:40:20)")
    parser.add_argument("--month", required=True, help="统计月份(格式: 2026-10)")

    args = parser.parse_args()
    verify_at_time(args.group_name, args.time, args.month)


if __name__ == "__main__":
    main()
