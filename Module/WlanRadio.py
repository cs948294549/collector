# WLAN 射频采集（wifi_radio）
from utils.snmp_tool import snmpwalk
import time


class WlanRadio(object):
    '''
    射频表采集：按 AC 的管理 IP 采集该 AC 下所有 AP 的射频

    各厂商 WLAN MIB 完全不同，按型号分开写，OID 与取值解析都在对应方法内部，
    输出结构保持一致（与 wifi_radio 表字段一一对应），只保留开启的射频。
    '''
    def __init__(self, ip, community="public", vendor="huawei", ac_id=0):
        self.ip = ip
        self.community = community
        self.vendor = str(vendor or "").strip().lower()
        self.ac_id = ac_id

    async def getRadios(self):
        '''
        返回射频列表；采集失败或厂商未支持时返回 None
        '''
        if self.vendor == "huawei":
            return await self.__getHuaweiRadios()
        elif self.vendor == "h3c":
            return await self.__getH3cRadios()
        elif self.vendor == "ruijie":
            return await self.__getRuijieRadios()
        else:
            print("射频采集跳过=%s 未支持的厂商=%s" % (self.ip, self.vendor))
            return None

    async def __getHuaweiRadios(self):
        '''
        华为 AC（AC6508 等）HUAWEI-WLAN-AP-MIB
        索引为 AP MAC(6 位) + 射频 ID(1 位)
        OID 需按实机 snmpwalk 核对后固化
        '''
        oid_nodes = {
            "wlan_type": "1.3.6.1.4.1.2011.6.139.16.1.2.1.4",
            "band": "1.3.6.1.4.1.2011.6.139.16.1.2.1.5",
            "channel_status": "1.3.6.1.4.1.2011.6.139.16.1.2.1.6",
            "channel": "1.3.6.1.4.1.2011.6.139.16.1.2.1.7",
            "bandwidth": "1.3.6.1.4.1.2011.6.139.16.1.2.1.19",
            "utilization": "1.3.6.1.4.1.2011.6.139.16.1.2.1.25",
            "interference_rate": "1.3.6.1.4.1.2011.6.139.16.1.2.1.29",
            "client_count": "1.3.6.1.4.1.2011.6.139.16.1.2.1.40",
            "tx_power": "1.3.6.1.4.1.2011.6.139.16.1.2.1.45",
            "max_power": "1.3.6.1.4.1.2011.6.139.16.1.2.1.46",
        }
        # 信道状态枚举，取值含义待实机确认
        state_map = {1: "up", 2: "down"}

        try:
            oid_cache = {}

            def radioIndex(oid, prefix):
                keys = oid[len(prefix):].strip(".").split(".")
                if len(keys) < 7:
                    return None, None
                ap_mac = ":".join(["%02x" % int(i) for i in keys[:6]])
                return ap_mac, int(keys[6])

            def toStr(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", "ignore").strip()
                return str(value).strip()

            def toInt(value):
                try:
                    return int(str(value).strip())
                except Exception:
                    return None

            def toRate(value):
                try:
                    return round(float(str(value).strip()), 2)
                except Exception:
                    return None

            # WLAN 类型
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["wlan_type"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["wlan_type"])
                if ap_mac is None:
                    continue
                key = "%s|%s" % (ap_mac, radio_id)
                if key not in oid_cache.keys():
                    oid_cache[key] = {"ap_mac": ap_mac, "radio_id": radio_id, "client_count": 0}
                oid_cache[key]["wlan_type"] = toStr(oid_infos[oid])

            # 频段：OID 返回枚举值 1/2/3，映射成可读频段名
            band_map = {1: "2.4G", 2: "5G", 3: "6G"}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["band"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["band"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    band = toInt(oid_infos[oid])
                    # 枚举值映射；非枚举实现（直接回频段字符串）原样保留
                    oid_cache[key]["band"] = band_map.get(band, toStr(oid_infos[oid]))

            # 信道状态
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["channel_status"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["channel_status"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    state = toInt(oid_infos[oid])
                    oid_cache[key]["channel_status"] = state_map.get(state, "unknown")

            # 信道
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["channel"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["channel"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["channel"] = toInt(oid_infos[oid])

            # 带宽
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["bandwidth"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["bandwidth"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["bandwidth"] = toInt(oid_infos[oid])

            # 信道利用率
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["utilization"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["utilization"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["utilization"] = toRate(oid_infos[oid])

            # 干扰率
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["interference_rate"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["interference_rate"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["interference_rate"] = toRate(oid_infos[oid])

            # 射频在线数量
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["client_count"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["client_count"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["client_count"] = toInt(oid_infos[oid]) or 0

            # 当前功率
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["tx_power"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["tx_power"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["tx_power"] = toInt(oid_infos[oid])

            # 最大功率
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["max_power"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac, radio_id = radioIndex(oid, oid_nodes["max_power"])
                key = "%s|%s" % (ap_mac, radio_id)
                if key in oid_cache.keys():
                    oid_cache[key]["max_power"] = toInt(oid_infos[oid])

            responds = []
            for key in oid_cache.keys():
                radio = oid_cache[key]
                # 关闭的射频不入库
                if radio.get("channel_status", "") == "down":
                    continue
                responds.append({
                    "ap_mac": radio["ap_mac"],
                    "radio_id": radio["radio_id"],
                    "wlan_type": radio.get("wlan_type", ""),
                    "band": radio.get("band", ""),
                    "channel_status": radio.get("channel_status", "unknown"),
                    "channel": radio.get("channel"),
                    "bandwidth": radio.get("bandwidth"),
                    "utilization": radio.get("utilization"),
                    "interference_rate": radio.get("interference_rate"),
                    "client_count": radio.get("client_count", 0),
                    "tx_power": radio.get("tx_power"),
                    "max_power": radio.get("max_power"),
                    "ac_id": self.ac_id,
                })
            return responds
        except Exception as e:
            print("射频采集异常=", self.ip, str(e))
            return None

    async def __getH3cRadios(self):
        '''
        华三 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("射频采集跳过=%s 华三 profile 待补充" % self.ip)
        return None

    async def __getRuijieRadios(self):
        '''
        锐捷 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("射频采集跳过=%s 锐捷 profile 待补充" % self.ip)
        return None


if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = WlanRadio("172.25.7.253", "vdiannet", "huawei", 1)
        res = await a.getRadios()
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
