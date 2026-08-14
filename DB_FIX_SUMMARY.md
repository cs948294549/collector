# 数据库连接问题修复方案

## 问题描述

线上排查发现 port 采集任务无法执行，同时出现大量数据库连接错误：
```
(2003, "Can't connect to MySQL server on '10.37.96.129' ([Errno 24] Too many open files)")
```

## 根本原因

1. **并发批次处理**：所有采集脚本使用 `asyncio.gather()` 并行执行多个批次
2. **每批次创建新连接**：每个批次在 `collect_and_save_batch()` 中创建新的 `DBHelper()` 实例
3. **连接未及时释放**：虽然调用了 `db.close()`，但在高并发下连接没有及时关闭，导致文件描述符耗尽

## 解决方案

采用**消息队列模式**，所有采集任务将数据发送到队列，由单一的数据库连接处理所有写入操作。

### 架构改进

```
采集任务1 ──┐
采集任务2 ──┼──> 消息队列 ──> 单一DB连接 ──> 数据库
采集任务3 ──┘     (异步)      (批量写入)
```

### 核心组件

#### 1. 数据库写入队列 (`utils/db_queue.py`)

- **单例模式**：全局唯一的队列实例
- **单一连接**：使用一个长连接处理所有写入
- **批量处理**：自动合并多个写入请求，提高效率
- **异步处理**：不阻塞采集任务

主要功能：
```python
queue = get_db_queue()
await queue.start()              # 启动队列
await queue.put('port', data)    # 添加数据
await queue.stop()               # 停止队列
```

#### 2. 修改后的采集脚本

所有采集脚本的 `collect_and_save_batch()` 函数支持两种模式：

- **use_queue=True**（默认）：数据发送到消息队列
- **use_queue=False**：直接写入数据库（fallback）

示例：
```python
async def collect_and_save_batch(device_batch, batch_id, use_queue=True):
    # ... 采集数据 ...
    
    if use_queue:
        # 使用消息队列
        queue = get_db_queue()
        for result in valid_results:
            await queue.put('port', result)
    else:
        # 直接写入（旧方式）
        with DBHelper() as db:
            db.save_port_info(data)
```

## 已修改的文件

### 核心文件
- ✅ `utils/db_queue.py` - 新增消息队列实现
- ✅ `utils/db_helper.py` - 添加上下文管理器支持
- ✅ `main.py` - 启动/停止队列

### 采集脚本
- ✅ `scripts/collect_port.py` - 端口状态采集
- ✅ `scripts/collect_mac.py` - MAC地址表采集
- ✅ `scripts/collect_arp.py` - ARP表采集
- ✅ `scripts/collect_device.py` - 设备信息采集
- ✅ `scripts/collect_lldp.py` - LLDP邻居信息采集
- ✅ `scripts/collect_gate.py` - 网关信息采集
- ✅ `scripts/collect_physical.py` - 设备物理信息采集

### 待修改（如果启用）
- ⏹ `scripts/collect_arpv6.py` - IPv6邻居表采集（默认禁用）
- ⏹ `scripts/collect_gate_ipv6.py` - IPv6网关信息采集（默认禁用）
- ⏹ `scripts/collect_route.py` - 路由表采集（默认禁用）

## 测试方法

### 1. 测试队列功能
```bash
python3 test_queue.py
```

### 2. 测试单个采集任务
```bash
# 测试端口采集
python3 scripts/collect_port.py
```

### 3. 启动完整采集器
```bash
python3 main.py
```

### 4. 监控队列状态
查看日志中的队列统计信息：
- 队列大小
- 已处理数量
- 失败数量

## 性能优势

1. **连接复用**：只使用一个数据库连接，避免连接池耗尽
2. **批量写入**：自动合并多个写入请求，减少数据库压力
3. **异步处理**：采集和写入分离，采集速度不受数据库性能影响
4. **容错能力**：队列可以缓冲数据，即使数据库暂时不可用也不丢失数据

## 配置参数

在 `utils/db_queue.py` 中可调整的参数：

```python
maxsize=10000           # 队列最大长度
batch_size = 100        # 批量处理大小
batch_timeout = 2.0     # 批量处理超时（秒）
```

## 回滚方案

如果消息队列出现问题，可以通过以下方式切换回直接写入模式：

1. 在采集脚本中设置 `use_queue=False`
2. 或者临时禁用队列启动（注释 `main.py` 中的 `await app.db_queue.start()`）

## 注意事项

1. **队列必须先启动**：在执行任何采集任务前，确保队列已经启动
2. **优雅停止**：停止采集器时会等待队列处理完所有数据
3. **监控队列大小**：如果队列持续增长，说明写入速度跟不上采集速度

## 下一步优化建议

1. 添加队列持久化，防止程序崩溃时丢失数据
2. 实现队列监控告警，当队列长度超过阈值时发送通知
3. 支持多个 worker 并行处理队列（如果单连接成为瓶颈）
4. 添加死信队列，处理持续失败的数据

---

**修复完成时间**: 2026-08-14  
**版本**: v1.0
