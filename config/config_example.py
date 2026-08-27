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

# Zabbix API 配置
zabbix_config = {
    "api_url": "http://10.35.112.170:8080/api_jsonrpc.php",
    "token": "your_zabbix_api_token_here",  # Zabbix Web -> Users -> API tokens 创建，必须修改
}
