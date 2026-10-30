# WLAN 射频采集（wifi_radio）
from utils.snmp_tool import snmpwalk
from utils.fortinet_api import fetch_monitor
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
        elif self.vendor == "fortinet":
            return await self.__getFortinetRadios()
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

    async def __getFortinetRadios(self):
        '''
        飞塔 FortiGate 自带无线控制器（fgWc，1.3.6.1.4.1.12356.101.14）
        运行态（模式 / 信道 / 功率 / 终端数）在 SessRadio 表（4.5.1），索引 vdom + WTP ID + 射频 ID
        频段与信道宽度只有 profile 配置值，在 ProfRadio 表（4.2.1），索引 vdom + profile 名 + 射频 ID
        WTP ID → AP MAC、WTP ID → profile 取 Session 表（4.4.1）
        只保留 ap 模式的射频，monitor / disabled 等不入库
        '''
        base = "1.3.6.1.4.1.12356.101.14."
        oid_nodes = {
            "ap_mac": base + "4.4.1.6",
            "profile": base + "4.4.1.11",
            "mode": base + "4.5.1.3",
            "channel": base + "4.5.1.7",
            "tx_power": base + "4.5.1.8",
            "client_count": base + "4.5.1.9",
            "band": base + "4.2.1.11",
            "bandwidth": base + "4.2.1.20",
        }
        # 射频模式：3=ap 为业务射频，其余（notExist/disabled/monitor/sniffer）均不入库
        mode_ap = 3
        # FgWcWtpRadioType 枚举 → 频段
        band_map = {
            2: "2.4G", 3: "2.4G", 5: "2.4G", 7: "2.4G", 8: "2.4G", 9: "2.4G",
            13: "2.4G", 16: "2.4G", 17: "2.4G", 18: "2.4G",
            1: "5G", 4: "5G", 6: "5G", 10: "5G", 11: "5G", 12: "5G",
            14: "5G", 19: "5G", 20: "5G", 21: "5G",
            15: "6G",
        }
        # FgWcWtpRadioType 枚举 → 协议
        type_map = {
            1: "802.11a", 2: "802.11b", 3: "802.11g", 8: "802.11g",
            4: "802.11n", 5: "802.11n", 7: "802.11n", 9: "802.11n", 10: "802.11n",
            6: "802.11ac", 11: "802.11ac", 12: "802.11ac",
            13: "802.11ax", 14: "802.11ax", 15: "802.11ax", 16: "802.11ax", 17: "802.11ax",
            18: "802.11ax", 19: "802.11ax", 20: "802.11ax", 21: "802.11ax",
        }
        # FgWcWtpChannelWidthType 枚举 → MHz，0=other 不填
        width_map = {1: 20, 2: 40, 3: 80, 4: 160}

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

            # WTP ID → profile
            profiles = {}
            for index, value in (await walkIndex(oid_nodes["profile"])).items():
                profiles[index[0]] = toStr(value)

            # 射频模式：以 SessRadio 表为行集，只建 ap 模式且能映射到 AP 的射频
            for index, value in (await walkIndex(oid_nodes["mode"])).items():
                if len(index) < 2 or index[0] not in ap_macs.keys():
                    continue
                if toInt(value) != mode_ap:
                    continue
                oid_cache[index[:2]] = {"ap_mac": ap_macs[index[0]], "radio_id": index[1], "client_count": 0}

            # 信道
            for index, value in (await walkIndex(oid_nodes["channel"])).items():
                if index[:2] in oid_cache.keys():
                    oid_cache[index[:2]]["channel"] = toInt(value)

            # 当前功率
            for index, value in (await walkIndex(oid_nodes["tx_power"])).items():
                if index[:2] in oid_cache.keys():
                    oid_cache[index[:2]]["tx_power"] = toInt(value)

            # 射频在线数量
            for index, value in (await walkIndex(oid_nodes["client_count"])).items():
                if index[:2] in oid_cache.keys():
                    oid_cache[index[:2]]["client_count"] = toInt(value) or 0

            # 频段 / 信道宽度：按 (profile, 射频 ID) 查
            bands = {}
            for index, value in (await walkIndex(oid_nodes["band"])).items():
                if len(index) >= 2:
                    bands[index[:2]] = value
            widths = {}
            for index, value in (await walkIndex(oid_nodes["bandwidth"])).items():
                if len(index) >= 2:
                    widths[index[:2]] = toInt(value)

            # REST 补采：MIB 没有任何利用率字段，频段/带宽/协议也只有 profile 配置值
            # 接口失败时这里返回空字典，射频仍按 SNMP 结果出，utilization 保持 None
            api_radios = await self.__getFortinetApiRadios()

            responds = []
            for (wtp_id, radio_id) in oid_cache.keys():
                radio = oid_cache[(wtp_id, radio_id)]
                profile_key = (profiles.get(wtp_id, ""), radio_id)
                band_type = toInt(bands.get(profile_key))
                band = band_map.get(band_type, "")
                channel = radio.get("channel")
                # 枚举外（如新型号）按信道兜底，6G 信道号与 2.4G 重叠，兜底不出 6G
                if not band and channel:
                    band = "2.4G" if channel <= 14 else "5G"
                if band_type in type_map.keys():
                    wlan_type = type_map[band_type]
                else:
                    wlan_type = toStr(bands[profile_key]) if profile_key in bands.keys() else ""
                item = {
                    "ap_mac": radio["ap_mac"],
                    "radio_id": radio_id,
                    "wlan_type": wlan_type,
                    "band": band,
                    "channel_status": "up",     # 非 ap 模式的已在建行时丢弃
                    "channel": channel,
                    "bandwidth": width_map.get(widths.get(profile_key)),
                    "utilization": None,        # 飞塔 MIB 不提供
                    "interference_rate": None,
                    "client_count": radio.get("client_count", 0),
                    "tx_power": radio.get("tx_power"),
                    "max_power": None,
                    "ac_id": self.ac_id,
                }
                # 先按 WTP ID 匹配，取不到再按 AP MAC（两者在实机上都唯一）
                api_radio = api_radios.get((wtp_id, radio_id)) or api_radios.get((radio["ap_mac"], radio_id))
                if api_radio:
                    self.__overlayApiRadio(item, api_radio)
                responds.append(item)
            return responds
        except Exception as e:
            print("射频采集异常=", self.ip, str(e))
            return None

    async def __getFortinetApiRadios(self):
        '''
        REST /api/v2/monitor/wifi/managed_ap 的 AP 模式射频，按 (WTP ID 或 AP MAC, 射频 ID) 建索引
        接口不可用时返回空字典，调用方据此保留 SNMP 结果
        '''
        rows = await fetch_monitor(self.ip, "wifi/managed_ap")
        if not isinstance(rows, list):
            return {}

        def toInt(value):
            try:
                return int(str(value).strip())
            except Exception:
                return None

        index = {}
        for ap in rows:
            if not isinstance(ap, dict):
                continue
            serial = str(ap.get("wtp_id") or "").strip()
            ap_mac = str(ap.get("board_mac") or "").strip().lower()
            for radio in (ap.get("radio") or []):
                if not isinstance(radio, dict):
                    continue
                # monitor / disabled 等射频不在采集范围内，和 SNMP 路径口径保持一致
                if str(radio.get("mode") or "").upper() != "AP":
                    continue
                radio_id = toInt(radio.get("radio_id"))
                if radio_id is None:
                    continue
                if serial:
                    index[(serial, radio_id)] = radio
                if ap_mac:
                    index[(ap_mac, radio_id)] = radio
        return index

    def __overlayApiRadio(self, item, radio):
        '''
        用 REST 字段覆盖射频行；只覆盖取得到值的字段，取不到就保留 SNMP 结果
        '''
        # channel_utilization_percent：整数 0-100，GUI 上的"信道利用率"
        utilization = radio.get("channel_utilization_percent")
        if isinstance(utilization, (int, float)):
            item["utilization"] = round(float(utilization), 2)

        # radio_type 形如 802.11ax-5G：前半是协议，后半是频段，比 profile 配置值更贴近运行态
        radio_type = str(radio.get("radio_type") or "").strip()
        if radio_type:
            protocol, _, band_tag = radio_type.partition("-")
            if protocol:
                item["wlan_type"] = protocol
            band = {"2G": "2.4G", "5G": "5G", "6G": "6G"}.get(band_tag.upper())
            if band:
                item["band"] = band

        # channel_bonding 形如 20MHz / 40MHz，是实际协商宽度而非配置值
        bonding = str(radio.get("channel_bonding") or "").strip().rstrip("MmHhzZ")
        if bonding.isdigit():
            item["bandwidth"] = int(bonding)

        # oper_chan / oper_txpower 是运行态，优先于 SNMP 值
        channel = radio.get("oper_chan")
        if isinstance(channel, int) and channel > 0:
            item["channel"] = channel
            # 信道变了，SNMP 那条"按信道兜底"的频段结论也要跟着刷新
            if not str(radio.get("radio_type") or "").strip():
                item["band"] = "2.4G" if channel <= 14 else "5G"
        tx_power = radio.get("oper_txpower")
        if isinstance(tx_power, int):
            item["tx_power"] = tx_power

        client_count = radio.get("client_count")
        if isinstance(client_count, int) and client_count >= 0:
            item["client_count"] = client_count

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
