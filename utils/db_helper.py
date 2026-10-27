"""
数据库辅助类
提供数据库连接和常用操作
"""
import pymysql
import logging
from config.config import db_config

logger = logging.getLogger(__name__)


class DBHelper:
    """数据库操作辅助类"""

    def __init__(self):
        """初始化数据库连接"""
        try:
            self.conn = pymysql.connect(
                host=db_config["host"],
                user=db_config["user"],
                password=db_config["password"],
                port=db_config["port"],
                database=db_config["dbname"],
                charset=db_config["charset"]
            )
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def get_device_list(self, status=None):
        """
        获取设备列表

        Args:
            status: 设备状态过滤，None表示获取所有设备

        Returns:
            ��备列表（包含 sys_type）
        """
        try:
            if status is not None:
                sql = """
                    SELECT i.ip, i.sysname, i.community, d.sys_type
                    FROM iplist i
                    LEFT JOIN devices d ON i.ip = d.ip
                    WHERE i.admin_status = %s
                """
                self.cursor.execute(sql, (status,))
            else:
                sql = """
                    SELECT i.ip, i.sysname, i.community, d.sys_type
                    FROM iplist i
                    LEFT JOIN devices d ON i.ip = d.ip
                    WHERE i.admin_status <> '1'
                """
                self.cursor.execute(sql)

            results = self.cursor.fetchall()
            return results if results else []

        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return []

    def save_device_info(self, device_data):
        """
        保存设备信息到 devices 表

        Args:
            device_data: 设备信息列表
        """
        try:
            sql = """
                INSERT INTO devices (ip, sysname, sysdesc, syscontact, uptime,
                                   hardware, features, version, sys_type, vendor, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    sysname = VALUES(sysname),
                    sysdesc = VALUES(sysdesc),
                    syscontact = VALUES(syscontact),
                    uptime = VALUES(uptime),
                    hardware = VALUES(hardware),
                    features = VALUES(features),
                    version = VALUES(version),
                    sys_type = VALUES(sys_type),
                    vendor = VALUES(vendor),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for device in device_data:
                if device and isinstance(device, dict):
                    values.append((
                        device.get('ip', ''),
                        device.get('sysname', ''),
                        device.get('sysdesc', ''),
                        device.get('syscontact', ''),
                        device.get('uptime', ''),
                        device.get('hardware', ''),
                        device.get('features', ''),
                        device.get('version', ''),
                        device.get('sys_type', 'default'),
                        device.get('vendor', 'unknown'),
                        device.get('timestamp', '')
                    ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条设备信息")

        except Exception as e:
            logger.error(f"保存设备信息失败: {e}")
            self.conn.rollback()

    def save_arp_info(self, arp_data):
        """
        保存ARP信息到 arps 表

        Args:
            arp_data: ARP信息列表
        """
        try:
            sql = """
                INSERT INTO arps (ip, arp_mac, arp_ip, port_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    port_id = VALUES(port_id),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in arp_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    arp_list = item.get('arp', [])

                    # 检查 arp_list 是否为 None
                    if arp_list is None:
                        continue

                    for arp in arp_list:
                        if isinstance(arp, dict):
                            values.append((
                                device_ip,
                                arp.get('arp_mac', ''),
                                arp.get('arp_ip', ''),
                                arp.get('port_id', 0),
                                arp.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条ARP记录")

        except Exception as e:
            logger.error(f"保存ARP信息失败: {e}")
            self.conn.rollback()

    def save_mac_info(self, mac_data):
        """
        保存MAC地址表信息到 macs 表

        Args:
            mac_data: MAC地址表信息列表
        """
        try:
            sql = """
                INSERT INTO macs (ip, vlan_id, mac_address, port_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    port_id = VALUES(port_id),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in mac_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    mac_table = item.get('mac_table', [])

                    # 检查 mac_table 是否为 None
                    if mac_table is None:
                        continue

                    for mac in mac_table:
                        if isinstance(mac, dict):
                            values.append((
                                device_ip,
                                mac.get('vlan_id', 0),
                                mac.get('mac_address', ''),
                                mac.get('port_id', 0),
                                mac.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条MAC记录")

        except Exception as e:
            logger.error(f"保存MAC信息失败: {e}")
            self.conn.rollback()

    def save_port_info(self, port_data):
        """
        保存端口状态信息到 ports 表

        Args:
            port_data: 端口状态信息列表
        """
        try:
            sql = """
                INSERT INTO ports (ip, port_id, if_name, mac_address, speed,
                                 admin_statu, oper_statu, alias, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    if_name = VALUES(if_name),
                    mac_address = VALUES(mac_address),
                    speed = VALUES(speed),
                    admin_statu = VALUES(admin_statu),
                    oper_statu = VALUES(oper_statu),
                    alias = VALUES(alias),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in port_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    ports = item.get('ports', [])

                    # 检查 ports 是否为 None
                    if ports is None:
                        continue

                    for port in ports:
                        if isinstance(port, dict):
                            values.append((
                                device_ip,
                                port.get('port_id', 0),
                                port.get('if_name', ''),
                                port.get('mac_address', ''),
                                port.get('speed', ''),
                                port.get('admin_statu', ''),
                                port.get('oper_statu', ''),
                                port.get('alias', ''),
                                port.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条端口记录")

        except Exception as e:
            logger.error(f"保存端口信息失败: {e}")
            self.conn.rollback()

    def save_route_info(self, route_data):
        """
        保存路由表信息到 routes 表

        Args:
            route_data: 路由表信息列表
        """
        try:
            sql = """
                INSERT INTO routes (ip, dest, mask, nexthop, nextindex, p_type,
                                  proto, metric, start_ip, end_ip, pool_len, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nextindex = VALUES(nextindex),
                    p_type = VALUES(p_type),
                    proto = VALUES(proto),
                    metric = VALUES(metric),
                    start_ip = VALUES(start_ip),
                    end_ip = VALUES(end_ip),
                    pool_len = VALUES(pool_len),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in route_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    routes = item.get('routes', [])

                    # 检查 routes 是否为 None
                    if routes is None:
                        continue

                    for route in routes:
                        if isinstance(route, dict):
                            values.append((
                                device_ip,
                                route.get('dest', ''),
                                route.get('mask', ''),
                                route.get('nexthop', ''),
                                route.get('nextindex', ''),
                                route.get('p_type', ''),
                                route.get('proto', ''),
                                route.get('metric', 0),
                                route.get('start_ip', 0),
                                route.get('end_ip', 0),
                                route.get('pool_len', 0),
                                route.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条路由记录")

        except Exception as e:
            logger.error(f"保存路由信息失败: {e}")
            self.conn.rollback()

    def save_lldp_info(self, lldp_data):
        """
        保存LLDP邻居信息到 lldps 表

        Args:
            lldp_data: LLDP邻居信息列表
        """
        try:
            sql = """
                INSERT INTO lldps (ip, port_id, rem_name, rem_portname, timestamp,
                                 rem_portalias, loc_portname, loc_portalias)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rem_name = VALUES(rem_name),
                    rem_portname = VALUES(rem_portname),
                    rem_portalias = VALUES(rem_portalias),
                    loc_portname = VALUES(loc_portname),
                    loc_portalias = VALUES(loc_portalias),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in lldp_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    lldp_list = item.get('lldp', [])

                    # 检查 lldp_list 是否为 None
                    if lldp_list is None:
                        continue

                    for lldp in lldp_list:
                        if isinstance(lldp, dict):
                            values.append((
                                device_ip,
                                lldp.get('port_id', ''),
                                lldp.get('rem_name', ''),
                                lldp.get('rem_portname', ''),
                                lldp.get('timestamp', ''),
                                lldp.get('rem_portalias', ''),
                                lldp.get('loc_portname', ''),
                                lldp.get('loc_portalias', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条LLDP记录")

        except Exception as e:
            logger.error(f"保存LLDP信息失败: {e}")
            self.conn.rollback()

    def save_gate_info(self, gate_data):
        """
        保存网关信息到 gates 表

        Args:
            gate_data: 网关信息列表
        """
        try:
            sql = """
                INSERT INTO gates (ip, gateway, port_id, mask, startip, endip, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    port_id = VALUES(port_id),
                    mask = VALUES(mask),
                    startip = VALUES(startip),
                    endip = VALUES(endip),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in gate_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    gates = item.get('gates', [])

                    # 检查 gates 是否为 None
                    if gates is None:
                        continue

                    for gate in gates:
                        if isinstance(gate, dict):
                            values.append((
                                device_ip,
                                gate.get('gateway', ''),
                                gate.get('port_id', 0),
                                gate.get('mask', ''),
                                gate.get('startip', 0),
                                gate.get('endip', 0),
                                gate.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条网关记录")

        except Exception as e:
            logger.error(f"保存网关信息失败: {e}")
            self.conn.rollback()

    def save_gate_ipv6_info(self, gate_data):
        """
        保存IPv6网关信息到 gates_ipv6 表

        Args:
            gate_data: IPv6网关信息列表
        """
        try:
            sql = """
                INSERT INTO gates_ipv6 (ip, gateway, port_id, mask, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    port_id = VALUES(port_id),
                    mask = VALUES(mask),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in gate_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    gates = item.get('gates_ipv6', [])

                    # 检查 gates 是否为 None
                    if gates is None:
                        continue

                    for gate in gates:
                        if isinstance(gate, dict):
                            values.append((
                                device_ip,
                                gate.get('gateway', ''),
                                gate.get('port_id', 0),
                                gate.get('mask', 0),
                                gate.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条IPv6网关记录")

        except Exception as e:
            logger.error(f"保存IPv6网关信息失败: {e}")
            self.conn.rollback()

    def save_dev_sn_info(self, sn_data):
        """
        保存设备序列号信息到 dev_sn 表

        Args:
            sn_data: 设备序列号信息列表
        """
        try:
            sql = """
                INSERT INTO dev_sn (ip, sn_id, sn_name, sn_desc, sn_number,
                                  sn_type, sn_ex, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    sn_name = VALUES(sn_name),
                    sn_desc = VALUES(sn_desc),
                    sn_number = VALUES(sn_number),
                    sn_type = VALUES(sn_type),
                    sn_ex = VALUES(sn_ex),
                    timestamp = VALUES(timestamp)
            """

            values = []
            for item in sn_data:
                if item and isinstance(item, dict):
                    device_ip = item.get('ip', '')
                    sn_list = item.get('sn_info', [])

                    # 检查 sn_list 是否为 None
                    if sn_list is None:
                        continue

                    for sn in sn_list:
                        if isinstance(sn, dict):
                            values.append((
                                device_ip,
                                sn.get('sn_id', 0),
                                sn.get('sn_name', ''),
                                sn.get('sn_desc', ''),
                                sn.get('sn_number', ''),
                                sn.get('sn_type', 0),
                                sn.get('sn_ex', ''),
                                sn.get('timestamp', '')
                            ))

            if values:
                self.cursor.executemany(sql, values)
                self.conn.commit()
                logger.info(f"保存了 {len(values)} 条设备序列号记录")

        except Exception as e:
            logger.error(f"保存设备序列号信息失败: {e}")
            self.conn.rollback()

    def clean_old_data(self, table_name, cutoff_date):
        """
        清理指定表的过期数据

        Args:
            table_name: 表名
            cutoff_date: 截止日期

        Returns:
            删除的记录数
        """
        try:
            sql = f"DELETE FROM {table_name} WHERE timestamp < %s"
            affected_rows = self.cursor.execute(sql, (cutoff_date,))
            self.conn.commit()
            return affected_rows
        except Exception as e:
            logger.error(f"清理表 {table_name} 数据失败: {e}")
            self.conn.rollback()
            return 0

    def execute_query(self, sql, params=None):
        """执行查询SQL"""
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return []

    def execute_update(self, sql, params=None):
        """执行更新SQL"""
        try:
            affected_rows = self.cursor.execute(sql, params)
            self.conn.commit()
            return affected_rows
        except Exception as e:
            logger.error(f"执行更新失败: {e}")
            self.conn.rollback()
            return 0

    def get_wifi_ac_list(self):
        """
        获取 Wi-Fi AC 列表

        Returns:
            AC 列表（community 为明文）
        """
        try:
            sql = """
                SELECT ac_id, ac_name, vendor, mgmt_ip, model, community, last_status
                FROM wifi_ac
            """
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
            return results if results else []

        except Exception as e:
            logger.error(f"获取AC列表失败: {e}")
            return []

    def update_wifi_ac_status(self, ac_id, status):
        """
        更新 AC 采集状态

        Args:
            ac_id: AC ID
            status: online / offline
        """
        try:
            sql = "UPDATE wifi_ac SET last_status = %s WHERE ac_id = %s"
            self.cursor.execute(sql, (status, ac_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"更新AC状态失败: {e}")
            self.conn.rollback()

    def replace_wifi_snapshot(self, ac_id, aps, radios, ssids, clients):
        """
        按 AC 原子替换 Wi-Fi 快照（AP / 射频 / SSID / 终端）

        单事务内先删该 AC 旧数据再写入新数据，展示侧不会读到半截快照；
        AP 换 AC、终端漫游到其他 AC 时主键冲突，按 ON DUPLICATE KEY UPDATE 改归属

        Args:
            ac_id: AC ID
            aps / radios / ssids / clients: Module 采集结果列表

        Returns:
            成功 True，失败 False
        """
        try:
            for table in ["wifi_client", "wifi_ssid", "wifi_radio", "wifi_ap"]:
                self.cursor.execute(f"DELETE FROM {table} WHERE ac_id = %s", (ac_id,))

            if aps:
                sql = """
                    INSERT INTO wifi_ap
                    (ap_mac, ap_name, ap_group, online_status, ap_ip, model, sw_version,
                     client_count, lldp_name, lldp_port, ac_id, last_seen_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    ap_name = VALUES(ap_name), ap_group = VALUES(ap_group),
                    online_status = VALUES(online_status), ap_ip = VALUES(ap_ip),
                    model = VALUES(model), sw_version = VALUES(sw_version),
                    client_count = VALUES(client_count), lldp_name = VALUES(lldp_name),
                    lldp_port = VALUES(lldp_port), ac_id = VALUES(ac_id),
                    last_seen_at = VALUES(last_seen_at)
                """
                values = [(i['ap_mac'], i['ap_name'], i['ap_group'], i['online_status'], i['ap_ip'],
                           i['model'], i['sw_version'], i['client_count'], i['lldp_name'],
                           i['lldp_port'], ac_id, i['last_seen_at']) for i in aps]
                self.cursor.executemany(sql, values)

            if radios:
                sql = """
                    INSERT INTO wifi_radio
                    (ap_mac, radio_id, wlan_type, band, channel_status, channel, bandwidth,
                     utilization, interference_rate, client_count, tx_power, max_power, ac_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    wlan_type = VALUES(wlan_type), band = VALUES(band),
                    channel_status = VALUES(channel_status), channel = VALUES(channel),
                    bandwidth = VALUES(bandwidth), utilization = VALUES(utilization),
                    interference_rate = VALUES(interference_rate), client_count = VALUES(client_count),
                    tx_power = VALUES(tx_power), max_power = VALUES(max_power), ac_id = VALUES(ac_id)
                """
                values = [(i['ap_mac'], i['radio_id'], i['wlan_type'], i['band'], i['channel_status'],
                           i['channel'], i['bandwidth'], i['utilization'], i['interference_rate'],
                           i['client_count'], i['tx_power'], i['max_power'], ac_id) for i in radios]
                self.cursor.executemany(sql, values)

            if ssids:
                sql = """
                    INSERT INTO wifi_ssid
                    (ap_mac, radio_id, seq, ssid, client_count, ssid_status, ac_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    ssid = VALUES(ssid), client_count = VALUES(client_count),
                    ssid_status = VALUES(ssid_status), ac_id = VALUES(ac_id)
                """
                values = [(i['ap_mac'], i['radio_id'], i['seq'], i['ssid'], i['client_count'],
                           i['ssid_status'], ac_id) for i in ssids]
                self.cursor.executemany(sql, values)

            if clients:
                sql = """
                    INSERT INTO wifi_client
                    (client_mac, username, ap_mac, ap_name, radio_id, band, channel,
                     ssid, status, vlan_id, ip, up_rate, down_rate, rssi, ac_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    username = VALUES(username), ap_mac = VALUES(ap_mac), ap_name = VALUES(ap_name),
                    radio_id = VALUES(radio_id), band = VALUES(band), channel = VALUES(channel),
                    ssid = VALUES(ssid), status = VALUES(status), vlan_id = VALUES(vlan_id),
                    ip = VALUES(ip), up_rate = VALUES(up_rate), down_rate = VALUES(down_rate),
                    rssi = VALUES(rssi), ac_id = VALUES(ac_id)
                """
                values = [(i['client_mac'], i['username'], i['ap_mac'], i['ap_name'], i['radio_id'],
                           i['band'], i['channel'], i['ssid'], i['status'], i['vlan_id'],
                           i['ip'], i['up_rate'], i['down_rate'], i['rssi'], ac_id) for i in clients]
                self.cursor.executemany(sql, values)

            self.conn.commit()
            logger.info(f"AC {ac_id} 快照已替换: AP {len(aps or [])}, 射频 {len(radios or [])}, "
                        f"SSID {len(ssids or [])}, 终端 {len(clients or [])}")
            return True

        except Exception as e:
            logger.error(f"替换AC {ac_id} Wi-Fi快照失败: {e}")
            self.conn.rollback()
            return False

    def close(self):
        """关闭数据库连接"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
        return False
