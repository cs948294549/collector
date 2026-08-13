from utils.snmp_tool import snmpwalk
import time

class PortInfo(object):
    '''
    普通设备采集节点：
    接口名称 = 1.3.6.1.2.1.2.2.1.2
    接口MAC = 1.3.6.1.2.1.2.2.1.6
    接口总带宽 = 1.3.6.1.2.1.31.1.1.1.15
    接口管理状态 = 1.3.6.1.2.1.2.2.1.7
    接口物理状态 = 1.3.6.1.2.1.2.2.1.8
    接口描述 = 1.3.6.1.2.1.31.1.1.1.18
    索引为最后1位 = 接口ID
    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type

    async def getPorts(self):
        port_info = await self.__getDefaultPortsInfo()
        return port_info

    async def __getDefaultPortsInfo(self):
        '''
        接口名称 = 1.3.6.1.2.1.2.2.1.2 或1.3.6.1.2.1.31.1.1.1.1
        接口MAC = 1.3.6.1.2.1.2.2.1.6
        接口总带宽 = 1.3.6.1.2.1.31.1.1.1.15
        接口管理状态 = 1.3.6.1.2.1.2.2.1.7
        接口物理状态 = 1.3.6.1.2.1.2.2.1.8
        接口描述 = 1.3.6.1.2.1.31.1.1.1.18

        '''

        oid_nodes = {
            "if_name": "1.3.6.1.2.1.2.2.1.2",
            "if_name_ex": "1.3.6.1.2.1.31.1.1.1.1",
            "mac_address": "1.3.6.1.2.1.2.2.1.6",
            "speed": "1.3.6.1.2.1.31.1.1.1.15",
            "admin_statu": "1.3.6.1.2.1.2.2.1.7",
            "oper_statu": "1.3.6.1.2.1.2.2.1.8",
            "alias": "1.3.6.1.2.1.31.1.1.1.18",# 64
        }
        # header = 80 byte
        # 40字节每节点，batch = 1*40+4*20+1*80, 最大batch = 1500/200 = 7.5,最好设置在20以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["if_name"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["if_name"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["if_name"] = oid_infos[oid].decode("utf-8", "ignore")
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["if_name"] = oid_infos[oid].decode("utf-8", "ignore")

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["if_name_ex"],
                                       max_repetitions=20)

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["if_name_ex"], "")[1:]
                if key in oid_cache.keys():
                    if oid_cache[key]["if_name"] == "":
                        oid_cache[key]["if_name"] = oid_infos[oid].decode("utf-8", "ignore")
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["if_name"] = oid_infos[oid].decode("utf-8", "ignore")

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mac_address"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["mac_address"], "")[1:]
                if key in oid_cache.keys():

                    oid_cache[key]["mac_address"] = ":".join(
                        [hex(int(i)).replace("0x", "").zfill(2).upper() for i in oid_infos[oid]])


            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["speed"],
                                       max_repetitions=30)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["speed"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["speed"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["speed"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["admin_statu"],
                                       max_repetitions=30)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["admin_statu"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["admin_statu"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["admin_statu"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["oper_statu"],
                                       max_repetitions=30)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["oper_statu"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["oper_statu"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["oper_statu"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["alias"],
                                       max_repetitions=10)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["alias"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["alias"] = oid_infos[oid].decode("utf-8", "ignore")
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["alias"] = oid_infos[oid].decode("utf-8", "ignore")

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                oid_cache[primary_key]["port_id"] = primary_key
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str
            return list(oid_cache.values())
        except Exception as e:
            print("接口信息采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = PortInfo("10.163.102.122", "Mrtg.Netease", "cisco")
        res = await a.getPorts()
        print(len(res))
        for i in res:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

