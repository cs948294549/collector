#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多接口合并计算当前自然月的 95 峰值剩余配额。

流量口径：同一接口先把 in/out 按时间点取最大值，再将多台设备的带宽曲线求和，
基于合并后的总带宽曲线计算 95 峰值和超限次数。

用法:
  查询某主机可用的流量监控项 key:
    zabbix_check_monthly_95th_quota.py <host>

  计算多接口合并配额与 95 峰值（组名见脚本内 INTERFACE_PAIRS）:
    zabbix_check_monthly_95th_quota.py <group_name>

/usr/lib/zabbix/externalscripts/zabbix_check_monthly_95th_quota.py
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

# 多接口合并配置：key 为组名，每组含接口列表和阈值梯度（Mbps）
# 运行时传入组名即可，如: python3 zabbix_check_monthly_95th_quota.py dc07
INTERFACE_PAIRS = {
    "dc07": {
        "interfaces": [
            {"host": "pcs1_dc07_m01.vdian.net", "port_id": "436231168"},
            {"host": "pcs2_dc07_m01.vdian.net", "port_id": "436231168"},
        ],
        "thresholds_mbps": [600, 700, 800, 900, 1000],
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
    lines.append("用法: 从上面任意一行 key 里取出方括号中的端口 ID（如 net.if.in[436231168] 的 436231168），"
                 "填入脚本里的 INTERFACE_PAIRS 配置，再执行：")
    lines.append(f"  python3 {os.path.basename(sys.argv[0])} <group_name>")

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


def sum_multi_interface_samples(per_interface_samples):
    """将多台设备的带宽曲线按时间点求和，返回合并后的总带宽曲线。
    每条曲线已由 merge_direction_samples 按采集间隔对齐，直接按 clock 求和即可；
    某台设备在某时间点缺采样时按 0 计（相当于该设备此刻无流量）。"""
    summed = {}
    for samples in per_interface_samples:
        for clock, value in samples:
            summed[clock] = summed.get(clock, 0) + value
    return sorted(summed.items())


def summarize_quota(values, thresholds_bps, delay_seconds, days_in_month):
    """对合并后的总带宽曲线只排序一次，同时算出 95 峰值和各阈值梯度的超限次数。

    quota_total 按当月实际天数和采集间隔动态计算：
    quota_total = (days_in_month * 86400 / delay_seconds) * 5%

    各阈值的超限次数在同一个有序数组上按阈值降序推进下标一次扫完，阈值再多也只排一次序。

    95 峰值的丢弃点数按当月完整周期的采样点数计算，而不是当前已采集的样本数，
    否则月末前因样本量不足会导致丢弃点数偏少、95 峰值虚高，无法与月末最终值对齐。
    """
    total_points_in_month = int(days_in_month * 86400 / delay_seconds)
    quota_total = int(total_points_in_month * 0.05)

    result = {
        "total_points_in_month": total_points_in_month,
        "quota_total": quota_total,
        "total_samples": len(values),
        "percentile_95th_bps": None,
    }

    if not values:
        for threshold_bps in thresholds_bps:
            label = int(threshold_bps // 1_000_000)
            result[f"over_count_{label}"] = 0
            result[f"remaining_{label}"] = quota_total
        return result

    ordered_desc = sorted(values, reverse=True)

    # 保护：月初等样本不足场景下，全月口径丢弃数可能超过实际样本数（甚至超过2倍），
    # 负数索引会越界，这里把丢弃数压到 len-1，保证至少保留1个点
    target_drop_count = quota_total
    drop_count = min(target_drop_count, len(ordered_desc) - 1)
    # 降序数组里下标 D 处的元素，就是升序数组里丢弃掉最大的 D 个之后的第一个值
    result["percentile_95th_bps"] = ordered_desc[drop_count]

    # 降序数组里「> 阈值」的元素构成一个前缀。阈值从大到小处理，
    # 前缀只会变长，下标单调右移，整个循环下来每个元素最多被扫一次
    idx = 0
    for threshold_bps in sorted(thresholds_bps, reverse=True):
        while idx < len(ordered_desc) and ordered_desc[idx] > threshold_bps:
            idx += 1
        label = int(threshold_bps // 1_000_000)
        result[f"over_count_{label}"] = idx
        # 超限点数超过当月配额时余量归零，不再显示负数
        result[f"remaining_{label}"] = max(0, quota_total - idx)

    return result


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
        print(f"  计算多接口合并配额:   {os.path.basename(sys.argv[0])} <group_name>")
        print(f"  可用组名: {list(INTERFACE_PAIRS.keys())}")
        sys.exit(1)

    if not ZABBIX_TOKEN:
        print("ERROR: ZABBIX_TOKEN 未配置", file=sys.stderr)
        sys.exit(1)
    headers = get_auth_headers(ZABBIX_TOKEN)

    arg = sys.argv[1]

    # 单独传 host 时，列出该主机可用监控项 key
    if arg not in INTERFACE_PAIRS:
        list_traffic_items(ZABBIX_API_URL, headers, arg)
        sys.exit(0)

    group_name = arg
    group_cfg = INTERFACE_PAIRS[group_name]
    interfaces = group_cfg["interfaces"]
    thresholds_bps = [t * 1_000_000 for t in group_cfg["thresholds_mbps"]]

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1, 0, 0, 0)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    time_from = int(month_start.timestamp())
    time_till = int(now.timestamp())

    # 拉取每个接口的历史数据，in/out 合并后得到该接口的带宽曲线
    per_interface_samples = []
    delay_seconds = None
    for iface in interfaces:
        host = iface["host"]
        port_id = iface["port_id"]
        hostid = get_hostid(ZABBIX_API_URL, headers, host)

        item_infos = {}
        for direction in ("in", "out"):
            key = f"net.if.{direction}[{port_id}]"
            item_infos[direction] = get_item_info(ZABBIX_API_URL, headers, hostid, host, key)

        if delay_seconds is None:
            delay_seconds = item_infos["in"]["delay_seconds"]

        history_in = get_item_history(
            ZABBIX_API_URL, headers, item_infos["in"]["itemid"],
            item_infos["in"]["value_type"], time_from, time_till
        )
        history_out = get_item_history(
            ZABBIX_API_URL, headers, item_infos["out"]["itemid"],
            item_infos["out"]["value_type"], time_from, time_till
        )
        merged = merge_direction_samples(history_in, history_out, delay_seconds)
        per_interface_samples.append(merged)

    # 多接口按时间点求和，得到总带宽曲线
    combined_samples = sum_multi_interface_samples(per_interface_samples)
    combined_values = [v for _, v in combined_samples]

    # 只排序一次，同时算出 95 峰值和各阈值梯度的剩余配额点数
    output = summarize_quota(combined_values, thresholds_bps, delay_seconds, days_in_month)
    # 合并后数组的最后一个点，即当前时刻的合并带宽值
    output["current_bps"] = combined_samples[-1][1] if combined_samples else None

    print(json.dumps(output))


if __name__ == "__main__":
    main()

