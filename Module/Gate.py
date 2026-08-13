from utils.snmp_tool import snmpwalk, ip2decimalism
import struct
import time


class Gate(object):
    '''
    普通设备采集节点：
    IP地址 = 1.3.6.1.2.1.4.20.1.1
    接口ID = 1.3.6.1.2.1.4.20.1.2
    子网掩码 = 1.3.6.1.2.1.4.20.1.3
    索引为最后四位 = IP

    ipv6接口ID = 1.3.6.1.2.1.55.1.8.1.2
    接口ID + IPV6(16)
    307.36.3.12.128.0.0.0.0.0.0.0.0.0.0.97.101 = INTEGER: 127
    307.254.128.0.0.0.0.0.0.62.140.64.255.254.8.58.57 = INTEGER: 10

    华三设备需特殊采集
    子网掩码 = 1.3.6.1.4.1.25506.2.67.1.1.2.1.4
    索引为最后一位 = 接口ID + 1 + 4 + IP地址
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
        elif self.sys_type == "arista":
            respond = await self.__getAristaIPtable()
        else:
            respond = await self.__getDefaultIPtable()
        return respond

    async def __getDefaultIPtable(self):
        '''
        1.3.6.1.2.1.4.20.1.2 = 接口ID[primary]
        1.3.6.1.2.1.4.20.1.3 = 子网掩码 [primary]
        '''
        oid_nodes = {
            "port_id": "1.3.6.1.2.1.4.20.1.2",
            "mask": "1.3.6.1.2.1.4.20.1.3",
        }
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["port_id"], max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["port_id"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["port_id"] = str(oid_infos[oid])
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["port_id"] = str(oid_infos[oid])

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mask"], max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["mask"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["mask"] = str(oid_infos[oid])
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["mask"] = str(oid_infos[oid])

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                oid_cache[primary_key]["gateway"] = ".".join(primary_key.split(".")[0:4])
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str

                gateint = ip2decimalism(oid_cache[primary_key]["gateway"])
                maskint = ip2decimalism(oid_cache[primary_key]["mask"])
                start = (gateint & maskint)
                end = (gateint | (~maskint) & 0xFFFFFFFF)
                oid_cache[primary_key]["startip"] = start
                oid_cache[primary_key]["endip"] = end

            required_key = ["port_id", "mask"]
            responds = []
            for i in list(oid_cache.values()):
                ff = False
                for k in required_key:
                    if k not in i.keys():
                        ff = True
                        break
                if ff is True:
                    continue
                else:
                    responds.append(i)
            return responds
        except Exception as e:
            print("网关采集异常=", self.ip, str(e))
            return None

    async def __getH3cIPtable(self):
        '''
        1.3.6.1.4.1.25506.2.67.1.1.2.1.4 = 子网掩码 [primary]
        ipv6 1.3.6.1.4.1.25506.2.71.1.1.2.1.4 = 子网掩码 [primary]
        '''
        oid_nodes = {
            "mask": "1.3.6.1.4.1.25506.2.67.1.1.2.1.4",
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
                oid_cache[primary_key]["gateway"] = ".".join(pri_keys[3:7])
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str

                gateint = ip2decimalism(oid_cache[primary_key]["gateway"])
                maskint = ip2decimalism(oid_cache[primary_key]["mask"])
                start = (gateint & maskint)
                end = (gateint | (~maskint) & 0xFFFFFFFF)
                oid_cache[primary_key]["startip"] = start
                oid_cache[primary_key]["endip"] = end

            required_key = ["port_id", "mask"]
            responds = []
            for i in list(oid_cache.values()):
                ff = False
                for k in required_key:
                    if k not in i.keys():
                        ff = True
                        break
                if ff is True:
                    continue
                else:
                    responds.append(i)
            return responds
        except Exception as e:
            print("h3c网关采集异常=", self.ip, str(e))
            return None

    async def __getAristaIPtable(self):
        '''
        1.3.6.1.2.1.4.20.1.2 = 接口ID[primary]
        1.3.6.1.2.1.4.20.1.3 = 子网掩码 [primary]
        通过 @ 可以采集对应vrf的地址
        '''
        oid_nodes = {
            "port_id": "1.3.6.1.2.1.4.20.1.2",
            "mask": "1.3.6.1.2.1.4.20.1.3",
        }
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["port_id"], max_repetitions=20)
            try:
                oid_infos1 = await snmpwalk(ip=self.ip, community=self.community+"@NENET_MGE", oid=oid_nodes["port_id"],
                                           max_repetitions=20)
                oid_infos.update(oid_infos1)
            except Exception as e:
                print("vrf获取portid失败", e)

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["port_id"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["port_id"] = str(oid_infos[oid])
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["port_id"] = str(oid_infos[oid])

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mask"], max_repetitions=20)
            try:
                oid_infos1 = await snmpwalk(ip=self.ip, community=self.community+"@NENET_MGE", oid=oid_nodes["mask"],
                                           max_repetitions=20)
                oid_infos.update(oid_infos1)
            except Exception as e:
                print("vrf获取mask失败", e)

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["mask"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["mask"] = str(oid_infos[oid])
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["mask"] = str(oid_infos[oid])

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                oid_cache[primary_key]["gateway"] = primary_key
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str

                gateint = ip2decimalism(oid_cache[primary_key]["gateway"])
                maskint = ip2decimalism(oid_cache[primary_key]["mask"])
                start = (gateint & maskint)
                end = (gateint | (~maskint) & 0xFFFFFFFF)
                oid_cache[primary_key]["startip"] = start
                oid_cache[primary_key]["endip"] = end

            required_key = ["port_id", "mask"]
            responds = []
            for i in list(oid_cache.values()):
                ff = False
                for k in required_key:
                    if k not in i.keys():
                        ff = True
                        break
                if ff is True:
                    continue
                else:
                    responds.append(i)

            return responds
        except Exception as e:
            print("网关采集异常=", self.ip, str(e))
            return None

    async def __getCiscoIPtable(self):
        '''
        1.3.6.1.2.1.4.20.1.2 = 接口ID[primary]
        1.3.6.1.2.1.4.20.1.3 = 子网掩码 [primary]
        通过@ 可以采集对应vrf的地址
        snmp-server context jtbgp vrf JTBGP
        思科需要添加配置，将vrf映射一下
        '''
        oid_nodes = {
            "port_id": "1.3.6.1.2.1.4.20.1.2",
            "mask": "1.3.6.1.2.1.4.20.1.3",
        }
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["port_id"], max_repetitions=20)
            try:
                oid_infos1 = await snmpwalk(ip=self.ip, community=self.community+"@mgmt", oid=oid_nodes["port_id"],
                                           max_repetitions=20)
                oid_infos.update(oid_infos1)
            except Exception as e:
                print("vrf获取portid失败", e)

            try:
                oid_infos2 = await snmpwalk(ip=self.ip, community=self.community+"@management", oid=oid_nodes["port_id"],
                                           max_repetitions=20)
                oid_infos.update(oid_infos2)
            except Exception as e:
                print("vrf获取portid失败", e)

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["port_id"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["port_id"] = str(oid_infos[oid])
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["port_id"] = str(oid_infos[oid])

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mask"], max_repetitions=20)
            try:
                oid_infos1 = await snmpwalk(ip=self.ip, community=self.community+"@mgmt", oid=oid_nodes["mask"],
                                           max_repetitions=20)
                oid_infos.update(oid_infos1)
            except Exception as e:
                print("vrf获取mask失败", e)

            try:
                oid_infos2 = await snmpwalk(ip=self.ip, community=self.community+"@management", oid=oid_nodes["mask"],
                                           max_repetitions=20)
                oid_infos.update(oid_infos2)
            except Exception as e:
                print("vrf获取mask失败", e)

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    continue
                key = oid.replace(oid_nodes["mask"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["mask"] = str(oid_infos[oid])
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["mask"] = str(oid_infos[oid])

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                oid_cache[primary_key]["gateway"] = primary_key
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str

                gateint = ip2decimalism(oid_cache[primary_key]["gateway"])
                maskint = ip2decimalism(oid_cache[primary_key]["mask"])
                start = (gateint & maskint)
                end = (gateint | (~maskint) & 0xFFFFFFFF)
                oid_cache[primary_key]["startip"] = start
                oid_cache[primary_key]["endip"] = end

            required_key = ["port_id", "mask"]
            responds = []
            for i in list(oid_cache.values()):
                ff = False
                for k in required_key:
                    if k not in i.keys():
                        ff = True
                        break
                if ff is True:
                    continue
                else:
                    responds.append(i)
            return responds
        except Exception as e:
            print("网关采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = Gate("10.80.173.232", "Mrtg.Netease", "arista")
        res = await a.getGates()
        for i in res:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

