# SNMP Collector - 网络设备信息采集器

通过定时任务采集设备列表的基础数据，为搜索提供依据
11
## 项目结构

```
collector/
├── main.py                 # 主程序入口
├── scheduler.py            # 任务调度器
├── requirements.txt        # 依赖包
├── README.md              # 项目说明
├── config/                # 配置文件目录
│   ├── config.py          # 基础配置
│   └── task_config.yaml   # 任务配置
├── Module/                # 采集模块
│   ├── Device.py          # 设备信息采集
│   ├── ARP.py             # ARP表采集
│   ├── ARPv6.py           # IPv6邻居表采集
│   ├── MAC.py             # MAC地址表采集
│   ├── Port.py            # 端口状态采集
│   ├── Route.py           # 路由表采集
│   ├── LLDP.py            # LLDP邻居信息采集
│   ├── Gate.py            # 网关信息采集
│   └── Physical.py        # 物理接口信息采集
├── scripts/               # 任务脚本目录
│   ├── __init__.py
│   ├── collect_device.py  # 设备信息采集任务
│   ├── collect_arp.py     # ARP表采集任务
│   ├── collect_mac.py     # MAC地址表采集任务
│   ├── collect_port.py    # 端口状态采集任务
│   ├── collect_route.py   # 路由表采集任务
│   ├── collect_lldp.py    # LLDP信息采集任务
│   └── clean_data.py      # 数据清理任务
├── utils/                 # 工具类
│   ├── snmp_tool.py       # SNMP工具
│   └── db_helper.py       # 数据库辅助类
└── logs/                  # 日志目录
    ├── scheduler.log      # 调度器日志
    └── collector.log      # 采集器日志
```

## 功能特性

- **异步采集**: 基于 aiosnmp 实现高效的异步 SNMP 采集
- **任务调度**: 使用 APScheduler 支持 cron 和 interval 两种调度方式
- **模块化设计**: 采集逻辑与任务脚本分离，易于扩展
- **配置化管理**: 通过 YAML 配置文件管理所有任务
- **并发控制**: 支持批量并发采集，可配置并发数
- **日志记录**: 完整的日志记录，便于监控和排查问题

## 安装依赖

```bash
python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**注意**: aiosnmp 包在 macOS 上可能无法使用，建议在 Linux 环境运行。

## 配置说明

### 1. 数据库配置

**首次使用**，需要复制配置示例文件：

```bash
# 复制配置示例
cp config/config_example.py config/config.py

# 编辑配置文件
vim config/config.py
```

编辑 `config/config.py` 配置数据库连接信息：

```python
db_config = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "your_password",  # 修改为实际密码
    "dbname": "network_monitor",
    "charset": "utf8mb4"
}
```

**注意**: 
- `config/config.py` 已添加到 `.gitignore`，不会被提交到 Git
- `config/config_example.py` 是配置模板，可以提交到 Git

### 2. 任务配置

编辑 `config/task_config.yaml` 配置定时任务：

```yaml
tasks:
  - id: collect_device_info          # 任务ID（唯一）
    type: cron                        # 调度类型: cron 或 interval
    module: scripts.collect_device    # 脚本模块路径
    function: run                     # 执行函数名
    schedule: "0 */1 * * *"          # cron表达式（每小时执行）
    description: "采集设备基础信息"   # 任务描述
    enabled: true                     # 是否启用
```

**cron 表达式格式**: `分 时 日 月 星期`
- `0 */1 * * *` - 每小时执行
- `*/30 * * * *` - 每30分钟执行
- `0 2 * * *` - 每天凌晨2点执行

**interval 调度格式**:
```yaml
schedule:
  hours: 0
  minutes: 10
  seconds: 0
```

## 运行

### 启动采集器

```bash
python3 main.py
```

### 后台运行

```bash
nohup python3 main.py > collector.log 2>&1 &
```

### 使用 systemd 管理（推荐）

创建服务文件 `/etc/systemd/system/collector.service`:

```ini
[Unit]
Description=SNMP Collector Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/collector
ExecStart=/usr/bin/python3 /path/to/collector/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start collector
sudo systemctl enable collector
sudo systemctl status collector
```

## 添加新任务

### 1. 创建任务脚本

在 `scripts/` 目录下创建新的采集脚本，例如 `collect_vlan.py`:

```python
import asyncio
import logging
from utils.db_helper import DBHelper

logger = logging.getLogger(__name__)

async def run():
    """主执行函数"""
    logger.info("开始执行VLAN采集任务")
    
    try:
        # 实现采集逻辑
        pass
    except Exception as e:
        logger.error(f"VLAN采集任务失败: {e}")
```

### 2. 配置任务

在 `config/task_config.yaml` 添加任务配置：

```yaml
  - id: collect_vlan
    type: cron
    module: scripts.collect_vlan
    function: run
    schedule: "0 */4 * * *"
    description: "采集VLAN信息"
    enabled: true
```

### 3. 重启服务

```bash
sudo systemctl restart collector
```

## 调度器 API

### 添加 cron 任务

```python
scheduler.add_cron_task(
    task_id="task_id",
    module_path="scripts.module_name",
    function_name="run",
    cron_expr="0 */1 * * *",
    description="任务描述"
)
```

### 添加间隔任务

```python
scheduler.add_interval_task(
    task_id="task_id",
    module_path="scripts.module_name",
    function_name="run",
    hours=1,
    minutes=0,
    seconds=0,
    description="任务描述"
)
```

### 其他操作

```python
# 移除任务
scheduler.remove_task("task_id")

# 暂停任务
scheduler.pause_task("task_id")

# 恢复任务
scheduler.resume_task("task_id")

# 获取所有任务
tasks = scheduler.get_tasks()
```

## 日志查看

```bash
# 查看调度器日志
tail -f logs/scheduler.log

# 查看采集器日志
tail -f logs/collector.log
```

## 故障排查

### 1. 任务未执行

- 检查任务是否启用 (`enabled: true`)
- 检查 cron 表达式是否正确
- 查看日志文件中的错误信息

### 2. SNMP 采集失败

- 确认设备 SNMP 配置正确
- 检查 community 字符串是否正确
- 确认网络连通性
- 查看超时和重试配置

### 3. 数据库连接失败

- 检查数据库配置信息
- 确认数据库服务运行正常
- 检查用户权限

## 最后更新

2026-08-13
