# Module 类名映射参考

本文档列出所有 Module 中的实际类名，供脚本开发时参考。

## 类名映射表

| 模块文件 | 类名 | 功能描述 |
|---------|------|---------|
| Module/Device.py | `DeviceInfo` | 设备基础信息 |
| Module/ARP.py | `ARPTable` | IPv4 ARP表 |
| Module/ARPv6.py | `ARPv6Table` | IPv6 邻居表 |
| Module/MAC.py | `MACTable` | MAC地址表 |
| Module/Port.py | `PortInfo` | 端口状态信息 |
| Module/Route.py | `RouteInfo` | 路由��信息 |
| Module/LLDP.py | `LLDPInfo` | LLDP邻居信息 |
| Module/Gate.py | `Gate` | IPv4网关信息 |
| Module/Gate_ipv6.py | `Gate_ipv6` | IPv6网关信息 |
| Module/Physical.py | `PhysicalInfo` | 设备物理信息 |

## 导入示例

```python
# 设备信息
from Module.Device import DeviceInfo
device = DeviceInfo(ip, community)
data = await device.getDeviceTable()

# IPv4 ARP表
from Module.ARP import ARPTable
arp = ARPTable(ip, community)
data = await arp.getARPTable()

# IPv6 邻居表
from Module.ARPv6 import ARPv6Table
arpv6 = ARPv6Table(ip, community)
data = await arpv6.getARPv6Table()

# MAC地址表
from Module.MAC import MACTable
mac = MACTable(ip, community)
data = await mac.getMACTable()

# 端口信息
from Module.Port import PortInfo
port = PortInfo(ip, community)
data = await port.getPortTable()

# 路由表
from Module.Route import RouteInfo
route = RouteInfo(ip, community)
data = await route.getRouteTable()

# LLDP信息
from Module.LLDP import LLDPInfo
lldp = LLDPInfo(ip, community)
data = await lldp.getLLDPTable()

# IPv4网关
from Module.Gate import Gate
gate = Gate(ip, community)
data = await gate.getGateTable()

# IPv6网关
from Module.Gate_ipv6 import Gate_ipv6
gate_ipv6 = Gate_ipv6(ip, community)
data = await gate_ipv6.getGateIPv6Table()

# 设备物理信息
from Module.Physical import PhysicalInfo
physical = PhysicalInfo(ip, community)
data = await physical.getPhysicalTable()
```

## 已修复的脚本

以下脚本已经修正了类名引用：

- ✅ scripts/collect_device.py - 使用 `DeviceInfo`
- ✅ scripts/collect_arp.py - 使用 `ARPTable`
- ✅ scripts/collect_arpv6.py - 使用 `ARPv6Table`
- ✅ scripts/collect_mac.py - 使用 `MACTable`
- ✅ scripts/collect_port.py - 使用 `PortInfo`
- ✅ scripts/collect_route.py - 使用 `RouteInfo`
- ✅ scripts/collect_lldp.py - 使用 `LLDPInfo`
- ✅ scripts/collect_gate.py - 使用 `Gate` 和 `Gate_ipv6`
- ✅ scripts/collect_physical.py - 使用 `PhysicalInfo`
