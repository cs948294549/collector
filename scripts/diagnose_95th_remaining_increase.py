#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 95 峰值配额剩余点位在同周期内上升的异常现象

用法:
  python3 diagnose_95th_remaining_increase.py <group_name> [--days N]

示例:
  python3 diagnose_95th_remaining_increase.py dc07 --days 3
"""

import sys
import argparse
import requests
from datetime import datetime, timedelta
import calendar

ZABBIX_API_URL = "http://10.35.112.170:8080/api_jsonrpc.php"
ZABBIX_TOKEN = "9529e553773f5f589746a480ded256415983516730c9c35ac30f101253c7fbbf"

# 复用主脚本的接口配置
INTERFACE_PAIRS = {
    "dc07": {
        "interfaces": [
            {"host": "pcs1_dc07_m01.vdian.net", "port_id": "436231168"},
            {"host": "pcs2_dc07_m01.vdian.net", "port_id": "436231168"},
        ],
        "thresholds_mbps": [600, 700, 800, 900, 1000, 1200, 1500],
    },
    "dc09": {
        "interfaces": [
            {"host": "pcs1_dc09_m01", "port_id": "436231168"},
            {"host": "pcs2_dc09_m01", "port_id": "436231168"},
        ],
        "thresholds_mbps": [100, 200, 300],
    },
    "dc03": {
        "interfaces": [
            {"host": "pcs1_dc03_m02", "port_id": "436231168"},
            {"host": "pcs2_dc03_m02", "port_id": "436231168"},
        ],
        "thresholds_mbps": [20, 40, 80],
    },
}


def get_auth_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZABBIX_TOKEN}"
    }


def zabbix_call(method, params):
    """通用 Zabbix API 调用"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    headers = get_auth_headers()
    response = requests.post(ZABBIX_API_URL, json=payload, headers=headers, timeout=30)
    result = response.json()
    if "error" in result:
        raise Exception(f"Zabbix API error: {result['error']}")
    return result.get("result", [])


def get_hostid(host):
    """查询主机 ID"""
    result = zabbix_call("host.get", {
        "filter": {"host": [host]},
        "output": ["hostid"]
    })
    if not result:
        raise Exception(f"Host '{host}' not found")
    return result[0]["hostid"]


def get_item_info(hostid, key_):
    """查询监控项信息"""
    result = zabbix_call("item.get", {
        "hostids": hostid,
        "filter": {"key_": key_},
        "output": ["itemid", "value_type", "delay"]
    })
    if not result:
        raise Exception(f"Item key '{key_}' not found for hostid {hostid}")
    return result[0]


def get_history(itemid, value_type, time_from, time_till):
    """拉取历史数据"""
    return zabbix_call("history.get", {
        "itemids": itemid,
        "time_from": time_from,
        "time_till": time_till,
        "output": "extend",
        "sortfield": "clock",
        "sortorder": "ASC",
        "history": value_type
    })


def parse_delay(delay_str):
    """解析采集间隔"""
    delay_str = str(delay_str).strip()
    if delay_str.endswith("s"):
        return int(delay_str[:-1])
    if delay_str.endswith("m"):
        return int(delay_str[:-1]) * 60
    if delay_str.endswith("h"):
        return int(delay_str[:-1]) * 3600
    return int(delay_str)


def bucket_and_merge(interfaces, time_from, time_till, delay_seconds):
    """拉取多接口数据并按时间桶合并（复用主脚本逻辑）"""
    from zabbix_check_monthly_95th_quota import (
        bucket_samples, sum_across_interfaces, merge_direction_totals
    )

    in_per_interface = []
    out_per_interface = []

    for iface in interfaces:
        host = iface["host"]
        port_id = iface["port_id"]
        hostid = get_hostid(host)

        item_in = get_item_info(hostid, f"net.if.in[{port_id}]")
        item_out = get_item_info(hostid, f"net.if.out[{port_id}]")

        hist_in = get_history(item_in["itemid"], item_in["value_type"], time_from, time_till)
        hist_out = get_history(item_out["itemid"], item_out["value_type"], time_from, time_till)

        in_per_interface.append(bucket_samples(hist_in, delay_seconds))
        out_per_interface.append(bucket_samples(hist_out, delay_seconds))

    in_totals = sum_across_interfaces(in_per_interface)
    out_totals = sum_across_interfaces(out_per_interface)
    combined_samples = merge_direction_totals(in_totals, out_totals)
    return [v for _, v in combined_samples]


def calculate_remaining(values, threshold_bps, quota_total):
    """计算某阈值的剩余配额点数"""
    if not values:
        return quota_total
    over_count = sum(1 for v in values if v > threshold_bps)
    return max(0, quota_total - over_count)


def diagnose_increase(group_name, days=3, target_month=None):
    """主诊断逻辑"""
    if group_name not in INTERFACE_PAIRS:
        print(f"ERROR: Unknown group '{group_name}'. Available: {list(INTERFACE_PAIRS.keys())}", file=sys.stderr)
        sys.exit(1)

    cfg = INTERFACE_PAIRS[group_name]
    interfaces = cfg["interfaces"]
    threshold_mbps = max(cfg["thresholds_mbps"])  # 取最高阈值
    threshold_bps = threshold_mbps * 1_000_000

    # 确定查询时间范围(当月)
    # 如果指定了 target_month (格式 "2026-10")，则使用该月最后时刻
    if target_month:
        year, month = map(int, target_month.split("-"))
        month_start = datetime(year, month, 1, 0, 0, 0)
        days_in_month = calendar.monthrange(year, month)[1]
        # 使用该月最后一秒作为 "now"
        now = datetime(year, month, days_in_month, 23, 59, 59)
    else:
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1, 0, 0, 0)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
    time_from = int(month_start.timestamp())
    time_till = int(now.timestamp())

    # 从第一个接口取采集间隔
    hostid = get_hostid(interfaces[0]["host"])
    item_info = get_item_info(hostid, f"net.if.in[{interfaces[0]['port_id']}]")
    delay_seconds = parse_delay(item_info["delay"])

    # 计算全月配额
    total_points_in_month = int(days_in_month * 86400 / delay_seconds)
    quota_total = int(total_points_in_month * 0.05)

    print(f"=" * 80)
    print(f"诊断组: {group_name}")
    print(f"阈值: {threshold_mbps}M ({threshold_bps:,} bps)")
    print(f"采集间隔: {delay_seconds}s")
    print(f"当月天数: {days_in_month}, 全月配额: {quota_total} 点")
    print(f"查询时间范围: {month_start.strftime('%Y-%m-%d %H:%M:%S')} ~ {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 80)

    # 按小时步进,对比相邻时刻的剩余点位
    print("\n开始按小时采样对比...\n")

    current_time = int((now - timedelta(days=days)).timestamp())
    end_time = time_till
    step = 3600  # 每小时检查一次

    prev_remaining = None
    prev_time = None
    prev_values = None
    anomalies = []

    while current_time <= end_time:
        # 拉取从月初到当前时刻的数据
        values = bucket_and_merge(interfaces, time_from, current_time, delay_seconds)
        remaining = calculate_remaining(values, threshold_bps, quota_total)

        ts = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')

        if prev_remaining is not None:
            delta = remaining - prev_remaining
            status = "↑↑ ANOMALY" if delta > 0 else "→" if delta == 0 else "↓"
            print(f"{ts}  remaining={remaining:4d}  (Δ={delta:+4d})  {status}")

            if delta > 0:
                anomalies.append({
                    "time": ts,
                    "prev_time": prev_time,
                    "prev_remaining": prev_remaining,
                    "curr_remaining": remaining,
                    "delta": delta,
                    "prev_samples": len(prev_values),
                    "curr_samples": len(values),
                    "sample_delta": len(values) - len(prev_values)
                })
        else:
            print(f"{ts}  remaining={remaining:4d}  (baseline)")

        prev_remaining = remaining
        prev_time = ts
        prev_values = values
        current_time += step

    # 总结异常
    print(f"\n{'=' * 80}")
    print(f"发现 {len(anomalies)} 处剩余点位上升异常:\n")

    for i, anom in enumerate(anomalies, 1):
        print(f"[{i}] {anom['prev_time']} → {anom['time']}")
        print(f"    remaining: {anom['prev_remaining']} → {anom['curr_remaining']} (↑ {anom['delta']})")
        print(f"    samples: {anom['prev_samples']} → {anom['curr_samples']} (Δ {anom['sample_delta']})")
        print()

    if not anomalies:
        print("  (未检测到剩余点位上升异常)")
    else:
        print("可能原因:")
        print("  1. 历史数据被手动删除或过期清理(housekeeper)")
        print("  2. 监控项配置变更导致 itemid 更换")
        print("  3. Zabbix 数据库回滚或数据损坏")
        print("  4. 脚本计算逻辑在边界条件下的 bug")


def main():
    parser = argparse.ArgumentParser(description="诊断 95 峰值配额剩余点位异常上升")
    parser.add_argument("group_name", help="接口组名(dc07/dc09/dc03)")
    parser.add_argument("--days", type=int, default=3, help="向前回溯天数(默认3天)")
    parser.add_argument("--month", type=str, help="指定统计月份(格式: 2026-10)，不指定则为当前月")

    args = parser.parse_args()
    diagnose_increase(args.group_name, args.days, args.month)


if __name__ == "__main__":
    main()
