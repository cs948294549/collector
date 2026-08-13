# Docker 部署快速指南

## 方式一：使用 Shell 脚本部署（推荐）

### 1. 准备数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE network_monitor DEFAULT CHARACTER SET utf8mb4;"

# 导入表结构
mysql -u root -p network_monitor < sql/init.sql

# 添加设备
mysql -u root -p network_monitor -e "
INSERT INTO device_list (ip, sysname, community, admin_status) VALUES
('192.168.1.1', 'switch-01', 'public', 0);
"
```

### 2. 构建镜像

```bash
cd /path/to/collector
./docker/app_build.sh v1
```

### 3. 启动容器

```bash
# 设置数据库密码
export DB_PASSWORD="your_password"

# 启动容器
./docker/app_start.sh v1
```

### 4. 查看日志

```bash
# 实时查看日志
./docker/logs.sh

# 查看调度器日志
./docker/logs.sh scheduler

# 查看错误日志
./docker/logs.sh error
```

## 方式二：使用 Docker Compose 部署

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
vim .env
```

编辑 `.env` 文件：
```bash
DB_HOST=192.168.1.100
DB_PORT=3306
DB_USER=collector
DB_PASSWORD=your_password
DB_NAME=network_monitor
COLLECTOR_DATA_DIR=/data/snmp_collector
```

### 2. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 配置文件位置

首次启动后，配置文件会被复制到：
```
/root/docker_apps/snmp_collector/
├── config/
│   ├── config.py              # 数据库配置
│   └── task_config.yaml       # 任务配置
└── logs/
    ├── scheduler.log          # 调度器日志
    └── collector.log          # 采集器日志
```

## 修改配置

### 修改数据库配置

```bash
# 编辑配置文件
vim /root/docker_apps/snmp_collector/config/config.py

# 重启容器
docker restart snmp_collector
# 或
docker-compose restart
```

### 修改任务配置

```bash
# 编辑任务配置
vim /root/docker_apps/snmp_collector/config/task_config.yaml

# 重启容器
docker restart snmp_collector
```

## 常用操作

### 查看容器状态

```bash
docker ps | grep snmp_collector
# 或
docker-compose ps
```

### 进入容器

```bash
docker exec -it snmp_collector bash
```

### 查看资源使用

```bash
docker stats snmp_collector
```

### 重启容器

```bash
docker restart snmp_collector
# 或
docker-compose restart
```

### 停止容器

```bash
docker stop snmp_collector
# 或
docker-compose stop
```

### 删除容器

```bash
docker rm -f snmp_collector
# 或
docker-compose down
```

## 故障排查

### 1. 查看启动日志

```bash
docker logs snmp_collector
# 或使用日志工具
./docker/logs.sh tail 100
```

### 2. 测试数据库连接

```bash
docker exec snmp_collector python3 -c "
from config.config import db_config
import pymysql
try:
    conn = pymysql.connect(**db_config)
    print('✓ 数据库连接成功')
    conn.close()
except Exception as e:
    print(f'✗ 数据库连接失败: {e}')
"
```

### 3. 测试 SNMP 连接

```bash
docker exec snmp_collector snmpwalk -v2c -c public 192.168.1.1 system
```

### 4. 查看任务执行情况

```bash
./docker/logs.sh scheduler
```

### 5. 查看错误信息

```bash
./docker/logs.sh error
```

## 数据备份

### 备份配置文件

```bash
tar -czf collector_config_$(date +%Y%m%d).tar.gz \
    /root/docker_apps/snmp_collector/config/
```

### 备份数据库

```bash
mysqldump -u root -p network_monitor > \
    backup_$(date +%Y%m%d).sql
```

## 更新升级

```bash
# 1. 停止容器
docker-compose down
# 或
docker stop snmp_collector

# 2. 更新代码
git pull

# 3. 重新构建
./docker/app_build.sh v2
# 或
docker-compose build

# 4. 启动新版本
DB_PASSWORD="your_password" ./docker/app_start.sh v2
# 或
docker-compose up -d
```

## 性能优化

### 限制资源使用

编辑 `docker-compose.yml` 添加：
```yaml
services:
  snmp_collector:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 512M
        reservations:
          cpus: '1'
          memory: 256M
```

### 调整并发数

编辑配置文件：
```python
# config/config.py
concurrency_config = {
    "max_workers": 30,  # 减少并发数
    "batch_size": 50    # 减少批次大小
}
```

## 网络配置说明

默认使用 `--network host` 模式，容器直接使用宿主机网络。

**优点**：
- 无需端口映射
- 可直接访问内网设备
- 性能最优

**缺点**：
- 端口可能冲突
- 安全性相对较低

如需使用桥接网络，修改 `docker-compose.yml`：
```yaml
services:
  snmp_collector:
    # 移除 network_mode: host
    # 如果有 Web 端口需要映射
    ports:
      - "8080:8080"
```

## 监控建议

### 日志监控

```bash
# 持续监控错误日志
./docker/logs.sh error | tee -a error_monitor.log

# 监控特定关键字
watch -n 10 './docker/logs.sh search "失败"'
```

### 资源监控

```bash
# 实时监控资源
watch -n 5 'docker stats snmp_collector --no-stream'
```

### 告警设置

可配置日志告警工具，如：
- Logwatch
- Fail2ban
- Prometheus Alertmanager

## 安全建议

1. **使用专用数据库用户**
   ```sql
   CREATE USER 'collector'@'%' IDENTIFIED BY 'strong_password';
   GRANT ALL ON network_monitor.* TO 'collector'@'%';
   ```

2. **不要提交 .env 文件到 Git**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **定期更新基础镜像**
   ```bash
   ./docker/app_build.sh v$(date +%Y%m%d)
   ```

4. **限制容器权限**
   ```yaml
   security_opt:
     - no-new-privileges:true
   ```

## 多环境部署

### 开发环境

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 生产环境

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 技术支持

- 详细文档: `docker/README.md`
- 项目文档: `README.md`
- 快速开始: `QUICKSTART.md`
- 问题排查: 查看日志 `./docker/logs.sh error`
