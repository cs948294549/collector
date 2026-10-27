# WLAN 终端采集（wifi_client）
from utils.snmp_tool import snmpwalk
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
        # 终端状态枚举，取值含义待实机确认
        state_map = {1: "online", 2: "offline"}

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
                    oid_cache[client_mac]["status"] = state_map.get(state, "unknown")

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
