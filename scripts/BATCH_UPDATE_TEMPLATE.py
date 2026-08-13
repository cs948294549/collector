"""
批量更新所有采集脚本为分批采集保存模式的模板

使用方法：根据此模板手动更新每个脚本
"""

# 模板结构：
# 1. collect_single_device_xxx() - 采集单个设备
# 2. collect_and_save_batch() - 采集一批设备并保存
# 3. run() - 主函数，分批处理

# 需要修改的脚本列表和对应的Module类名、保存方法：
SCRIPTS_CONFIG = {
    'collect_arpv6.py': {
        'module_class': 'ARPv6Table',
        'module_import': 'Module.ARPv6',
        'method': 'getARPv6Table',
        'save_method': 'save_arpv6_info',  # 需要在db_helper中添加
        'data_key': 'arpv6',
        'description': 'IPv6邻居表'
    },
    'collect_mac.py': {
        'module_class': 'MACTable',
        'module_import': 'Module.MAC',
        'method': 'getMACs',
        'save_method': 'save_mac_info',
        'data_key': 'mac_table',
        'description': 'MAC地址表'
    },
    'collect_port.py': {
        'module_class': 'PortInfo',
        'module_import': 'Module.Port',
        'method': 'getPorts',
        'save_method': 'save_port_info',
        'data_key': 'ports',
        'description': '端口状态'
    },
    'collect_route.py': {
        'module_class': 'RouteInfo',
        'module_import': 'Module.Route',
        'method': 'getRouteTable',
        'save_method': 'save_route_info',
        'data_key': 'routes',
        'description': '路由表'
    },
    'collect_lldp.py': {
        'module_class': 'LLDPInfo',
        'module_import': 'Module.LLDP',
        'method': 'getLLDPInfos',
        'save_method': 'save_lldp_info',
        'data_key': 'lldp',
        'description': 'LLDP信息'
    },
    'collect_gate.py': {
        'module_class': 'Gate',
        'module_import': 'Module.Gate',
        'method': 'getGateTable',
        'save_method': 'save_gate_info',
        'data_key': 'gates',
        'description': 'IPv4网关'
    },
    'collect_gate_ipv6.py': {
        'module_class': 'Gate_ipv6',
        'module_import': 'Module.Gate_ipv6',
        'method': 'getGateIPv6Table',
        'save_method': 'save_gate_ipv6_info',
        'data_key': 'gates_ipv6',
        'description': 'IPv6网关'
    },
    'collect_physical.py': {
        'module_class': 'PhysicalInfo',
        'module_import': 'Module.Physical',
        'method': 'getPhysicalInfos',
        'save_method': 'save_physical_info',
        'data_key': 'sn_info',
        'description': '设备物理信息'
    },
    'collect_device.py': {
        'module_class': 'DeviceInfo',
        'module_import': 'Module.Device',
        'method': 'getDeviceTable',
        'save_method': 'save_device_info',
        'data_key': None,  # 直接返回device_data
        'description': '设备信息'
    }
}

print("所有采集脚本配置信息：")
for script, config in SCRIPTS_CONFIG.items():
    print(f"\n{script}:")
    print(f"  - Module: {config['module_import']}.{config['module_class']}")
    print(f"  - 采集方法: {config['method']}")
    print(f"  - 保存方法: db.{config['save_method']}()")
    print(f"  - 数据键: {config['data_key']}")
