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
        elif self.vendor == "fortinet":
            return await self.__getFortinetSSIDs()
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
        # SSID 状态：1=normal 视为 up，其余均视为 down
        normal_state = 1

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
                    if state is None:
                        continue
                    oid_cache[key]["ssid_status"] = "up" if state == normal_state else "down"

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

    async def __getFortinetSSIDs(self):
        '''
        飞塔 FortiGate 自带无线控制器（fgWc，1.3.6.1.4.1.12356.101.14）
        SessVap 表（4.6.1）索引 vdom + WTP ID + 射频 ID + VAP ifIndex
        seq 取 VAP ifIndex：VAP 是全局接口，编号跨采集稳定
        表里没有状态列，出现在 SessVap 即视为在播，状态固定 up
        WTP ID → AP MAC 取 Session 表（4.4.1），射频模式取 SessRadio 表（4.5.1）
        '''
        base = "1.3.6.1.4.1.12356.101.14."
        oid_nodes = {
            "ap_mac": base + "4.4.1.6",
            "mode": base + "4.5.1.3",
            "ssid": base + "4.6.1.3",
            "client_count": base + "4.6.1.4",
        }
        # 射频模式：3=ap，只保留 ap 射频下的 SSID
        mode_ap = 3

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

            # WTP ID → AP MAC
            ap_macs = {}
            for index, value in (await walkIndex(oid_nodes["ap_mac"])).items():
                ap_mac = toMac(value)
                if ap_mac:
                    ap_macs[index[0]] = ap_mac

            # (WTP ID, 射频 ID) → 射频模式
            modes = {}
            for index, value in (await walkIndex(oid_nodes["mode"])).items():
                if len(index) >= 2:
                    modes[index[:2]] = toInt(value)

            # SSID 名称：以 SessVap 表为行集
            for index, value in (await walkIndex(oid_nodes["ssid"])).items():
                if len(index) < 3 or index[0] not in ap_macs.keys():
                    continue
                # 射频模式查得到且不是 ap 的丢弃（正常 monitor 射频不会出现在 VAP 表，这里是防御）
                mode = modes.get(index[:2])
                if mode is not None and mode != mode_ap:
                    continue
                oid_cache[index[:3]] = {
                    "ap_mac": ap_macs[index[0]],
                    "radio_id": index[1],
                    "seq": index[2],
                    "ssid": toStr(value),
                    "client_count": 0,
                }

            # 在线数量
            for index, value in (await walkIndex(oid_nodes["client_count"])).items():
                if index[:3] in oid_cache.keys():
                    oid_cache[index[:3]]["client_count"] = toInt(value) or 0

            responds = []
            for key in oid_cache.keys():
                item = oid_cache[key]
                responds.append({
                    "ap_mac": item["ap_mac"],
                    "radio_id": item["radio_id"],
                    "seq": item["seq"],
                    "ssid": item.get("ssid", ""),
                    "client_count": item.get("client_count", 0),
                    "ssid_status": "up",
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
