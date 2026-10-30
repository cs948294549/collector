# WLAN 终端采集（wifi_client）
from utils.snmp_tool import snmpwalk
from utils.ipaddr import getIPaddressStr, getIPaddressStrV6
import time


class WlanClient(object):
    '''
    终端表采集：按 AC 的管理 IP 采集该 AC 下所有在线终端

    各厂商 WLAN MIB 完全不同，按型号分开写，OID 与取值解析都在对应方法内部，
    输出结构保持一致（与 wifi_client 表字段一一对应）。

    信号强度与上下行速率随终端快照一起采集入库，不再实时查询。
    '''
    def __init__(self, ip, community="public", vendor="huawei", ac_id=0):
        self.ip = ip
        self.community = community
        self.vendor = str(vendor or "").strip().lower()
        self.ac_id = ac_id

    async def getClients(self):
        '''
        返回终端列表；采集失败或厂商未支持时返回 None
        '''
        if self.vendor == "huawei":
            return await self.__getHuaweiClients()
        elif self.vendor == "h3c":
            return await self.__getH3cClients()
        elif self.vendor == "ruijie":
            return await self.__getRuijieClients()
        elif self.vendor == "fortinet":
            return await self.__getFortinetClients()
        else:
            print("终端采集跳过=%s 未支持的厂商=%s" % (self.ip, self.vendor))
            return None

    async def __getHuaweiClients(self):
        '''
        华为 AC（AC6508 等）HUAWEI-WLAN-STATION-MIB
        索引为终端 MAC(6 位)，统一转小写冒号格式
        OID 需按实机 snmpwalk 核对后固化
        '''
        oid_nodes = {
            "username": "1.3.6.1.4.1.2011.6.139.18.1.2.1.2",
            "ap_mac": "1.3.6.1.4.1.2011.6.139.18.1.2.1.3",
            "ap_name": "1.3.6.1.4.1.2011.6.139.18.1.2.1.4",
            "radio_id": "1.3.6.1.4.1.2011.6.139.18.1.2.1.6",
            "band": "1.3.6.1.4.1.2011.6.139.18.1.2.1.7",
            "channel": "1.3.6.1.4.1.2011.6.139.18.1.2.1.9",
            "ssid": "1.3.6.1.4.1.2011.6.139.18.1.2.1.18",
            "status": "1.3.6.1.4.1.2011.6.139.18.1.2.1.19",
            "vlan_id": "1.3.6.1.4.1.2011.6.139.18.1.2.1.24",
            "ip": "1.3.6.1.4.1.2011.6.139.18.1.2.1.25",
            "up_rate": "1.3.6.1.4.1.2011.6.139.18.1.2.1.35",
            "down_rate": "1.3.6.1.4.1.2011.6.139.18.1.2.1.38",
            "rssi": "1.3.6.1.4.1.2011.6.139.18.1.2.1.42",
        }
        # 终端状态：3=normal 视为 online，其余（idle 等）均视为 offline
        normal_state = 3

        try:
            oid_cache = {}

            def clientIndex(oid, prefix):
                keys = oid[len(prefix):].strip(".").split(".")
                if len(keys) < 6:
                    return None
                return ":".join(["%02x" % int(i) for i in keys[:6]])

            def toStr(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", "ignore").strip()
                return str(value).strip()

            def toInt(value):
                try:
                    return int(str(value).strip())
                except Exception:
                    return None

            # 用户名
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["username"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["username"])
                if client_mac is None:
                    continue
                if client_mac not in oid_cache.keys():
                    oid_cache[client_mac] = {}
                oid_cache[client_mac]["username"] = toStr(oid_infos[oid])

            # 所属 AP MAC
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ap_mac"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["ap_mac"])
                if client_mac in oid_cache.keys():
                    value = oid_infos[oid]
                    if isinstance(value, bytes) and len(value) == 6:
                        oid_cache[client_mac]["ap_mac"] = ":".join(["%02x" % b for b in value])
                    else:
                        oid_cache[client_mac]["ap_mac"] = toStr(value).lower().replace("-", ":")

            # 所属 AP 名称
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ap_name"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["ap_name"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["ap_name"] = toStr(oid_infos[oid])

            # 射频 ID
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["radio_id"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["radio_id"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["radio_id"] = toInt(oid_infos[oid])

            # 频段
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["band"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["band"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["band"] = toStr(oid_infos[oid])

            # 信道
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["channel"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["channel"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["channel"] = toInt(oid_infos[oid])

            # SSID
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ssid"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["ssid"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["ssid"] = toStr(oid_infos[oid])

            # 终端状态
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["status"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["status"])
                if client_mac in oid_cache.keys():
                    state = toInt(oid_infos[oid])
                    if state is None:
                        continue
                    oid_cache[client_mac]["status"] = "online" if state == normal_state else "offline"

            # VLAN
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["vlan_id"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["vlan_id"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["vlan_id"] = toInt(oid_infos[oid])

            # IP
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ip"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["ip"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["ip"] = toStr(oid_infos[oid])

            # 用户速率收（上行 bps）
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["up_rate"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["up_rate"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["up_rate"] = toInt(oid_infos[oid])

            # 用户速率发（下行 bps）
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["down_rate"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["down_rate"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["down_rate"] = toInt(oid_infos[oid])

            # 用户信号强度（dBm）
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["rssi"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                client_mac = clientIndex(oid, oid_nodes["rssi"])
                if client_mac in oid_cache.keys():
                    oid_cache[client_mac]["rssi"] = toInt(oid_infos[oid])

            responds = []
            for client_mac in oid_cache.keys():
                client = oid_cache[client_mac]
                responds.append({
                    "client_mac": client_mac,
                    "username": client.get("username", ""),
                    "ap_mac": client.get("ap_mac", ""),
                    "ap_name": client.get("ap_name", ""),
                    "radio_id": client.get("radio_id"),
                    "band": client.get("band", ""),
                    "channel": client.get("channel"),
                    "ssid": client.get("ssid", ""),
                    "status": client.get("status", ""),
                    "vlan_id": client.get("vlan_id"),
                    "ip": client.get("ip", ""),
                    "up_rate": client.get("up_rate"),
                    "down_rate": client.get("down_rate"),
                    "rssi": client.get("rssi"),
                    "ac_id": self.ac_id,
                })
            return responds
        except Exception as e:
            print("终端采集异常=", self.ip, str(e))
            return None

    async def __getFortinetClients(self):
        '''
        飞塔 FortiGate 自带无线控制器（fgWc，1.3.6.1.4.1.12356.101.14）
        Sta 表（5.1）索引为 vdom + VAP ifIndex + 终端 MAC(6 位)，定长，MAC 前没有长度前缀
        同一 MAC 可能挂在多个 VAP 索引下，wifi_client 以 MAC 为主键只留一行
        所属 AP 只给 WTP ID，AP MAC / 名称 / profile 取 Session（4.4.1）、Config（4.3.1）表
        频段按 (profile, 射频 ID) 查 ProfRadio（4.2.1），SSID / VLAN 按 VAP ifIndex 查 Wlan 表（3.1）
        BandwidthTx/Rx 是 Gauge32 瞬时带宽（kbps），原值 ×1000 转 bps，不跨次相减
        '''
        base = "1.3.6.1.4.1.12356.101.14."
        oid_nodes = {
            "ap_mac": base + "4.4.1.6",
            "profile": base + "4.4.1.11",
            "ap_name": base + "4.3.1.3",
            "mode": base + "4.5.1.3",
            "band": base + "4.2.1.11",
            "wlan_ssid": base + "3.1.1",
            "wlan_vlan": base + "3.1.9",
            "ssid": base + "5.1.2",
            "wtp_id": base + "5.1.3",
            "radio_id": base + "5.1.4",
            "vlan_id": base + "5.1.5",
            "ip": base + "5.1.7",
            "username": base + "5.1.10",
            "rssi": base + "5.1.12",
            "down_rate": base + "5.1.15",
            "up_rate": base + "5.1.16",
            "channel": base + "5.1.17",
            "online": base + "5.1.21",
        }
        # 终端在线：1=yes 视为 online，2=no 不入库
        online_yes = 1
        online_no = 2
        # 射频模式：3=ap，挂在非 ap 射频上的终端不入库
        mode_ap = 3
        # FgWcWtpRadioType 枚举 → 频段
        band_map = {
            2: "2.4G", 3: "2.4G", 5: "2.4G", 7: "2.4G", 8: "2.4G", 9: "2.4G",
            13: "2.4G", 16: "2.4G", 17: "2.4G", 18: "2.4G",
            1: "5G", 4: "5G", 6: "5G", 10: "5G", 11: "5G", 12: "5G",
            14: "5G", 19: "5G", 20: "5G", 21: "5G",
            15: "6G",
        }

        try:
            oid_cache = {}

            def strIndex(oid, prefix):
                # 变长串索引：vdom . 长度 n . n 个 ASCII 字符 . 后续定长段，返回 (串, 后续段...)
                try:
                    keys = [int(i) for i in oid[len(prefix):].strip(".").split(".")]
                except ValueError:
                    return None
                if len(keys) < 2:
                    return None
                count = keys[1]
                if count <= 0 or len(keys) < 2 + count:
                    return None
                return ("".join([chr(i) for i in keys[2:2 + count]]),) + tuple(keys[2 + count:])

            def staIndex(oid, prefix):
                # 定长索引：vdom . VAP ifIndex . MAC(6 位)，返回 (ifIndex, 终端 MAC)
                try:
                    keys = [int(i) for i in oid[len(prefix):].strip(".").split(".")]
                except ValueError:
                    return None
                if len(keys) < 8:
                    return None
                return keys[1], ":".join(["%02x" % i for i in keys[2:8]])

            def toStr(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", "ignore").strip()
                return str(value).strip()

            def toInt(value):
                try:
                    return int(str(value).strip())
                except Exception:
                    return None

            def toMac(value):
                if isinstance(value, bytes) and len(value) == 6 and value != b"\x00" * 6:
                    return ":".join(["%02x" % b for b in value])
                return ""

            def toIp(value):
                # InetAddress 按字节格式化，4 字节 IPv4、16 字节 IPv6；全 0 视为无效
                if not isinstance(value, bytes) or value.count(0) == len(value):
                    return ""
                if len(value) == 4:
                    return getIPaddressStr(ip_byte=value)
                if len(value) == 16:
                    return getIPaddressStrV6(ipv6_byte=value)
                return ""

            def toRate(value):
                # kbps → bps
                rate = toInt(value)
                return rate * 1000 if rate is not None else None

            async def walkIndex(column_oid):
                # walk 一列，返回 {(串, 后续段...): 原始值}
                result = {}
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=column_oid, max_repetitions=10)
                for oid in (oid_infos or {}).keys():
                    if oid_infos[oid] is None:
                        continue
                    index = strIndex(oid, column_oid)
                    if index is None:
                        continue
                    result[index] = oid_infos[oid]
                return result

            async def fillSta(column_oid, field, convert):
                # 按 (ifIndex, 终端 MAC) 把 Sta 表一列填进 oid_cache
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=column_oid, max_repetitions=10)
                for oid in (oid_infos or {}).keys():
                    if oid_infos[oid] is None:
                        continue
                    index = staIndex(oid, column_oid)
                    if index is None:
                        continue
                    if index not in oid_cache.keys():
                        oid_cache[index] = {"if_index": index[0], "client_mac": index[1]}
                    try:
                        oid_cache[index][field] = convert(oid_infos[oid])
                    except Exception:
                        continue

            # WTP ID → AP MAC / profile / AP 名称
            ap_macs = {}
            for index, value in (await walkIndex(oid_nodes["ap_mac"])).items():
                ap_mac = toMac(value)
                if ap_mac:
                    ap_macs[index[0]] = ap_mac
            profiles = {}
            for index, value in (await walkIndex(oid_nodes["profile"])).items():
                profiles[index[0]] = toStr(value)
            ap_names = {}
            for index, value in (await walkIndex(oid_nodes["ap_name"])).items():
                ap_names[index[0]] = toStr(value)

            # (WTP ID, 射频 ID) → 射频模式
            modes = {}
            for index, value in (await walkIndex(oid_nodes["mode"])).items():
                if len(index) >= 2:
                    modes[index[:2]] = toInt(value)

            # (profile, 射频 ID) → 频段
            bands = {}
            for index, value in (await walkIndex(oid_nodes["band"])).items():
                if len(index) >= 2:
                    bands[index[:2]] = band_map.get(toInt(value), "")

            # VAP ifIndex → SSID / VLAN（Wlan 表索引 vdom . ifIndex）
            # Sta 表的 Wlan 列是 VAP 接口名，不一定等于 SSID；Sta 表的 VLAN 实机恒为 0
            wlan_ssids = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["wlan_ssid"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                keys = oid[len(oid_nodes["wlan_ssid"]):].strip(".").split(".")
                if len(keys) < 2:
                    continue
                if_index, ssid = toInt(keys[1]), toStr(oid_infos[oid])
                if if_index is not None and ssid:
                    wlan_ssids[if_index] = ssid
            wlan_vlans = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["wlan_vlan"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                keys = oid[len(oid_nodes["wlan_vlan"]):].strip(".").split(".")
                if len(keys) < 2:
                    continue
                if_index, vlan_id = toInt(keys[1]), toInt(oid_infos[oid])
                if if_index is not None and vlan_id:
                    wlan_vlans[if_index] = vlan_id

            # 终端各列
            await fillSta(oid_nodes["wtp_id"], "wtp_id", toStr)
            await fillSta(oid_nodes["ssid"], "ssid", toStr)
            await fillSta(oid_nodes["radio_id"], "radio_id", toInt)
            await fillSta(oid_nodes["vlan_id"], "vlan_id", toInt)
            await fillSta(oid_nodes["ip"], "ip", toIp)
            await fillSta(oid_nodes["username"], "username", toStr)
            await fillSta(oid_nodes["rssi"], "rssi", toInt)
            await fillSta(oid_nodes["down_rate"], "down_rate", toRate)
            await fillSta(oid_nodes["up_rate"], "up_rate", toRate)
            await fillSta(oid_nodes["channel"], "channel", toInt)
            await fillSta(oid_nodes["online"], "online", toInt)

            # 同一 MAC 多行时在线的优先，其次取后出现的一行
            clients = {}
            for index in oid_cache.keys():
                client = oid_cache[index]
                online = client.get("online")
                if online == online_no:
                    continue
                exist = clients.get(client["client_mac"])
                if exist is not None and exist.get("online") == online_yes and online != online_yes:
                    continue
                clients[client["client_mac"]] = client

            responds = []
            for client_mac in clients.keys():
                client = clients[client_mac]
                wtp_id = client.get("wtp_id", "")
                radio_id = client.get("radio_id")
                # 射频模式查得到且不是 ap 的丢弃
                mode = modes.get((wtp_id, radio_id))
                if mode is not None and mode != mode_ap:
                    continue
                channel = client.get("channel")
                band = bands.get((profiles.get(wtp_id, ""), radio_id), "")
                # 枚举外（如新型号）按信道兜底，6G 信道号与 2.4G 重叠，兜底不出 6G
                if not band and channel:
                    band = "2.4G" if channel <= 14 else "5G"
                responds.append({
                    "client_mac": client_mac,
                    "username": client.get("username", ""),
                    # 映射不到 AP 的终端照样入库，ap_mac 留空、ap_name 回退 WTP ID
                    "ap_mac": ap_macs.get(wtp_id, ""),
                    "ap_name": ap_names.get(wtp_id) or wtp_id,
                    "radio_id": radio_id,
                    "band": band,
                    "channel": channel,
                    "ssid": wlan_ssids.get(client["if_index"]) or client.get("ssid", ""),
                    "status": "online" if client.get("online") == online_yes else "",
                    "vlan_id": client.get("vlan_id") or wlan_vlans.get(client["if_index"]),
                    "ip": client.get("ip", ""),
                    "up_rate": client.get("up_rate"),
                    "down_rate": client.get("down_rate"),
                    "rssi": client.get("rssi"),
                    "ac_id": self.ac_id,
                })
            return responds
        except Exception as e:
            print("终端采集异常=", self.ip, str(e))
            return None

    async def __getH3cClients(self):
        '''
        华三 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("终端采集跳过=%s 华三 profile 待补充" % self.ip)
        return None

    async def __getRuijieClients(self):
        '''
        锐捷 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("终端采集跳过=%s 锐捷 profile 待补充" % self.ip)
        return None


if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = WlanClient("172.25.7.253", "vdiannet", "huawei", 1)
        res = await a.getClients()
        if res is None:
            print("采集失败")
        else:
            print(len(res))
            for i in res:
                print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)
