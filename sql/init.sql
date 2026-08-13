-- SNMP Collector 数据库初始化脚本
-- 创建所有需要的表结构

-- 0. 设备列表表（IP清单）
CREATE TABLE IF NOT EXISTS iplist (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'IP地址',
    sysname VARCHAR(300) COLLATE utf8_bin NOT NULL COMMENT '设备名称',
    community VARCHAR(100) COLLATE utf8_bin NOT NULL DEFAULT 'public' COMMENT 'SNMP Community',
    admin_status VARCHAR(1) COLLATE utf8_bin NOT NULL DEFAULT '0' COMMENT '管理状态 0=正常 1=屏蔽',
    timestamp VARCHAR(100) COLLATE utf8_bin NOT NULL COMMENT '更新时间',
    PRIMARY KEY(ip),
    INDEX idx_admin_status (admin_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备IP清单表';

-- 插入示例数据（根据实际情况修改）
-- INSERT INTO device_list (ip, sysname, community, admin_status) VALUES
-- ('192.168.1.1', 'switch-core-01', 'public', 0),
-- ('192.168.1.2', 'switch-access-01', 'public', 0);

-- 1. 设备基础���息表
CREATE TABLE IF NOT EXISTS devices (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'ip地址',
    sysname VARCHAR(300) COLLATE utf8_bin NULL COMMENT '系统名',
    sysdesc TEXT COLLATE utf8_bin NULL COMMENT '系统描述',
    syscontact VARCHAR(300) COLLATE utf8_bin NULL COMMENT '公司',
    uptime VARCHAR(100) COLLATE utf8_bin NULL COMMENT '启动时间',
    hardware VARCHAR(100) COLLATE utf8_bin NULL COMMENT '硬件',
    features VARCHAR(100) COLLATE utf8_bin NULL COMMENT '版本',
    version VARCHAR(100) COLLATE utf8_bin NULL COMMENT '软件版本',
    sys_type VARCHAR(50) COLLATE utf8_bin NULL COMMENT '设备类型',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备基础信息表';

-- 2. 端口状态信息表
CREATE TABLE IF NOT EXISTS ports (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'ip地址',
    port_id INT COLLATE utf8_bin NOT NULL COMMENT '端口snmp-id',
    if_name VARCHAR(300) COLLATE utf8_bin NULL COMMENT '端口名称',
    mac_address VARCHAR(30) COLLATE utf8_bin NULL COMMENT '端口mac地址',
    speed VARCHAR(30) COLLATE utf8_bin NULL COMMENT '端口速度',
    admin_statu VARCHAR(30) COLLATE utf8_bin NULL COMMENT '端口管理状态',
    oper_statu VARCHAR(30) COLLATE utf8_bin NULL COMMENT '端口物理状态',
    alias VARCHAR(300) COLLATE utf8_bin NULL COMMENT '端口描述',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip, port_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='端口状态信息表';

-- 3. ARP表
CREATE TABLE IF NOT EXISTS arps (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'ip地址',
    arp_mac VARCHAR(30) COLLATE utf8_bin NOT NULL COMMENT 'arp-mac地址',
    arp_ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT '设备ip地址',
    port_id INT COLLATE utf8_bin NULL COMMENT '逻辑端口id',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip, arp_mac, arp_ip),
    INDEX idx_arp_ip (arp_ip),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ARP表';

-- 4. MAC地址表
CREATE TABLE IF NOT EXISTS macs (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'ip地址',
    vlan_id INT COLLATE utf8_bin NOT NULL COMMENT 'vlan_id',
    mac_address VARCHAR(30) COLLATE utf8_bin NOT NULL COMMENT 'mac地址',
    port_id INT COLLATE utf8_bin NULL COMMENT '转发端口id',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip, vlan_id, mac_address),
    INDEX idx_mac (mac_address),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MAC地址表';

-- 5. IPv4网关表
CREATE TABLE IF NOT EXISTS gates (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT '设备ip地址',
    gateway VARCHAR(30) COLLATE utf8_bin NOT NULL COMMENT '网关ip地址',
    port_id INT COLLATE utf8_bin NULL COMMENT '端口id',
    mask VARCHAR(64) COLLATE utf8_bin NULL COMMENT '子网掩码',
    startip INT UNSIGNED COLLATE utf8_bin NULL COMMENT '开始ip',
    endip INT UNSIGNED COLLATE utf8_bin NULL COMMENT '结束ip',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip, gateway),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IPv4网关表';

-- 6. IPv6网关表
CREATE TABLE IF NOT EXISTS gates_ipv6 (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT '设备ip地址',
    gateway VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT '网关ipv6地址',
    port_id INT COLLATE utf8_bin NULL COMMENT '端口id',
    mask INT COLLATE utf8_bin NULL COMMENT '掩码长度',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip, gateway),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IPv6网关表';

-- 7. LLDP邻居信息表
CREATE TABLE IF NOT EXISTS lldps (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'ip地址',
    port_id VARCHAR(30) COLLATE utf8_bin NOT NULL COMMENT '接口序号',
    rem_name VARCHAR(300) COLLATE utf8_bin NULL COMMENT '系统名',
    rem_portname VARCHAR(300) COLLATE utf8_bin NULL COMMENT '端口名称',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    rem_portalias VARCHAR(300) COLLATE utf8_bin NULL COMMENT '端口描述',
    loc_portname VARCHAR(300) COLLATE utf8_bin NULL COMMENT '本端端口名称',
    loc_portalias VARCHAR(300) COLLATE utf8_bin NULL COMMENT '本端端口描述',
    PRIMARY KEY(ip, port_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LLDP邻居信息表';

-- 8. 路由表
CREATE TABLE IF NOT EXISTS routes (
    ip VARCHAR(32) COLLATE utf8_bin NOT NULL COMMENT '设备ip地址',
    dest VARCHAR(32) COLLATE utf8_bin NOT NULL COMMENT '目的地址',
    mask VARCHAR(32) COLLATE utf8_bin NOT NULL COMMENT '目的地址掩码',
    nexthop VARCHAR(32) COLLATE utf8_bin NOT NULL COMMENT '下一跳地址',
    nextindex VARCHAR(20) COLLATE utf8_bin NOT NULL COMMENT '下一跳端口ID',
    p_type VARCHAR(1) COLLATE utf8_bin NULL COMMENT '路由类型',
    proto VARCHAR(2) COLLATE utf8_bin NULL COMMENT '协议类型',
    metric BIGINT COLLATE utf8_bin NULL COMMENT '度量值',
    start_ip BIGINT COLLATE utf8_bin NULL COMMENT '开始IP',
    end_ip BIGINT COLLATE utf8_bin NULL COMMENT '结束IP',
    pool_len BIGINT COLLATE utf8_bin NULL COMMENT '匹配长度',
    timestamp VARCHAR(20) COLLATE utf8_bin NOT NULL COMMENT '采集时间',
    PRIMARY KEY(ip, dest, mask, nexthop),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='路由表';

-- 9. 设备序列号信息表
CREATE TABLE IF NOT EXISTS dev_sn (
    ip VARCHAR(64) COLLATE utf8_bin NOT NULL COMMENT 'ip地址',
    sn_id INT COLLATE utf8_bin NOT NULL COMMENT 'snmp id',
    sn_name VARCHAR(300) COLLATE utf8_bin NULL COMMENT '硬件名称',
    sn_desc VARCHAR(300) COLLATE utf8_bin NULL COMMENT '硬件描述',
    sn_number VARCHAR(300) COLLATE utf8_bin NULL COMMENT '序列号',
    sn_type INT COLLATE utf8_bin NOT NULL DEFAULT 0 COMMENT '类型',
    sn_ex VARCHAR(300) COLLATE utf8_bin NULL COMMENT '硬件扩展名称',
    timestamp VARCHAR(100) COLLATE utf8_bin NULL COMMENT '采集时间',
    PRIMARY KEY(ip, sn_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备序列号信息表';

