from utils.snmp_tool import snmpwalk
import struct
import re
import time

def ipv6_trans(ipv6_arrys):
    key = 0
    ipv6_units = []
    for i in ipv6_arrys:
        if key % 2 == 1:
            ipv6_unit = hex(int(i)).replace("0x", "").zfill(2)
            ipv6_units.append(ipv6_unit)
        else:
            ipv6_unit = hex(int(i)).replace("0x", "")
            ipv6_units.append(ipv6_unit)
        key += 1

    ipv6_addrs = []
    for i in range(0, len(ipv6_units), 2):
        ipv6_unit = ipv6_units[i] + ipv6_units[i + 1]
        ipv6_unit = re.sub("^0+", "", ipv6_unit, count=0)
        if "" == ipv6_unit:
            ipv6_unit = "0"
        ipv6_addrs.append(ipv6_unit)
    ipv6_addrs.reverse()
    ipv6_addr = ":".join(ipv6_addrs)
    ipv6_zip = re.sub("(:0){2,}", ":", ipv6_addr, count=1)
    ipv6_addrs = ipv6_zip.split(":")
    ipv6_addrs.reverse()
    ipv6_addr = ":".join(ipv6_addrs)
    ipv6_zip = re.sub("^0::", "::", ipv6_addr, count=0)
    return ipv6_zip

class Gate_ipv6(object):
    '''
    普通设备采集节点：
    ipv6接口ID = 1.3.6.1.2.1.55.1.8.1.2
    接口ID + IPV6(16)
    307.36.3.12.128.0.0.0.0.0.0.0.0.0.0.97.101 = INTEGER: 127
    307.254.128.0.0.0.0.0.0.62.140.64.255.254.8.58.57 = INTEGER: 10

    华三设备需特殊采集
    子网掩码ipv6 = 1.3.6.1.4.1.25506.2.71.1.1.2.1.4
    接口ID + 2 + 16 + IPV6
    307.2.16.36.3.12.128.0.0.0.0.0.0.0.0.0.0.97.101
    2403:C80::6165 =
    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type

    async def getGates(self):
        if self.sys_type == "h3c":
            respond = await self.__getH3cIPtable()
        elif "cisco" in self.sys_type:
            respond = await self.__getCiscoIPtable()
        else:
            respond = await self.__getDefaultIPtable()
        return respond

    async def __getDefaultIPtable(self):
        '''
        1.3.6.1.2.1.55.1.8.1.2 = 掩码长度[primary]
        '''
        oid_nodes = {
            "mask": "1.3.6.1.2.1.55.1.8.1.2"
        }
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mask"], max_repetitions=15)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["mask"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["mask"] = str(oid_infos[oid])
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["mask"] = str(oid_infos[oid])

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                pri_keys = primary_key.split(".")
                oid_cache[primary_key]["port_id"] = pri_keys[0]
                oid_cache[primary_key]["gateway"] = ipv6_trans(pri_keys[1:])
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str
            responds = list(oid_cache.values())
            return responds
        except Exception as e:
            print("网关采集异常=", self.ip, str(e))
            return None

    async def __getH3cIPtable(self):
        '''
        ipv6 1.3.6.1.4.1.25506.2.71.1.1.2.1.4 = 子网掩码 [primary]
        '''
        oid_nodes = {
            "mask": "1.3.6.1.4.1.25506.2.71.1.1.2.1.4",
        }
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mask"], max_repetitions=30)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["mask"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["mask"] = str(oid_infos[oid])
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["mask"] = str(oid_infos[oid])

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                pri_keys = primary_key.split(".")
                oid_cache[primary_key]["port_id"] = pri_keys[0]
                oid_cache[primary_key]["gateway"] = ipv6_trans(pri_keys[3:])
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str
            responds = list(oid_cache.values())
            return responds
        except Exception as e:
            print("h3c网关采集异常=", self.ip, str(e))
            return None

    async def __getCiscoIPtable(self):
        '''
        ipv6
        1.3.6.1.2.1.4.34.1.3 = 接口id[primary]
        1.3.6.1.2.1.4.34.1.5 = 掩码长度
        '''
        oid_nodes = {
            "port_id": "1.3.6.1.2.1.4.34.1.3",
            "mask_len": "1.3.6.1.2.1.4.34.1.5"
        }
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["port_id"], max_repetitions=30)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["port_id"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["port_id"] = str(oid_infos[oid])
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["port_id"] = str(oid_infos[oid])

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mask_len"],
                                       max_repetitions=10)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["mask_len"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["mask"] = str(oid_infos[oid]).split(".")[-1]
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["mask"] = str(oid_infos[oid]).split(".")[-1]

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            gate_ipv6s = []
            for primary_key in oid_cache.keys():
                pri_keys = primary_key.split(".")
                if pri_keys[0] == "1":
                    continue
                elif pri_keys[0] == "2":
                    _ipv6_array = pri_keys[2:18]
                    oid_cache[primary_key]["gateway"] = ipv6_trans(_ipv6_array)
                    oid_cache[primary_key]["ip"] = self.ip
                    oid_cache[primary_key]["timestamp"] = timestamp_str
                    gate_ipv6s.append(oid_cache[primary_key])
                else:
                    continue

            responds = gate_ipv6s
            return responds
        except Exception as e:
            print("h3c网关采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = Gate_ipv6("10.220.16.1", "Mrtg.Netease", "h3c")
        res = await a.getGates()
        for i in res:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

