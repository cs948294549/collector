# WLAN SSID 采集（wifi_ssid）
from utils.snmp_tool import snmpwalk
import time


class WlanSSID(object):
    '''
    SSID 表采集：按 AC 的管理 IP 采集该 AC 下所有 AP 的 SSID

    各厂商 WLAN MIB 完全不同，按型号分开写，OID 与取值解析都在对应方法内部，
    输出结构保持一致（与 wifi_ssid 表字段一一对应）。

    同一 SSID 出现在多个射频下时各存一行，按 (ap_mac, radio_id, seq) 唯一。
    '''
    def __init__(self, ip, community="public", vendor="huawei", ac_id=0):
        self.ip = ip
        self.community = community
        self.vendor = str(vendor or "").strip().lower()
        self.ac_id = ac_id

    async def getSSIDs(self):
        '''
        返回 SSID 列表；采集失败或厂商未支持时返回 None
        '''
        if self.vendor == "huawei":
            return await self.__getHuaweiSSIDs()
        elif self.vendor == "h3c":
            return await self.__getH3cSSIDs()
        elif self.vendor == "ruijie":
            return await self.__getRuijieSSIDs()
        else:
            print("SSID采集跳过=%s 未支持的厂商=%s" % (self.ip, self.vendor))
            return None

    async def __getHuaweiSSIDs(self):
        '''
        华为 AC（AC6508 等）HUAWEI-WLAN-VAP-MIB
        索引为 AP MAC(6 位) + 射频 ID(1 位) + 序号(1 位)
        OID 需按实机 snmpwalk 核对后固化
        '''
        oid_nodes = {
            "ssid": "1.3.6.1.4.1.2011.6.139.17.1.1.1.6",
            "client_count": "1.3.6.1.4.1.2011.6.139.17.1.1.1.9",
            "ssid_status": "1.3.6.1.4.1.2011.6.139.17.1.1.1.10",
        }
        # SSID 状态枚举，取值含义待实机确认
        state_map = {1: "up", 2: "down"}

        try:
            oid_cache = {}

            def ssidIndex(oid, prefix):
                keys = oid[len(prefix):].strip(".").split(".")
                if len(keys) < 8:
                    return None, None, None
                ap_mac = ":".join(["%02x" % int(i) for i in keys[:6]])
                return ap_mac, int(keys[6]), int(keys[7])

            def toStr(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", "ignore").strip()
                return str(value).strip()

            def toInt(value):
                try:
                    return int(str(value).strip())
                except Exception:
                    return None

            # SSID 名称
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ssid"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id, seq = ssidIndex(oid, oid_nodes["ssid"])
                if ap_mac is None:
                    continue
                key = "%s|%s|%s" % (ap_mac, radio_id, seq)
                if key not in oid_cache.keys():
                    oid_cache[key] = {"ap_mac": ap_mac, "radio_id": radio_id, "seq": seq, "client_count": 0}
                oid_cache[key]["ssid"] = toStr(oid_infos[oid])

            # 在线数量
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["client_count"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id, seq = ssidIndex(oid, oid_nodes["client_count"])
                key = "%s|%s|%s" % (ap_mac, radio_id, seq)
                if key in oid_cache.keys():
                    oid_cache[key]["client_count"] = toInt(oid_infos[oid]) or 0

            # SSID 状态
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ssid_status"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id, seq = ssidIndex(oid, oid_nodes["ssid_status"])
                key = "%s|%s|%s" % (ap_mac, radio_id, seq)
                if key in oid_cache.keys():
                    state = toInt(oid_infos[oid])
                    oid_cache[key]["ssid_status"] = state_map.get(state, "unknown")

            responds = []
            for key in oid_cache.keys():
                item = oid_cache[key]
                responds.append({
                    "ap_mac": item["ap_mac"],
                    "radio_id": item["radio_id"],
                    "seq": item["seq"],
                    "ssid": item.get("ssid", ""),
                    "client_count": item.get("client_count", 0),
                    "ssid_status": item.get("ssid_status", "unknown"),
                    "ac_id": self.ac_id,
                })
            return responds
        except Exception as e:
            print("SSID采集异常=", self.ip, str(e))
            return None

    async def __getH3cSSIDs(self):
        '''
        华三 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("SSID采集跳过=%s 华三 profile 待补充" % self.ip)
        return None

    async def __getRuijieSSIDs(self):
        '''
        锐捷 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("SSID采集跳过=%s 锐捷 profile 待补充" % self.ip)
        return None


if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = WlanSSID("172.25.7.253", "vdiannet", "huawei", 1)
        res = await a.getSSIDs()
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
