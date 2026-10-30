# WLAN AP 采集（wifi_ap）
from utils.snmp_tool import snmpwalk
import time


class WlanAP(object):
    '''
    AP 表采集：按 AC 的管理 IP 采集该 AC 下所有 AP

    各厂商 WLAN MIB 完全不同，按型号分开写，OID 与取值解析都在对应方法内部，
    输出结构保持一致（与 wifi_ap 表字段一一对应）。

    说明：lldp_port 的 OID 尚未按实机核对，
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
        elif self.vendor == "fortinet":
            return await self.__getFortinetAPs()
        else:
            print("AP采集跳过=%s 未支持的厂商=%s" % (self.ip, self.vendor))
            return None

    async def __getHuaweiAPs(self):
        '''
        华为 AC（AC6508 等）HUAWEI-WLAN-AP-MIB
        索引为 AP MAC(6 位)，统一转小写冒号格式
        运行状态 8=normal 为 online，其余均为 offline
        OID 需按实机 snmpwalk 核对后固化
        '''
        oid_nodes = {
            "sn": "1.3.6.1.4.1.2011.6.139.13.3.3.1.2",
            "model": "1.3.6.1.4.1.2011.6.139.13.3.3.1.3",
            "ap_name": "1.3.6.1.4.1.2011.6.139.13.3.3.1.4",
            "ap_group": "1.3.6.1.4.1.2011.6.139.13.3.3.1.5",
            "online_status": "1.3.6.1.4.1.2011.6.139.13.3.3.1.6",
            "sw_version": "1.3.6.1.4.1.2011.6.139.13.3.3.1.7",
            "ap_ip": "1.3.6.1.4.1.2011.6.139.13.3.3.1.13",
            "client_count": "1.3.6.1.4.1.2011.6.139.13.3.3.1.44",
            "lldp_name": "1.3.6.1.4.1.2011.6.139.13.3.6.1.8",
        }
        # 运行状态：8=normal 视为 online，其余（idle/autofind/fault/config/download/standby 等）均视为 offline
        normal_state = 8

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

            # AP SN
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sn"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["sn"])
                if ap_mac in oid_cache.keys():
                    oid_cache[ap_mac]["sn"] = toStr(oid_infos[oid])

            # AP 型号
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["model"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["model"])
                if ap_mac in oid_cache.keys():
                    oid_cache[ap_mac]["model"] = toStr(oid_infos[oid])

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
                    oid_cache[ap_mac]["online_status"] = "online" if state == normal_state else "offline"

            # 软件版本
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sw_version"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                ap_mac = macIndex(oid, oid_nodes["sw_version"])
                if ap_mac in oid_cache.keys():
                    oid_cache[ap_mac]["sw_version"] = toStr(oid_infos[oid])

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
                    "sn": ap.get("sn", ""),
                    "ap_group": ap.get("ap_group", ""),
                    "online_status": ap.get("online_status", "unknown"),
                    "ap_ip": ap.get("ap_ip", ""),
                    "model": ap.get("model", ""),
                    "sw_version": ap.get("sw_version", ""),
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

    async def __getFortinetAPs(self):
        '''
        飞塔 FortiGate 自带无线控制器（fgWc，1.3.6.1.4.1.12356.101.14）
        名称 / 管理状态在 Config 表（4.3.1），IP / 型号 / 版本 / 连接状态在 Session 表（4.4.1）
        索引为 vdom + WTP ID（变长字符串），WTP ID 即 AP 序列号，直接作 sn
        在线状态取 ConnectionState，不能用 WtpAdmin——后者是管理状态，AP 掉线后仍是 enable
        '''
        base = "1.3.6.1.4.1.12356.101.14."
        oid_nodes = {
            "admin": base + "4.3.1.2",
            "ap_name": base + "4.3.1.3",
            "ap_ip_remote": base + "4.4.1.3",
            "ap_ip": base + "4.4.1.5",
            "ap_mac": base + "4.4.1.6",
            "connection_state": base + "4.4.1.7",
            "ap_group": base + "4.4.1.11",
            "model": base + "4.4.1.12",
            "sw_version": base + "4.4.1.14",
            "client_count": base + "4.4.1.17",
        }
        # 连接状态：2=onLine 视为 online，其余（offLine / 下载镜像 / 待连接等）均视为 offline
        online_state = 2
        # 管理状态：1=discovered 为发现未授权，不入库
        admin_discovered = 1

        try:
            oid_cache = {}

            def wtpIndex(oid, prefix):
                # 变长串索引：vdom . 长度 n . n 个 ASCII 字符
                try:
                    keys = [int(i) for i in oid[len(prefix):].strip(".").split(".")]
                except ValueError:
                    return None
                if len(keys) < 2:
                    return None
                count = keys[1]
                if count <= 0 or len(keys) < 2 + count:
                    return None
                return "".join([chr(i) for i in keys[2:2 + count]])

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
                # PhysAddress 是 6 字节，按字节格式化，不能 decode；全 0 视为无效
                if isinstance(value, bytes) and len(value) == 6 and value != b"\x00" * 6:
                    return ":".join(["%02x" % b for b in value])
                return ""

            def toIp(value):
                # InetAddress 是 4 字节，按字节格式化；全 0 视为无效
                if isinstance(value, bytes) and len(value) == 4 and value != b"\x00" * 4:
                    return ".".join([str(b) for b in value])
                return ""

            async def fill(column_oid, field, convert=None):
                # 按 WTP ID 把一列填进 oid_cache，没有 MAC 的 AP 不建行
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=column_oid, max_repetitions=10)
                for oid in (oid_infos or {}).keys():
                    if oid_infos[oid] is None:
                        continue
                    wtp_id = wtpIndex(oid, column_oid)
                    if wtp_id is None or wtp_id not in oid_cache.keys():
                        continue
                    try:
                        oid_cache[wtp_id][field] = convert(oid_infos[oid]) if convert else oid_infos[oid]
                    except Exception:
                        continue

            # 以 MAC 建行：Session 表里没有 MAC 的 AP 落不了主键，直接跳过
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["ap_mac"], max_repetitions=10)
            for oid in (oid_infos or {}).keys():
                if oid_infos[oid] is None:
                    continue
                wtp_id = wtpIndex(oid, oid_nodes["ap_mac"])
                ap_mac = toMac(oid_infos[oid])
                if not wtp_id or not ap_mac:
                    continue
                oid_cache[wtp_id] = {"ap_mac": ap_mac, "sn": wtp_id}

            await fill(oid_nodes["ap_name"], "ap_name", toStr)
            await fill(oid_nodes["admin"], "admin", toInt)
            await fill(oid_nodes["connection_state"], "state", toInt)
            await fill(oid_nodes["ap_group"], "ap_group", toStr)
            await fill(oid_nodes["model"], "model", toStr)
            await fill(oid_nodes["sw_version"], "sw_version", toStr)
            await fill(oid_nodes["client_count"], "client_count", toInt)
            await fill(oid_nodes["ap_ip"], "ap_ip", toIp)
            # CAPWAP 源 IP，过 NAT 时与 AP 真实 IP 不同，只作兜底
            await fill(oid_nodes["ap_ip_remote"], "ap_ip_remote", toIp)

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            responds = []
            for wtp_id in oid_cache.keys():
                ap = oid_cache[wtp_id]
                # 发现未授权的 AP 不入库
                if ap.get("admin") == admin_discovered:
                    continue
                state = ap.get("state")
                if state is None:
                    online_status = "unknown"
                else:
                    online_status = "online" if state == online_state else "offline"
                responds.append({
                    "ap_mac": ap["ap_mac"],
                    "ap_name": ap.get("ap_name") or wtp_id,
                    "sn": ap["sn"],
                    "ap_group": ap.get("ap_group", ""),
                    "online_status": online_status,
                    "ap_ip": ap.get("ap_ip") or ap.get("ap_ip_remote") or "",
                    "model": ap.get("model", ""),
                    "sw_version": ap.get("sw_version", ""),
                    "client_count": ap.get("client_count") or 0,
                    "lldp_name": "",    # 飞塔 MIB 不提供 LLDP
                    "lldp_port": "",
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
