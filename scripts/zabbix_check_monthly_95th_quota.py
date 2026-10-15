#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算当前自然月的 95 峰值剩余配额，并计算截至目前的 95 峰值。

流量口径:按端口统计,不区分方向。先把同一时刻的 in / out 两个方向取最大值,
得到该端口在该时刻的实际带宽占用,再基于这条合并后的曲线计算 95 峰值和超限次数。

用法:
  仅查询该主机可用的流量监控项 key:
    zabbix_check_monthly_95th_quota.py <host>

  计算配额与 95 峰值:
    zabbix_check_monthly_95th_quota.py <host> <port_id> <threshold_bps>
"""

import sys
import os
import re
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import calendar

# 将项目根目录加入 Python 路径，与其他 scripts/*.py 保持一致
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


ZABBIX_API_URL = "http://10.35.112.170:8080/api_jsonrpc.php"
ZABBIX_TOKEN = "9529e553773f5f589746a480ded256415983516730c9c35ac30f101253c7fbbf"

# 匹配 net.if.in[...] / net.if.out[...]，排除 .discards / .errors 等子指标
TRAFFIC_KEY_RE = re.compile(r'^net\.if\.(in|out)\[')


def parse_delay_to_seconds(delay_str):
    """将 Zabbix item 的 delay 字段（如 '1m'、'30s'、'60'）解析为秒数"""
    delay_str = str(delay_str).strip()
    if delay_str.endswith("s"):
        return int(delay_str[:-1])
    if delay_str.endswith("m"):
        return int(delay_str[:-1]) * 60
    if delay_str.endswith("h"):
        return int(delay_str[:-1]) * 3600
    return int(delay_str)


def get_auth_headers(token):
    """Zabbix 6.4+ 使用 Authorization: Bearer <token>，请求体里不再需要 auth 字段"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }


def get_hostid(url, headers, host):
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "filter": {"host": [host]},
            "output": ["hostid"]
        },
        "id": 2
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        if "error" in result:
            print(f"ERROR: Failed to get host: {result['error']}", file=sys.stderr)
            sys.exit(1)
        if "result" not in result or len(result["result"]) == 0:
            print(f"ERROR: Host '{host}' not found in Zabbix", file=sys.stderr)
            sys.exit(1)
        return result["result"][0]["hostid"]
    except Exception as e:
        print(f"ERROR: Cannot get host ID: {e}", file=sys.stderr)
        sys.exit(1)


def list_traffic_items(url, headers, host):
    """仅提供 host 时调用：列出该主机上可用于流量统计的监控项 key，供人工挑选"""
    hostid = get_hostid(url, headers, host)

    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "hostids": hostid,
            "search": {"key_": "net.if"},
            "searchByAny": True,
            "output": ["itemid", "name", "key_", "delay", "value_type"],
            "sortfield": "name"
        },
        "id": 10
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        result = response.json()
        if "error" in result:
            print(f"ERROR: Failed to get items: {result['error']}", file=sys.stderr)
            sys.exit(1)
        items = result.get("result", [])
    except Exception as e:
        print(f"ERROR: Cannot get items: {e}", file=sys.stderr)
        sys.exit(1)

    traffic_items = [it for it in items if TRAFFIC_KEY_RE.match(it["key_"])]
    traffic_items.sort(key=lambda x: x["name"])

    lines = []
    lines.append(f"主机: {host} (hostid={hostid})")
    lines.append(f"可用于流量统计的监控项 (net.if.in[...] / net.if.out[...])，共 {len(traffic_items)} 个：")
    lines.append("-" * 100)
    for it in traffic_items:
        lines.append(
            f"  key={it['key_']:<24}  delay={str(it.get('delay', 'N/A')):<6}  name={it.get('name', 'N/A')}"
        )
    lines.append("-" * 100)
    if not traffic_items:
        lines.append("  (未找到匹配 net.if.in[...] / net.if.out[...] 的监控项，"
                      "该主机可能未启用接口流量采集模板)")
    lines.append("")
    lines.append("用法: 从上面任意一行 key 里取出方括号中的端口 ID（如 net.if.in[436231168] 的 436231168），再执行：")
    lines.append(f"  python3 {os.path.basename(sys.argv[0])} {host} <port_id> <threshold_bps>")

    print("\n".join(lines))


def get_item_info(url, headers, hostid, host, item_key):
    """查询监控项的 itemid / value_type / delay / name"""
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "hostids": hostid,
            "filter": {"key_": item_key},
            "output": ["itemid", "name", "key_", "delay", "value_type"]
        },
        "id": 3
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()

        if "error" in result:
            print(f"ERROR: Failed to get item: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if "result" not in result or len(result["result"]) == 0:
            print(f"ERROR: Item with key '{item_key}' not found for host '{host}'", file=sys.stderr)
            print("提示: 不带参数重新运行本脚本，可列出该主机所有可用的流量监控项 key。",
                  file=sys.stderr)
            sys.exit(1)

        item_info = result["result"][0]
        return {
            "itemid": item_info["itemid"],
            "value_type": int(item_info.get("value_type", 3)),
            "delay_seconds": parse_delay_to_seconds(item_info.get("delay", "60")),
            "name": item_info.get("name", "N/A"),
        }
    except Exception as e:
        print(f"ERROR: Cannot get item ID: {e}", file=sys.stderr)
        sys.exit(1)


def get_item_history(url, headers, item_id, value_type, time_from, time_till):
    """获取监控项历史数据，返回 [{clock, value}, ...]（按时间升序）"""
    # value_type: 0=float, 1=character, 2=log, 3=unsigned, 4=text
    payload = {
        "jsonrpc": "2.0",
        "method": "history.get",
        "params": {
            "itemids": item_id,
            "time_from": time_from,
            "time_till": time_till,
            "output": "extend",
            "sortfield": "clock",
            "sortorder": "ASC",
            "history": value_type
        },
        "id": 4
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()

        if "error" in result:
            print(f"ERROR: Failed to get history: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if "result" not in result:
            print(f"ERROR: Unexpected history response: {result}", file=sys.stderr)
            sys.exit(1)

        return result["result"]
    except Exception as e:
        print(f"ERROR: Cannot get history data: {e}", file=sys.stderr)
        sys.exit(1)


def merge_direction_samples(history_in, history_out, delay_seconds):
    """把 in / out 两个方向的采样按时间点合并为一条曲线:同一时刻取两者最大值。
    某个时刻只有一个方向有采样时,该时刻取该方向的值(相当于另一方向为 0)。
    返回按时间升序的 [(clock, value), ...]

    合并的键按采集间隔取整(clock // delay * delay),而不是直接用 clock:
    两个方向是各自独立的 item,轮询落库时间会差 1~2 秒(一个 :20、一个 :21),
    直接按 clock 精确匹配会让这些点各占一个时间点,把样本数虚增约 5%。
    而配额上限(X)和丢弃点数都按样本数计算,样本数虚增会直接让结果算错。
    取整到采集间隔后,同一轮询周期的两个方向会落进同一个桶。"""
    merged = {}
    for history in (history_in, history_out):
        for record in history:
            bucket = int(record["clock"]) // delay_seconds * delay_seconds
            value = float(record["value"])
            if bucket not in merged or value > merged[bucket]:
                merged[bucket] = value
    return sorted(merged.items())


def calculate_95th_percentile(values, total_points_in_month):
    """计算当前 95 峰值。values 为按时间点取 in/out 最大值后的曲线。
    丢弃点数按当月完整周期的采样点数（total_points_in_month，
    与 calculate_quota_remaining 用的是同一个值）计算，而不是当前已采集的样本数，
    否则月末前因样本量不足会导致丢弃点数偏少、95 峰值虚高，无法与月末最终值对齐"""
    values = sorted(values)
    if not values:
        return None

    target_drop_count = int(total_points_in_month * 0.05)
    # 保护：月初等样本不足场景下，全月口径丢弃数可能超过实际样本数（甚至超过2倍），
    # Python 负数切片会导致 remaining_values 为空、remaining_values[-1] 抛 IndexError，
    # 这里把丢弃数压到 len(values)-1，保证至少保留1个点，不崩溃
    drop_count = min(target_drop_count, len(values) - 1)
    remaining_values = values[:len(values) - drop_count] if drop_count > 0 else values
    return {
        "percentile_95th_value": remaining_values[-1],
        "total_samples": len(values),
        "dropped_top_count": drop_count,
        "remaining_count": len(remaining_values),
        # 实际丢弃数被压缩过，说明样本量还远不够全月配额，此时的 95 峰值不可信
        "insufficient_samples": drop_count < target_drop_count
    }


def calculate_quota_remaining(values, threshold, delay_seconds, days_in_month):
    """计算剩余配额 M = quota_total - X
    quota_total 按当月实际天数和采集间隔动态计算：
    quota_total = (days_in_month * 86400 / delay_seconds) * 5%
    over_count 统计的是合并后的曲线（按时间点取 in/out 最大值）中超过阈值的次数
    """
    over_count = sum(1 for value in values if value > threshold)

    total_points_in_month = int(days_in_month * 86400 / delay_seconds)
    quota_total = int(total_points_in_month * 0.05)
    remaining = quota_total - over_count
    return {
        "remaining": remaining,
        "over_count": over_count,
        "total_samples": len(values),
        "quota_total": quota_total,
        "total_points_in_month": total_points_in_month,
        "usage_percent": round((over_count / quota_total) * 100, 2) if quota_total else 0
    }


def print_human_report(host, port_id, threshold, delay_seconds, days_in_month,
                        quota_result, percentile_result, query_from, query_till):
    """将本次运行的关键信息整理成一份人可读的文本报告，输出到 stderr
    （stdout 只保留最终数值，供 Zabbix external check 直接采集）"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"主机:           {host}")
    lines.append(f"端口 ID:        {port_id} (in/out 按时间点取最大值合并统计)")
    lines.append(f"统计区间:       {query_from} ~ {query_till} (自然月至今)")
    lines.append(f"采集间隔:       {delay_seconds}s")
    lines.append(f"当月天数:       {days_in_month}")
    lines.append(f"超限阈值:       {threshold:,.0f} bps ({threshold/1e9:.3f} Gbps)")
    lines.append("-" * 70)
    lines.append("[配额统计]")
    lines.append(f"  当月总采样点:         {quota_result['total_points_in_month']}")
    lines.append(f"  95% 配额上限:         {quota_result['quota_total']} 次")
    lines.append(f"  已采集样本数:         {quota_result['total_samples']}")
    lines.append(f"  已超限次数 (X):       {quota_result['over_count']}")
    lines.append(f"  剩余配额 (M):         {quota_result['remaining']}")
    lines.append(f"  配额使用率:           {quota_result['usage_percent']}%")
    lines.append("-" * 70)
    lines.append("[95 峰值（截至目前）]")
    if percentile_result:
        pv = percentile_result["percentile_95th_value"]
        lines.append(f"  95 峰值:              {pv:,.0f} bps ({pv/1e9:.3f} Gbps)")
        lines.append(f"  95% 配额(应丢弃点位数): {quota_result['quota_total']} "
                      f"/ {quota_result['total_points_in_month']} (全月)")
        lines.append(f"  丢弃的最高样本数:     {percentile_result['dropped_top_count']} "
                      f"/ {percentile_result['total_samples']}")
        lines.append("  注意: 该值基于月初至当前时刻的数据，月末最终值可能更高。")
    else:
        lines.append("  (无历史数据，无法计算)")
    lines.append("=" * 70)
    print("\n".join(lines), file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  查询可选监控项 key:   {os.path.basename(sys.argv[0])} <host>")
        print(f"  计算配额与 95 峰值:   {os.path.basename(sys.argv[0])} <host> <port_id> <threshold_bps>")
        sys.exit(1)

    host = sys.argv[1]

    if not ZABBIX_TOKEN:
        print("ERROR: config/config.py 中 zabbix_config['api_token'] 未配置", file=sys.stderr)
        sys.exit(1)
    headers = get_auth_headers(ZABBIX_TOKEN)

    # 只提供了 host：列出可选的监控项 key，不做计算
    if len(sys.argv) == 2:
        list_traffic_items(ZABBIX_API_URL, headers, host)
        sys.exit(0)

    if len(sys.argv) < 4:
        print(f"用法: {os.path.basename(sys.argv[0])} <host> <port_id> <threshold_bps>", file=sys.stderr)
        sys.exit(1)

    port_id = sys.argv[2]
    threshold = float(sys.argv[3])

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1, 0, 0, 0)
    days_in_month = calendar.monthrange(now.year, now.month)[1]

    time_from = int(month_start.timestamp())
    # time_from = int((now - timedelta(days=30)).timestamp())
    time_till = int(now.timestamp())

    hostid = get_hostid(ZABBIX_API_URL, headers, host)

    # 分别取 in / out 的历史数据，再按时间点合并（取最大值），得到该端口的实际带宽曲线
    item_infos = {}
    for direction in ("in", "out"):
        key = "net.if.{}[{}]".format(direction, port_id)
        item_infos[direction] = get_item_info(ZABBIX_API_URL, headers, hostid, host, key)

    history_in = get_item_history(
        ZABBIX_API_URL, headers, item_infos["in"]["itemid"],
        item_infos["in"]["value_type"], time_from, time_till
    )
    history_out = get_item_history(
        ZABBIX_API_URL, headers, item_infos["out"]["itemid"],
        item_infos["out"]["value_type"], time_from, time_till
    )

    delay_seconds = item_infos["in"]["delay_seconds"]
    merged_samples = merge_direction_samples(history_in, history_out, delay_seconds)
    merged_values = [value for _, value in merged_samples]

    quota_result = calculate_quota_remaining(merged_values, threshold, delay_seconds, days_in_month)
    percentile_result = calculate_95th_percentile(merged_values, quota_result["total_points_in_month"])

    # print_human_report(
    #     host, port_id, threshold, delay_seconds, days_in_month,
    #     quota_result, percentile_result,
    #     month_start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")
    # )

    # stdout 输出一份 JSON，供 Zabbix external check 采集；
    # Zabbix 侧用一个主监控项采集这份 JSON，再用多个依赖项通过 JSONPath 拆出各字段，
    # 避免同时对接告警和图表时重复调用本脚本（每次调用都会拉取整月历史数据）。
    output = dict(quota_result)
    output["percentile_95th_bps"] = percentile_result["percentile_95th_value"] if percentile_result else None
    print(json.dumps(output))



if __name__ == "__main__":
    main()

    #pcs1_dc07_m01.vdian.net 436231168 600000000
    #pcs2_dc07_m01.vdian.net 436231168 600000000
