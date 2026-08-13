# scripts 目录说明

本目录存放所有的定时采集任务脚本。

## 目录结构

```
scripts/
├── __init__.py              # 包初始化文件
├── collect_device.py        # 设备��息采集任务
├── collect_arp.py           # ARP表采集任务
├── collect_mac.py           # MAC地址表采集任务
├── collect_port.py          # 端口状态采集任务
├── collect_route.py         # 路由表采集任务
├── collect_lldp.py          # LLDP邻居信息采集任务
└── clean_data.py            # 数据清理任务
```

## 脚本规范

每个任务脚本应遵循以下规范：

### 1. 必须包含 `run()` 异步函数

这是任务的入口函数，调度器会调用这个函数：

```python
async def run():
    """主执行函数"""
    logger.info("开始执行任务")
    try:
        # 任务逻辑
        pass
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
```

### 2. 使用日志记录

使用标准的 logging 模块记录任务执行情况：

```python
import logging
logger = logging.getLogger(__name__)

logger.info("信息日志")
logger.error("错误日志")
logger.warning("警告日志")
```

### 3. 异常处理

任务中应该有完善的异常处理，避免单个设备失败导致整个任务中断：

```python
async def collect_single_device(ip):
    try:
        # 采集逻辑
        pass
    except Exception as e:
        logger.error(f"采集设备 {ip} 失败: {e}")
        return None
```

### 4. 资源清理

使用完数据库连接等资源后应及时关闭：

```python
try:
    db = DBHelper()
    # 使用数据库
    pass
finally:
    if 'db' in locals():
        db.close()
```

### 5. 支持独立运行

每个脚本应该支持独立运行以便测试：

```python
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
```

## 现有任务说明

### collect_device.py
- **功能**: 采集设备基础信息（名称、描述、型号等）
- **调度**: 每小时执行一次
- **数据源**: Module/Device.py

### collect_arp.py
- **功能**: 采集设备的 ARP 表和 IPv6 邻居表
- **调度**: 每30分钟执行一次
- **数据源**: Module/ARP.py, Module/ARPv6.py

### collect_mac.py
- **功能**: 采集设备的 MAC 地址表
- **调度**: 每30分钟执行一次
- **数据源**: Module/MAC.py

### collect_port.py
- **功能**: 采集设备的端口状态信息
- **调度**: 每10分钟执行一次（interval模式）
- **数据源**: Module/Port.py

### collect_lldp.py
- **功能**: 采集设备的 LLDP 邻居发现信息
- **调度**: 每2小时执行一次
- **数据源**: Module/LLDP.py

### collect_route.py
- **功能**: 采集设备的路由表信息
- **调度**: 每6小时执行一次
- **数据源**: Module/Route.py

### clean_data.py
- **功能**: 清理30天前的历史数据
- **调度**: 每天凌晨2点执行
- **数据源**: utils/db_helper.py

## 添加新脚本

1. 在 scripts 目录创建新的 Python 文件
2. 实现 `async def run()` 函数
3. 在 `config/task_config.yaml` 中添加任务配置
4. 重启采集器服务

## 测试脚本

单独测试某个脚本：

```bash
cd /path/to/collector
python3 -m scripts.collect_device
```

## 注意事项

1. 所有脚本都是异步执行的，使用 `async/await` 语法
2. 使用 `asyncio.gather()` 实现并发采集
3. 避免在脚本中使用阻塞式操作
4. 注意控制并发数，避免对设备造成过大压力
5. 所有数据库操作应通过 `utils/db_helper.py` 进行
