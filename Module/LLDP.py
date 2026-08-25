# LLDP
from utils.snmp_tool import snmpwalk, snmpget
import time
import struct
import re


class LLDPInfo(object):
    '''
    普通设备采集节点：(由于端口ID不是全设备通用，因此采用端口名称进行关联)
    本端端口名称 = 1.0.8802.1.1.2.1.3.7.1.3
    本端端口描述 = 1.0.8802.1.1.2.1.3.7.1.4
    对端端口名称 = 1.0.8802.1.1.2.1.4.1.1.7
    对端端口描述 = 1.0.8802.1.1.2.1.4.1.1.8
    对端设备名称 = 1.0.8802.1.1.2.1.4.1.1.9
    对端设备描述 = 1.0.8802.1. 1.2.1.4.1.1.10

    对端管理地址 = 1.0.8802.1.1.2.1.4.2.1.4

    1.3.7 索引为 最后一位 ID
    iso.0.8802.1.1.2.1.3.7.1.3.112 = STRING: "Ten-GigabitEthernet2/0/49"
    1.4.1 索引为 最后三位 时间 + 本端端口ID + 远端端口序号
    iso.0.8802.1.1.2.1.4.1.1.9.1849895490.49.1 = STRING: "GM_NHZ05_M06_R03R04N03_BGP_NE_S12508_DSW_104.9"
    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type


    async def getLLDPInfos(self):
        lldp_infos = await self.__getDefaultgetLLDPInfo()
        return lldp_infos


    async def __getDefaultgetLLDPInfo(self):
        '''
        本端端口名称 = 1.0.8802.1.1.2.1.3.7.1.3
        本端端口描述 = 1.0.8802.1.1.2.1.3.7.1.4
        对端端口名称 = 1.0.8802.1.1.2.1.4.1.1.7
        对端端口描述 = 1.0.8802.1.1.2.1.4.1.1.8
        对端设备名称 = 1.0.8802.1.1.2.1.4.1.1.9
        '''

        oid_nodes = {
            "rem_portname": "1.0.8802.1.1.2.1.4.1.1.7", # 80
            "rem_portalias": "1.0.8802.1.1.2.1.4.1.1.8", # 150
            "rem_name": "1.0.8802.1.1.2.1.4.1.1.9", # 40
            "sysdesc": "1.3.6.1.2.1.1.1.0",
            "rem_sysdesc": "1.0.8802.1.1.2.1.4.1.1.10"
        }

        reg_gi = re.compile("Gi(?=[\d])", re.I)
        reg_eth = re.compile("Eth(?=[\d])", re.I)
        reg_te = re.compile("Te(?=[\d])", re.I)
        reg_hu = re.compile("Hu(?=[\d])", re.I)
        reg_be = re.compile("BE(?=[\d])", re.I)
        reg_mg = re.compile("Mg(?=[\d])", re.I)
        reg_ruijie = re.compile("ruijie", re.I)
        reg_c31x0 = re.compile("S31X0|C3560", re.I)


        # header = 80 byte
        # 40字节每节点，batch = 200, 最大batch = 1500/200 = 7.5,最好设置在20以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["rem_portname"],
                                       max_repetitions=5)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["rem_portname"], "")[1:]
                key = ".".join(key.split(".")[-2:])
                try:
                    port_name = oid_infos[oid].decode("utf-8")
                except Exception as e:
                    port_name = ":".join([str(hex(dd))[2:].upper().zfill(2) for dd in struct.unpack("!6B", oid_infos[oid])])
                if key in oid_cache.keys():
                    oid_cache[key]["rem_portname"] = port_name
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["rem_portname"] = port_name

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["rem_portalias"],
                                   max_repetitions=5)

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["rem_portalias"], "")[1:]
                key = ".".join(key.split(".")[-2:])
                if key in oid_cache.keys():
                    oid_cache[key]["rem_portalias"] = oid_infos[oid].decode("utf-8", "ignore")
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["rem_portalias"] = oid_infos[oid].decode("utf-8", "ignore")

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["rem_name"],
                                   max_repetitions=5)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["rem_name"], "")[1:]
                key = ".".join(key.split(".")[-2:])
                if key in oid_cache.keys():
                    oid_cache[key]["rem_name"] = oid_infos[oid].decode("utf-8", "ignore")
                    oid_cache[key]["rem_name"] = oid_cache[key]["rem_name"].replace(".vdian.net", "")
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["rem_name"] = oid_infos[oid].decode("utf-8", "ignore")

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["rem_sysdesc"],
                                       max_repetitions=2)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["rem_sysdesc"], "")[1:]
                key = ".".join(key.split(".")[-2:])
                if key in oid_cache.keys():
                    oid_cache[key]["rem_sysdesc"] = oid_infos[oid].decode("utf-8", "ignore")

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                oid_cache[primary_key]["port_id"] = primary_key
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str

            sysdesc = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["sysdesc"])
            sysdesc = sysdesc.decode("utf-8", "ignore")

            result = []
            for i in oid_cache.values():
                pid = i["port_id"].split(".")[0]
                loc_portname = await snmpget(ip=self.ip, community=self.community, oid="1.0.8802.1.1.2.1.3.7.1.3.%s" % pid)
                loc_portalias = await snmpget(ip=self.ip, community=self.community, oid="1.0.8802.1.1.2.1.3.7.1.4.%s" % pid)
                if loc_portname is not None and loc_portalias is not None:
                    i["loc_portname"] = loc_portname.decode("utf-8", "ignore")
                    i["loc_portalias"] = loc_portalias.decode("utf-8", "ignore")

                    # 添加还原端口处理
                    if i["loc_portname"] != "":
                        if i["loc_portname"][0] == "G":
                            if len(reg_ruijie.findall(sysdesc)) > 0:
                                i["loc_portname"] = reg_gi.sub("GigabitEthernet ", i["loc_portname"])
                            else:
                                i["loc_portname"] = reg_gi.sub("GigabitEthernet", i["loc_portname"])
                        elif i["loc_portname"][0] == "E":
                            i["loc_portname"] = reg_eth.sub("Ethernet", i["loc_portname"])
                        elif i["loc_portname"][0] == "T":
                            if len(reg_ruijie.findall(sysdesc)) > 0:
                                i["loc_portname"] = reg_te.sub("TenGigabitEthernet ", i["loc_portname"])
                            else:
                                if len(reg_c31x0.findall(sysdesc)) > 0:
                                    i["loc_portname"] = reg_te.sub("TenGigabitEthernet", i["loc_portname"])
                                elif "Cisco IOS" in sysdesc:
                                    i["loc_portname"] = reg_te.sub("TenGigabitEthernet", i["loc_portname"])
                                else:
                                    i["loc_portname"] = reg_te.sub("TenGigE", i["loc_portname"])
                        elif i["loc_portname"][0] == "H":
                            i["loc_portname"] = reg_hu.sub("HundredGigE", i["loc_portname"])
                        elif i["loc_portname"][0] == "B":
                            i["loc_portname"] = reg_be.sub("Bundle-Ether", i["loc_portname"])
                        elif i["loc_portname"][0] == "M":
                            i["loc_portname"] = reg_mg.sub("Mgmt ", i["loc_portname"])
                        else:
                            pass
                    else:
                        pass

                    if i["rem_portname"] != "":
                        if i["rem_portname"][0] == "G":
                            if len(reg_ruijie.findall(i["rem_sysdesc"])) > 0:
                                i["rem_portname"] = reg_gi.sub("GigabitEthernet ", i["rem_portname"])
                            else:
                                i["rem_portname"] = reg_gi.sub("GigabitEthernet", i["rem_portname"])
                        elif i["rem_portname"][0] == "E":
                            i["rem_portname"] = reg_eth.sub("Ethernet", i["rem_portname"])
                        elif i["rem_portname"][0] == "T":
                            if len(reg_ruijie.findall(i["rem_sysdesc"])) > 0:
                                i["rem_portname"] = reg_te.sub("TenGigabitEthernet ", i["rem_portname"])
                            else:
                                if len(reg_c31x0.findall(i["rem_sysdesc"])) > 0:
                                    i["rem_portname"] = reg_te.sub("TenGigabitEthernet", i["rem_portname"])
                                elif "Cisco IOS" in i["rem_sysdesc"]:
                                    i["rem_portname"] = reg_te.sub("TenGigabitEthernet", i["rem_portname"])
                                else:
                                    i["rem_portname"] = reg_te.sub("TenGigE", i["rem_portname"])

                        elif i["rem_portname"][0] == "H":
                            i["rem_portname"] = reg_hu.sub("HundredGigE", i["rem_portname"])
                        elif i["rem_portname"][0] == "B":
                            i["rem_portname"] = reg_be.sub("Bundle-Ether", i["rem_portname"])
                        elif i["rem_portname"][0] == "M":
                            i["rem_portname"] = reg_mg.sub("Mgmt ", i["rem_portname"])
                        else:
                            pass
                    else:
                        pass
                    result.append(i)
            return result
        except Exception as e:
            print("LLDP采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = LLDPInfo("10.80.166.118", "Mrtg.Netease", "h3c")
        res = await a.getLLDPInfos()
        for i in res:
            print(i)
            if "rem_name" not in i.keys():
                print("===", i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

