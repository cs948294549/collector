# WLAN AP 采集（wifi_ap）
from utils.snmp_tool import snmpwalk
import time


class WlanAP(object):
    '''
    AP 表采集：按 AC 的管理 IP 采集该 AC 下所有 AP

    各厂商 WLAN MIB 完全不同，按型号分开写，OID 与取值解析都在对应方法内部，
    输出结构保持一致（与 wifi_ap 表字段一一对应）。

    说明：model / sw_version / lldp_port 的 OID 尚未按实机核对，
          方法里先置空，采不到的字段入库为空，不影响采集跑通。
    '''
    def __init__(self, ip, community="public", vendor="huawei", ac_id=0):
        self.ip = ip
        self.community = community
        self.vendor = str(vendor or "").strip().lower()
        self.ac_id = ac_id

    async def getAPs(self):
        '''
        返回 AP 列表；采集失败或厂商未支持时返回 None
        '''
        if self.vendor == "huawei":
            return await self.__getHuaweiAPs()
        elif self.vendor == "h3c":
            return await self.__getH3cAPs()
        elif self.vendor == "ruijie":
            return await self.__getRuijieAPs()
        else:
            print("AP采集跳过=%s 未支持的厂商=%s" % (self.ip, self.vendor))
            return None

    async def __getHuaweiAPs(self):
        '''
        华为 AC（AC6508 等）HUAWEI-WLAN-AP-MIB
        索引为 AP MAC(6 位)，统一转小写冒号格式
        在线状态注释见方法内 state_map
        OID 需按实机 snmpwalk 核对后固化
        '''
        oid_nodes = {
            "ap_name": "1.3.6.1.4.1.2011.6.139.13.3.3.1.4",
            "ap_group": "1.3.6.1.4.1.2011.6.139.13.3.3.1.5",
            "online_status": "1.3.6.1.4.1.2011.6.139.13.3.3.1.6",
            "ap_ip": "1.3.6.1.4.1.2011.6.139.13.3.3.1.13",
            "client_count": "1.3.6.1.4.1.2011.6.139.13.3.3.1.44",
            "lldp_name": "1.3.6.1.4.1.2011.6.139.13.3.6.1.8",
        }
        # 在线状态枚举，取值含义待实机确认
        state_map = {1: "online", 2: "offline"}

        try:
            oid_cache = {}

            def macIndex(oid, prefix):
                keys = oid[len(prefix):].strip(".").split(".")
                if len(keys) < 6:
                    return None
                return ":".join(["%02x" % int(i) for i in keys[:6]])

            def toStr(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", "ignore").strip()
                return str(value).strip()

            # AP 名称
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ap_name"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["ap_name"])
                if ap_mac is None:
                    continue
                if ap_mac not in oid_cache.keys():
                    oid_cache[ap_mac] = {}
                oid_cache[ap_mac]["ap_name"] = toStr(oid_infos[oid])

            # AP 分组
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ap_group"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["ap_group"])
                if ap_mac in oid_cache.keys():
                    oid_cache[ap_mac]["ap_group"] = toStr(oid_infos[oid])

            # 运行状态
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["online_status"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["online_status"])
                if ap_mac in oid_cache.keys():
                    try:
                        state = int(oid_infos[oid])
                    except Exception:
                        continue
                    oid_cache[ap_mac]["online_status"] = state_map.get(state, "unknown")

            # AP IP
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ap_ip"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["ap_ip"])
                if ap_mac in oid_cache.keys():
                    oid_cache[ap_mac]["ap_ip"] = toStr(oid_infos[oid])

            # 用户数
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["client_count"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["client_count"])
                if ap_mac in oid_cache.keys():
                    try:
                        oid_cache[ap_mac]["client_count"] = int(oid_infos[oid])
                    except Exception:
                        oid_cache[ap_mac]["client_count"] = 0

            # 上级设备（需 AP 支持 LLDP，取不到留空）
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["lldp_name"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["lldp_name"])
                if ap_mac in oid_cache.keys():
                    oid_cache[ap_mac]["lldp_name"] = toStr(oid_infos[oid])

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            responds = []
            for ap_mac in oid_cache.keys():
                ap = oid_cache[ap_mac]
                responds.append({
                    "ap_mac": ap_mac,
                    "ap_name": ap.get("ap_name", ""),
                    "ap_group": ap.get("ap_group", ""),
                    "online_status": ap.get("online_status", "unknown"),
                    "ap_ip": ap.get("ap_ip", ""),
                    "model": "",        # 型号 OID 待补
                    "sw_version": "",   # 软件版本 OID 待补
                    "client_count": ap.get("client_count", 0),
                    "lldp_name": ap.get("lldp_name", ""),
                    "lldp_port": "",    # 上级端口 OID 待补
                    "ac_id": self.ac_id,
                    "last_seen_at": timestamp_str,
                })
            return responds
        except Exception as e:
            print("AP采集异常=", self.ip, str(e))
            return None

    async def __getH3cAPs(self):
        '''
        华三 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("AP采集跳过=%s 华三 profile 待补充" % self.ip)
        return None

    async def __getRuijieAPs(self):
        '''
        锐捷 WLAN MIB 待按实机 snmpwalk 补齐
        补齐时在此方法内写 OID 与解析，输出字段与华为方法保持一致
        '''
        print("AP采集跳过=%s 锐捷 profile 待补充" % self.ip)
        return None


if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = WlanAP("172.25.7.253", "vdiannet", "huawei", 1)
        res = await a.getAPs()
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
