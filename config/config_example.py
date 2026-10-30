"""
数据库配置示例
复制此文件为 config.py 并修改相应配置
"""

# 数据库配置
db_config = {
    "host": "localhost",      # 数据库地址
    "port": 3306,            # 数据库端口
    "user": "root",          # 数据库用户
    "password": "your_password",  # 数据库密码（必须修改）
    "dbname": "network_monitor",  # 数据库名称
    "charset": "utf8mb4"
}

# SNMP 默认配置
snmp_config = {
    "community": "public",   # 默认 Community 字符串
    "version": 2,           # SNMP 版本
    "timeout": 5,           # 超时时间（秒）
    "retries": 2            # 重试次数
}

# 并发配置
concurrency_config = {
    "max_workers": 50,      # 最大并发数（根据设备数量和网络情况调整）
    "batch_size": 100       # 批次大小
}

# 飞塔 FortiGate REST 接口配置
# 用于补 SNMP MIB 拿不到的数据（信道利用率 / LLDP 邻居 / 终端真实 VLAN）
# 关闭或某台设备没配 token 时，自动降级为纯 SNMP 采集，飞塔独有字段留 None
fortinet_config = {
    "enabled": False,        # 总开关，先关着，配好 token 再打开
    "port": 443,             # admin 端口
    "vdom": "root",          # 多 VDOM 且无线跑在非 root 时改这里
    "timeout": 15,           # 单次请求超时（秒）
    "verify_ssl": False,     # 设备是自签证书，默认不校验
    # 按 FortiGate 管理 IP（对应 wifi_ac.mgmt_ip）配 token，一台一份
    # 生成方式：config system api-user → execute api-user generate-key <name>
    "tokens": {
        "172.19.2.8": "your_fortigate_api_token_here",
    },
}

# Zabbix API 配置
zabbix_config = {
    "api_url": "http://10.35.112.170:8080/api_jsonrpc.php",
    "api_token": "your_zabbix_api_token_here",  # Zabbix Web -> Users -> API tokens 创建，必须修改
}
