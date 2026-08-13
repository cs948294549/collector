import struct
from utils.snmp_tool import snmpwalk
import time


class ARPTable(object):
    '''
    普通设备采集节点：
    arp = 1.3.6.1.2.1.4.22.1.2
    索引为最后5位 = 接口ID+IP地址
    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type

    async def getARPs(self):
        arp_table = await self.__getDefaultArps()
        return arp_table

    async def __getDefaultArps(self):
        '''
        arp = 1.3.6.1.2.1.4.22.1.2
        索引为最后5位 = 接口ID+IP地址
        '''
        oid_nodes = {
            "arp_mac": "1.3.6.1.2.1.4.22.1.2",
        }
        # header = 80 byte
        # 40字节每节点，batch = 35, 最大batch = 1500/35 = 42,最好设置在20以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["arp_mac"], max_repetitions=30)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["arp_mac"], "")[1:]
                if len(oid_infos[oid]) == 6:
                    mac_addrs = ":".join([str(hex(dd))[2:].upper().zfill(2) for dd in struct.unpack("!6B", oid_infos[oid])])
                else:
                    mac_addrs = "00:00:00:00:00:00"
                if key in oid_cache.keys():
                    oid_cache[key]["arp_mac"] = mac_addrs
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["arp_mac"] = mac_addrs

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            for primary_key in oid_cache.keys():
                pri_keys = primary_key.split(".")
                oid_cache[primary_key]["port_id"] = int(pri_keys[0])
                oid_cache[primary_key]["arp_ip"] = ".".join(pri_keys[1:])
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str

            responds = []
            for i in list(oid_cache.values()):
                if i["arp_mac"] == "00:00:00:00:00:00":
                    continue
                responds.append(i)
            return responds
        except Exception as e:
            print("ARP采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = ARPTable("10.163.87.92", "Mrtg.Netease")
        res = await a.getARPs()
        print(len(res))
        for i in res:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)


