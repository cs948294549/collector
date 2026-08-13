# 快速开始指南

本指南将帮助你快速部署和运行 SNMP Collector。

## 环境要求

- Python 3.7+
- MySQL 5.7+ 或 MariaDB 10.0+
- Linux 系统（推荐，aiosnmp 在 macOS 上可能无法正常工作）
- 网络设备支持 SNMP v2c

## 快速部署步骤

### 1. 数据库初始化

```bash
# 登录 MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE network_monitor DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 导入表结构
USE network_monitor;
SOURCE /path/to/collector/sql/init.sql;

# 退出
EXIT;
```

### 2. 配置数据库连接

编辑 `config/config.py`：

```python
db_config = {
    "host": "localhost",      # 数据库地址
    "port": 3306,            # 数据库端口
    "user": "root",          # 数据库用户
    "password": "your_pass", # 数据库密码
    "dbname": "network_monitor",
    "charset": "utf8mb4"
}
```

### 3. 添加设备到设备列表

```sql
INSERT INTO iplist (ip, sysname, community, admin_status, timestamp) VALUES
('192.168.1.1', 'core-switch-01', 'public', '0', NOW()),
('192.168.1.2', 'access-switch-01', 'public', '0', NOW()),
('192.168.1.3', 'router-01', 'public', '0', NOW());
```

### 4. 安装依赖

```bash
cd /path/to/collector
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 5. 测试单个脚本

在启动整个调度器之前，建议先测试单个脚本：

```bash
# 测试设备信息采集
python3 -m scripts.collect_device

# 测试端口信息采集
python3 -m scripts.collect_port
```

### 6. 启动采集器

```bash
# 前台运行（调试用）
python3 main.py

# 后台运行
nohup python3 main.py > collector.log 2>&1 &

# 查看日志
tail -f logs/scheduler.log
tail -f logs/collector.log
```

## 使用 systemd 管理（生产环境推荐）

### 创建服务文件

创建 `/etc/systemd/system/snmp-collector.service`：

```ini
[Unit]
Description=SNMP Collector Service
After=network.target mysql.service

[Service]
Type=simple
User=your_user
Group=your_group
WorkingDirectory=/path/to/collector
ExecStart=/usr/bin/python3 /path/to/collector/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start snmp-collector

# 查看状态
sudo systemctl status snmp-collector

# 设置开机自启
sudo systemctl enable snmp-collector

# 查看日志
sudo journalctl -u snmp-collector -f
```

### 管理服务

```bash
# 停止服务
sudo systemctl stop snmp-collector

# 重启服务
sudo systemctl restart snmp-collector

# 重新加载配置（修改 task_config.yaml 后）
sudo systemctl restart snmp-collector
```

## 任务配置说明

编辑 `config/task_config.yaml` 可以调整任务调度：

```yaml
- id: collect_device_info      # 任务唯一ID
  type: cron                    # 调度类型: cron 或 interval
  module: scripts.collect_device # 脚本模块
  function: run                 # 执行函数
  schedule: "0 */1 * * *"      # Cron 表达式
  description: "采集设备信息"   # 任务描述
  enabled: true                 # 是否启用
```

### Cron 表达式示例

```
*/5 * * * *    - 每5分钟
0 */1 * * *    - 每小时
0 */2 * * *    - 每2小时
0 0 * * *      - 每天0点
0 2 * * *      - 每天凌晨2点
```

### Interval 调度示例

```yaml
schedule:
  hours: 0      # 间隔小时数
  minutes: 10   # 间隔分钟数
  seconds: 0    # 间隔秒数
```

## 默认任务列表

| 任务ID | 任务描述 | 调度频率 | 数据表 |
|--------|---------|---------|--------|
| collect_device_info | 设备基础信息 | 每小时 | devices |
| collect_arp_table | ARP表 | 每30分钟 | arps |
| collect_mac_table | MAC地址表 | 每30分钟 | macs |
| collect_port_status | 端口状态 | 每10分钟 | ports |
| collect_lldp | LLDP邻居 | 每2小时 | lldps |
| collect_route_table | 路由表 | 每6小时 | routes |
| collect_gate_info | 网关信息 | 每4小时 | gates, gates_ipv6 |
| collect_physical_info | 设备物理信息 | 每天0点 | dev_sn |
| clean_old_data | 数据清理 | 每天凌晨2点 | 所有表 |

## 常见问题

### 1. 任务未执行

**检查项**：
- 任务是否启用（`enabled: true`）
- Cron 表达式是否正确
- 查看日志文件获取错误信息

```bash
tail -f logs/scheduler.log
```

### 2. SNMP 采集失败

**检查项**：
- 设备 SNMP 是否开启
- Community 字符串是否正确
- 网络连通性是否正常
- 防火墙是否允许 UDP 161 端口

**测试命令**：
```bash
snmpwalk -v2c -c public 192.168.1.1 system
```

### 3. 数据库连接失败

**检查项**：
- 数据库服务是否运行
- 配置文件中的连接信息是否正确
- 数据库用户是否有足够权限

```sql
-- 授权示例
GRANT ALL PRIVILEGES ON network_monitor.* TO 'user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. 内存占用过高

**优化建议**：
- 调整并发数 `config/config.py` 中的 `max_workers`
- 增加采集间隔时间
- 清理过期数据

### 5. aiosnmp 在 macOS 上无法使用

aiosnmp 依赖的底层库在 macOS 上可能存在兼容性问题。

**解决方案**：
- 在 Linux 环境运行（推荐）
- 使用 Docker 容器运行
- 使用虚拟机运行

## 监控和维护

### 查看日志

```bash
# 调度器日志
tail -f logs/scheduler.log

# 采集器主日志
tail -f logs/collector.log

# systemd 日志
sudo journalctl -u snmp-collector -f
```

### 查看数据库

```sql
-- 查看设备信息
SELECT * FROM devices;

-- 查看最新采集时间
SELECT ip, sysname, timestamp FROM devices ORDER BY timestamp DESC;

-- 统计各表记录数
SELECT 
    (SELECT COUNT(*) FROM devices) AS devices,
    (SELECT COUNT(*) FROM ports) AS ports,
    (SELECT COUNT(*) FROM arps) AS arps,
    (SELECT COUNT(*) FROM macs) AS macs,
    (SELECT COUNT(*) FROM routes) AS routes,
    (SELECT COUNT(*) FROM lldps) AS lldps;
```

### 性能优化

1. **数据库索引**：已在 `init.sql` 中创建必要索引
2. **定期清理**：`clean_data` 任务会清理30天前的数据
3. **批量操作**：使用 `executemany` 批量插入数据
4. **并发控制**：根据设备数量和网络情况调整 `max_workers`

## 备份策略

### 数据库备份

```bash
# 备份整个数据库
mysqldump -u root -p network_monitor > backup_$(date +%Y%m%d).sql

# 只备份表结构
mysqldump -u root -p --no-data network_monitor > schema.sql

# 恢复备份
mysql -u root -p network_monitor < backup_20260813.sql
```

### 配置文件备份

```bash
# 备份配置目录
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/

# 恢复配置
tar -xzf config_backup_20260813.tar.gz
```

## 扩展开发

### 添加新的采集任务

1. 在 `scripts/` 目录创建新脚本
2. 实现 `async def run()` 函数
3. 在 `config/task_config.yaml` 添加任务配置
4. 如需保存新数据，在 `utils/db_helper.py` 添加保存方法
5. 重启服务

详细说明请查看 `scripts/README.md`

## 技术支持

遇到问题请查看：
- 项目 README.md
- scripts/README.md
- logs/ 目录下的日志文件

## 更新日志

- 2026-08-13: 初始版本发布
