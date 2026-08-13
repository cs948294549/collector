# SNMP Collector Docker 部署

本目录包含用于构建、启动和管理 SNMP Collector Docker 容器的脚本。

## 脚本列表

### app_build.sh
构建 Docker 镜像

```bash
./docker/app_build.sh [tag]
```

**参数:**
- `tag`: 镜像标签（默认: v1）

**示例:**
```bash
./docker/app_build.sh v1
```

### app_start.sh
启动 Docker 容器

```bash
./docker/app_start.sh [tag]
```

**参数:**
- `tag`: 镜像标签（默认: v1）

**环境变量:**
- `COLLECTOR_DATA_DIR`: 数据目录路径（默认: /root/docker_apps/snmp_collector）
- `DB_HOST`: 数据库地址（默认: localhost）
- `DB_PORT`: 数据库端口（默认: 3306）
- `DB_USER`: 数据库用户（默认: root）
- `DB_PASSWORD`: 数据库密码（必填）
- `DB_NAME`: 数据库名称（默认: network_monitor）

**示例:**
```bash
# 基本启动
DB_PASSWORD="your_password" ./docker/app_start.sh

# 指定数据库配置
DB_HOST="192.168.1.100" \
DB_PORT="3306" \
DB_USER="collector" \
DB_PASSWORD="your_password" \
DB_NAME="network_monitor" \
./docker/app_start.sh v1

# 使用自定义数据目录
COLLECTOR_DATA_DIR=/data/snmp_collector \
DB_PASSWORD="your_password" \
./docker/app_start.sh
```

### logs.sh
日志查看和管理工具

```bash
./docker/logs.sh [选项]
```

**选项:**
- `follow, -f`: 实时跟踪 Docker 日志（默认）
- `tail [N]`: 查看最后 N 行日志（默认 100）
- `app`: 查看应用日志文件列表
- `scheduler`: 实时跟踪调度器日志
- `collector`: 实时跟踪采集器日志
- `error`: 查看错误日志
- `search [keyword]`: 搜索包含关键字的日志
- `clear`: 清空应用日志文件
- `help, -h`: 显示帮助信息

**示例:**
```bash
# 实时查看 Docker 日志
./docker/logs.sh

# 查看最后 200 行
./docker/logs.sh tail 200

# 列出应用日志文件
./docker/logs.sh app

# 实时查看调度器日志
./docker/logs.sh scheduler

# 实时查看采集器日志
./docker/logs.sh collector

# 查看错误日志
./docker/logs.sh error

# 搜索关键字
./docker/logs.sh search "设备"

# 清空日志
./docker/logs.sh clear
```

## 快速开始

### 1. 准备数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE network_monitor DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 导入表结构
mysql -u root -p network_monitor < sql/init.sql

# 添加设备列表
mysql -u root -p network_monitor -e "
INSERT INTO device_list (ip, sysname, community, admin_status) VALUES
('192.168.1.1', 'switch-01', 'public', 0),
('192.168.1.2', 'router-01', 'public', 0);
"
```

### 2. 构建镜像

```bash
cd /path/to/collector
./docker/app_build.sh
```

### 3. 启动容器

```bash
# 设置数据库密码并启动
DB_PASSWORD="your_password" ./docker/app_start.sh
```

### 4. 查看日志

```bash
# 查看 Docker 日志
./docker/logs.sh

# 查看调度器日志
./docker/logs.sh scheduler
```

## 数据目录结构

```
/root/docker_apps/snmp_collector/
├── logs/                      # 应用日志
│   ├── scheduler.log         # 调度器日志
│   └── collector.log         # 采集器日志
└── config/                    # 配置文件
    ├── config.py             # 数据库配置
    └── task_config.yaml      # 任务配置
```

## 配置说明

### 数据库配置

首次启动后，配置文件会被复制到数据目录：
- `/root/docker_apps/snmp_collector/config/config.py`

编辑数据库配置：
```python
db_config = {
    "host": "192.168.1.100",    # 数据库地址
    "port": 3306,                # 数据库端口
    "user": "collector",         # 数据库用户
    "password": "your_password", # 数据库密码
    "dbname": "network_monitor",
    "charset": "utf8mb4"
}
```

**注意**: 修改配置后需要重启容器：
```bash
docker restart snmp_collector
```

### 任务配置

编辑任务配置：
- `/root/docker_apps/snmp_collector/config/task_config.yaml`

启用/禁用任务：
```yaml
- id: collect_arpv6_table
  enabled: false  # 改为 true 启用
```

修改采集频率：
```yaml
- id: collect_arp_table
  schedule: "*/15 * * * *"  # 改为每15分钟
```

## 常用命令

```bash
# 查看容器状态
docker ps | grep snmp_collector

# 停止容器
docker stop snmp_collector

# 重启容器
docker restart snmp_collector

# 进入容器
docker exec -it snmp_collector bash

# 删除容器
docker rm -f snmp_collector

# 删除镜像
docker rmi snmp_collector:v1

# 查看容器资源使用
docker stats snmp_collector
```

## 网络配置

容器使用 `--network host` 模式，直接使用宿主机网络，方便访问内网设备和数据库。

如需使用桥接网络，修改 `app_start.sh`：
```bash
# 移除 --network host
# 添加端口映射（如果有Web界面）
-p 8080:8080 \
```

## 故障排查

### 1. 容器启动失败

```bash
# 查看详细错误
docker logs snmp_collector

# 检查配置文件
cat /root/docker_apps/snmp_collector/config/config.py
```

### 2. 数据库连接失败

```bash
# 检查数据库连通性
docker exec snmp_collector ping -c 3 <DB_HOST>

# 测试数据库连接
docker exec snmp_collector python3 -c "
from config.config import db_config
import pymysql
conn = pymysql.connect(**db_config)
print('Database connected successfully!')
"
```

### 3. SNMP 采集失败

```bash
# 进入容器测试 SNMP
docker exec -it snmp_collector bash
snmpwalk -v2c -c public 192.168.1.1 system

# 查看采集错误日志
./docker/logs.sh error
```

### 4. 任务未执行

```bash
# 查看调度器日志
./docker/logs.sh scheduler

# 检查任务配置
cat /root/docker_apps/snmp_collector/config/task_config.yaml
```

## 性能优化

### 限制容器资源

```bash
docker update \
    --memory="512m" \
    --memory-swap="1g" \
    --cpus="2" \
    snmp_collector
```

### 日志轮转

添加 Docker 日志配置（在 `app_start.sh` 中）：
```bash
--log-opt max-size=50m \
--log-opt max-file=3 \
```

## 备份和恢复

### 备份配置

```bash
tar -czf collector_config_backup.tar.gz \
    /root/docker_apps/snmp_collector/config/
```

### 备份数据库

```bash
mysqldump -u root -p network_monitor > backup_$(date +%Y%m%d).sql
```

### 恢复

```bash
# 恢复配置
tar -xzf collector_config_backup.tar.gz -C /

# 恢复数据库
mysql -u root -p network_monitor < backup_20260813.sql

# 重启容器
docker restart snmp_collector
```

## 更新升级

```bash
# 1. 停止旧容器
docker stop snmp_collector

# 2. 备份数据
./docker/backup.sh  # 如果有备份脚本

# 3. 更新代码
git pull

# 4. 重新构建镜像
./docker/app_build.sh v2

# 5. 启动新容器
DB_PASSWORD="your_password" ./docker/app_start.sh v2
```

## 监控建议

使用以下工具监控容器：
- Prometheus + Grafana
- Docker Stats
- 日志告警

示例 Prometheus 配置：
```yaml
scrape_configs:
  - job_name: 'snmp_collector'
    static_configs:
      - targets: ['localhost:8080']  # 如果暴露了metrics端口
```

## 安全建议

1. **不要在镜像中硬编码敏感信息**
2. **使用环境变量传递密码**
3. **定期更新基础镜像**
4. **限制容器权��**
5. **使用专用数据库用户**

## 技术支持

遇到问题请查看：
- 项目 README.md
- QUICKSTART.md
- 容器日志: `./docker/logs.sh`
- 应用日志: `/root/docker_apps/snmp_collector/logs/`
