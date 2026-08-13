from utils.snmp_tool import snmpwalk, snmpget
import time

class PhysicalInfo(object):
    '''
    普通设备采集节点：
    硬件名称 = 1.3.6.1.2.1.47.1.1.1.1.2
    硬件类型 = 1.3.6.1.2.1.47.1.1.1.1.5
    硬件描述 = 1.3.6.1.2.1.47.1.1.1.1.7
    硬件序列号 = 1.3.6.1.2.1.47.1.1.1.1.11
    硬件扩展名称 = 1.3.6.1.2.1.47.1.1.1.1.13
    索引为最后1位 = 硬件ID
    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type

    async def getPhysicalInfos(self):
        if self.sys_type == "hillstone":
            physical_table = await self.__getHillstonePhysicalInfo()
            return physical_table
        else:
            physical_table = await self.__getDefaultPhysicalInfo()
            return physical_table

    async def __getDefaultPhysicalInfo(self):
        '''
        硬件名称 = 1.3.6.1.2.1.47.1.1.1.1.2
        硬件类型 = 1.3.6.1.2.1.47.1.1.1.1.5
        硬件描述 = 1.3.6.1.2.1.47.1.1.1.1.7
        硬件序列号 = 1.3.6.1.2.1.47.1.1.1.1.11
        硬件扩展名称 = 1.3.6.1.2.1.47.1.1.1.1.13
        '''

        oid_nodes = {
            "sn_name": "1.3.6.1.2.1.47.1.1.1.1.2", #80
            "sn_type": "1.3.6.1.2.1.47.1.1.1.1.5", #40
            "sn_desc": "1.3.6.1.2.1.47.1.1.1.1.7", #80
            "sn_number": "1.3.6.1.2.1.47.1.1.1.1.11",#40
            "sn_ex": "1.3.6.1.2.1.47.1.1.1.1.13",  # 40
        }
        # ip,sn_id,sn_name,sn_desc,sn_number,timestamp,sn_type,sn_ex
        # header = 80 byte
        # 40字节每节点，batch = 40, 最大batch = 1400/40 = 30, 最好设置在30以下
        # 解析 oid索引=[硬件id 1位]
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sn_type"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["sn_type"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["sn_type"] = oid_infos[oid]
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["sn_type"] = oid_infos[oid]

            try:
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sn_name"],
                                       max_repetitions=2)
            except:
                oid_infos = {}
                for oid_ky in oid_cache.keys():
                    _v = await snmpget(ip=self.ip, community=self.community, oid="{}.{}".format(oid_nodes["sn_name"], oid_ky))
                    oid_infos["."+oid_ky] = _v

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["sn_name"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["sn_name"] = oid_infos[oid].decode("utf-8", "ignore")
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["sn_name"] = oid_infos[oid].decode("utf-8", "ignore")
            try:
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sn_desc"],
                                       max_repetitions=2)
            except:
                oid_infos = {}
                for oid_ky in oid_cache.keys():
                    _v = await snmpget(ip=self.ip, community=self.community, oid="{}.{}".format(oid_nodes["sn_desc"], oid_ky))
                    oid_infos["."+oid_ky] = _v

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["sn_desc"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["sn_desc"] = oid_infos[oid].decode("utf-8", "ignore")
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["sn_desc"] = oid_infos[oid].decode("utf-8", "ignore")

            try:
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sn_number"],
                                       max_repetitions=10)
            except:
                oid_infos = {}
                for oid_ky in oid_cache.keys():
                    _v = await snmpget(ip=self.ip, community=self.community, oid="{}.{}".format(oid_nodes["sn_number"], oid_ky))
                    oid_infos["."+oid_ky] = _v

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["sn_number"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["sn_number"] = oid_infos[oid].decode("utf-8", "ignore")
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["sn_number"] = oid_infos[oid].decode("utf-8", "ignore")

            try:
                oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["sn_ex"],
                                       max_repetitions=10)
            except:
                oid_infos = {}
                for oid_ky in oid_cache.keys():
                    _v = await snmpget(ip=self.ip, community=self.community, oid="{}.{}".format(oid_nodes["sn_ex"], oid_ky))
                    oid_infos["."+oid_ky] = _v

            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["sn_ex"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["sn_ex"] = oid_infos[oid].decode("utf-8", "ignore")

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                oid_cache[primary_key]["sn_id"] = primary_key
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str
            return list(oid_cache.values())

        except Exception as e:
            print("硬件信息采集异常=", self.ip, str(e))
            return None


    async def __getHillstonePhysicalInfo(self):
        '''
        硬件名称 = 1.3.6.1.4.1.28557.2.2.1.11
        硬件描述 = 1.3.6.1.4.1.28557.2.2.2.0
        硬件序列号 = 1.3.6.1.4.1.28557.2.2.1
        # ip,sn_id,sn_name,sn_desc,sn_number,timestamp,sn_type,sn_ex
        '''

        oid_nodes = {
            "sn_name": "1.3.6.1.4.1.28557.2.2.1.11.0", #80
            "sn_desc": "1.3.6.1.4.1.28557.2.2.1.2.0", #80
            "sn_number": "1.3.6.1.4.1.28557.2.2.1.1.0",#40
        }
        # header = 80 byte
        # 40字节每节点，batch = 40, 最大batch = 1400/40 = 30, 最好设置在30以下
        # 解析 oid索引=[硬件id 1位]
        try:
            dev_info = {}
            sn_name = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["sn_name"])
            dev_info["sn_name"] = sn_name.decode("utf-8", "ignore")

            sn_desc = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["sn_desc"])
            dev_info["sn_desc"] = sn_desc.decode("utf-8", "ignore")

            sn_number = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["sn_number"])
            dev_info["sn_number"] = sn_number.decode("utf-8", "ignore")

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            dev_info["ip"] = self.ip
            dev_info["sn_id"] = "1"
            dev_info["sn_type"] = "3"
            dev_info["sn_ex"] = ""
            dev_info["timestamp"] = timestamp_str
            return [dev_info]
        except Exception as e:
            print("硬件信息采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = PhysicalInfo("10.163.102.122", "Mrtg.Netease", "cisco")
        res = await a.getPhysicalInfos()
        print(len(res))
        for i in res:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

