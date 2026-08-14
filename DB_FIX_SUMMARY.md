# 数据库连接问题修复方案

## 问题描述

线上排查发现 port 采集任务无法执行，同时出现大量连接错误：
```
(2003, "Can't connect to MySQL server on '10.37.96.129' ([Errno 24] Too many open files)")
MAC采集异常= 10.39.240.45 [Errno 24] Too many open files
```

## 根本原因

1. **数据库连接过多**：每个批次创建新连接，并发批次导致连接数爆炸
2. **SNMP 连接过多**：390台设备 × 20批次并发 = 最多400个同时打开的SNMP连接
3. **文件描述符耗尽**：数据库连接 + SNMP连接 + 其他文件，超过系统限制（通常256-1024）

## 解决方案

采用**双重控制策略**：

### 1. 消息队列（解决数据库连接问题）
所有采集任务将数据发送到队列，由单一的数据库连接处理所有写入操作。

```
采集任务1 ──┐
采集任务2 ──┼──> 消息队列 ──> 单一DB连接 ──> 数据库
采集任务3 ──┘     (异步)      (批量写入)
```

### 2. 并发限制器（解决SNMP连接问题）
使用 Semaphore 限制同时进行的 SNMP 采集数量，防止文件描述符耗尽。

```python
# 全局限制最多50个并发SNMP连接
limiter = get_concurrency_limiter(max_concurrent=50)

async with limiter:
    # 采集操作
    data = await snmp_collect(ip)
```

### 3. 批次大小优化
- **修改前**：batch_size = 20，可能产生 20批次 × 20设备 = 400并发
- **修改后**：batch_size = 10 + 全局限制50，最多50个并发

### 核心组件

#### 1. 数据库写入队列 (`utils/db_queue.py`)

- **单例模式**：全局唯一的队列实例
- **单一连接**：使用一个长连接处理所有写入
- **批量处理**：自动合并多个写入请求，提高效率
- **异步处理**：不阻塞采集任务

#### 2. 并发限制器 (`utils/concurrency_limiter.py`)

- **信号量控制**：使用 asyncio.Semaphore 限制并发数
- **全局限制**：默认最多50个同时进行的SNMP采集
- **上下文管理器**：自动获取和释放许可
- **动态调整**：支持运行时修改并发限制

#### 3. 修改后的采集脚本

所有采集脚本的改进：

**并发控制：**
```python
async def collect_single_device(ip, ...):
    limiter = get_concurrency_limiter()
    async with limiter:  # 限制并发
        # 采集操作
        data = await snmp_collect(ip)
```

**数据写入：**
```python
if use_queue:
    queue = get_db_queue()
    await queue.put('operation', data)
else:
    with DBHelper() as db:
        db.save_data(data)
```

**批次优化：**
- 批次大小从 20 降到 10
- 日志显示最大并发限制

## 已修改的文件

### 核心文件
- ✅ `utils/db_queue.py` - 数据库写入队列
- ✅ `utils/db_helper.py` - 上下文管理器支持
- ✅ `utils/concurrency_limiter.py` - 并发限制器（新增）
- ✅ `main.py` - 启动/停止队列
- ✅ `config/performance_config.yaml` - 性能配置文件（新增）

### 采集脚本（已全部完成）
所有10个采集脚本已添加：
- ✅ 并发限制器（限制SNMP连接数）
- ✅ 消息队列支持（单一数据库连接）
- ✅ 批次大小优化（20→10）

文件列表：
- ✅ `scripts/collect_port.py`
- ✅ `scripts/collect_mac.py`
- ✅ `scripts/collect_arp.py`
- ✅ `scripts/collect_device.py`
- ✅ `scripts/collect_lldp.py`
- ✅ `scripts/collect_gate.py`
- ✅ `scripts/collect_physical.py`
- ✅ `scripts/collect_route.py`
- ✅ `scripts/collect_arpv6.py`
- ✅ `scripts/collect_gate_ipv6.py`

**所有采集脚本已完成双重优化！**

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

1. **数据库连接复用** - 只使用一个连接，避免连接池耗尽
2. **SNMP并发控制** - 信号量限制最多50个并发，防止文件描述符耗尽
3. **批量写入** - 自动合并多个写入请求，减少数据库压力
4. **异步处理** - 采集和写入分离，采集速度不受数据库性能影响
5. **容错能力** - 队列可以缓冲数据，即使数据库暂时不可用也不丢失数据
6. **可调节性** - 通过配置文件调整并发限制和批次大小

## 配置参数

### 并发控制（`utils/concurrency_limiter.py`）

```python
max_concurrent = 50  # 最大并发SNMP连接数
```

**调整建议：**
- 查看系统限制：`ulimit -n`（Linux/macOS）
- 建议值：系统限制的 50-70%
- macOS 默认 256，建议设置 50-100
- Linux 可调高，建议 100-200

### 数据库队列（`utils/db_queue.py`）

```python
maxsize = 10000          # 队列最大长度
batch_size = 100         # 批量处理大小
batch_timeout = 2.0      # 批量处理超时（秒）
```

### 批次大小（各采集脚本）

```python
batch_size = 10          # 每批次设备数量
```

### 性能配置文件

所有参数集中在 `config/performance_config.yaml`：

```yaml
max_concurrent_snmp: 50    # 全局SNMP并发限制
batch_size: 10             # 批次大小
db_queue:
  max_size: 10000
  batch_size: 100
  batch_timeout: 2.0
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
