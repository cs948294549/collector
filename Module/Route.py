from utils.snmp_tool import snmpwalk, ip2decimalism, exchange_maskint
import time

class RouteInfo(object):
    '''
    思科ios和思科nx-os设备具有差异性
    思科ios
    IPv4 使用 1.3.6.1.2.1.4.24.4.1.4+ipv4(x.x.x.x)+掩码(255.255.255.255)
    IPv6 使用 1.3.6.1.2.1.4.24.7.1.8+2.16+ipv6(16位)+前缀长度128
    思科nx-os 不支持使用1.3.6.1.2.1.4.24.4.1.4 节点
    IPv4、IPv6统一使用 1.3.6.1.2.1.4.24.7.1.8 节点
    v4 = 1.3.6.1.2.1.4.24.7.1.8+1.4+ipv6(4位)+前缀长度32
    v6 = 1.3.6.1.2.1.4.24.7.1.8+2.16+ipv6(16位)+前缀长度128

    华三设备两种都支持
    为方便统一使用与思科nx-os相同方式
    v4 = 1.3.6.1.2.1.4.24.7.1.8+1.4+ipv6(4位)+前缀长度32
    v6 = 1.3.6.1.2.1.4.24.7.1.8+2.16+ipv6(16位)+前缀长度128

    ipCidrRouteTable 该表包含CIDR路由的信息，当路由表中有路由之后填充该值
    索引是ipCidrRouteDest、ipCidrRouteMask、ipCidrRouteTos、ipCidrRouteNextHop
    基础oid=1.3.6.1.2.1.4.24.4.1
    【仅包含IPv4路由】
    inetCidrRouteTable 该表用来查询活跃的公网路由信息以及创建公网静态路由。
    索引是inetCidrRouteDestType；inetCidrRouteDest；inetCidrRoutePfxLen；inetCidrRoutePolicy；inetCidrRouteNextHopType；inetCidrRouteNextHop
    基础oid=1.3.6.1.2.1.4.24.7.1
    【包含IPv6路由，不好解读，暂时不实现】

    vrf路由分开查
    华三使用这个
    1.3.6.1.2.1.10.166.11.1.4.1.1.7


    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type

    async def getRouteTable(self):
        if "nx-os" in self.sys_type:
            route_table = await self.__getNetCidrRouteTable()
        else:
            route_table = await self.__getIpCidrRouteTable()
        return route_table

    async def __getIpCidrRouteTable(self):
        '''
        .1 = 目的地址 [primary]
        .2 = 子网掩码 [primary]
        .3 = TOS策略，默认0 [primary]
        .4 = 下一跳地址，若无下一跳则为0.0.0.0 [primary]
        .5 = 出接口索引
        .6 = 路由类型 other(1) reject(2) local(3) remote(4)
        .7 = 路由协议 other(1),local(2),netmgmt(3),icmp(4),
        egp(5),ggp(6),hello(7),rip(8),isIs(9),esIs(10),ciscoIgrp(11),
        bbnSpfIgp(12),ospf(13),bgp(14),idpr(15),ciscoEigrp(16)
        .11 = 主要的路由Metric未使用为-1
        当前功能选择 [.1][.2][.4][.5][.7][.11]
        ipCidrRouteTable 该表包含CIDR路由的信息，当路由表中有路由之后填充该值
        索引是ipCidrRouteDest、ipCidrRouteMask、ipCidrRouteTos、ipCidrRouteNextHop
        基础oid=1.3.6.1.2.1.4.24.4.1
        '''
        oid_nodes = {
            "nextindex": "1.3.6.1.2.1.4.24.4.1.5",
            "p_type": "1.3.6.1.2.1.4.24.4.1.6",
            "proto": "1.3.6.1.2.1.4.24.4.1.7",
            "metric": "1.3.6.1.2.1.4.24.4.1.11",
        }
        # header = 80 byte
        # 40字节每节点，batch = 4*40, 最大batch = 1500/160 = 12,最好设置在10以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["nextindex"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["nextindex"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["nextindex"] = oid_infos[oid]
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["nextindex"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["p_type"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["p_type"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["p_type"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["p_type"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["proto"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["proto"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["proto"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["proto"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["metric"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key = oid.replace(oid_nodes["metric"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["metric"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["metric"] = oid_infos[oid]

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                pri_keys = primary_key.split(".")
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str
                oid_cache[primary_key]["dest"] = ".".join(pri_keys[0:4])
                oid_cache[primary_key]["mask"] = ".".join(pri_keys[4:8])
                oid_cache[primary_key]["nexthop"] = ".".join(pri_keys[9:])
                gateint = ip2decimalism(oid_cache[primary_key]["dest"])
                maskint = ip2decimalism(oid_cache[primary_key]["mask"])
                start = (gateint & maskint)
                end = (gateint | (~maskint) & 0xFFFFFFFF)
                oid_cache[primary_key]["start_ip"] = start
                oid_cache[primary_key]["end_ip"] = end
                oid_cache[primary_key]["pool_len"] = end - start
            return list(oid_cache.values())
        except Exception as e:
            print("路由采集异常=", self.ip, str(e))
            return None

    async def __getNetCidrRouteTable(self):
        '''
        inetCidrRouteTable
        1.3.6.1.2.1.4.24.7.1.7  接口地址id inetCidrRouteIfIndex
        1.3.6.1.2.1.4.24.7.1.8  路由类型inetCidrRouteType INTEGER{other(1),reject(2),local(3),remote(4),blackhole(5)}
        1.3.6.1.2.1.4.24.7.1.9  协议类型 inetCidrRouteProto
        INTEGER{other(1),local(2),netmgmt(3),icmp(4),egp(5),ggp(6),
        hello(7),rip(8),isIs(9),esIs(10),
        ciscoIgrp(11),bbnSpfIgp(12),ospf(13),bgp(14),
        idpr(15),ciscoEigrp(16),dvmrp(17)}

        该表的索引是inetCidrRouteDestType、inetCidrRouteDest、inetCidrRoutePfxLen、
        inetCidrRoutePolicy、inetCidrRouteNextHopType、inetCidrRouteNextHop。
        '''
        oid_nodes = {
            "nextindex": "1.3.6.1.2.1.4.24.7.1.7.1.4",
            "p_type": "1.3.6.1.2.1.4.24.7.1.8.1.4",
            "proto": "1.3.6.1.2.1.4.24.7.1.9.1.4",
            "metric": "1.3.6.1.2.1.4.24.7.1.12.1.4",
        }
        # header = 80 byte
        # 40字节每节点，batch = 4*40, 最大batch = 1500/160 = 12,最好设置在10以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = {}
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["nextindex"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key_str = oid.replace(oid_nodes["nextindex"], "")[1:]
                keys = key_str.split(".")[0:5] + key_str.split(".")[-4:]
                key = ".".join(keys)
                if key in oid_cache.keys():
                    oid_cache[key]["nextindex"] = oid_infos[oid]
                else:
                    oid_cache[key] = {}
                    oid_cache[key]["nextindex"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["p_type"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key_str = oid.replace(oid_nodes["p_type"], "")[1:]
                keys = key_str.split(".")[0:5] + key_str.split(".")[-4:]
                key = ".".join(keys)
                if key in oid_cache.keys():
                    oid_cache[key]["p_type"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["p_type"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["proto"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key_str = oid.replace(oid_nodes["proto"], "")[1:]
                keys = key_str.split(".")[0:5] + key_str.split(".")[-4:]
                key = ".".join(keys)
                if key in oid_cache.keys():
                    oid_cache[key]["proto"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["proto"] = oid_infos[oid]

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["metric"],
                                       max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                key_str = oid.replace(oid_nodes["metric"], "")[1:]
                keys = key_str.split(".")[0:5] + key_str.split(".")[-4:]
                key = ".".join(keys)
                if key in oid_cache.keys():
                    oid_cache[key]["metric"] = oid_infos[oid]
                # else:
                #     oid_cache[key] = {}
                #     oid_cache[key]["metric"] = oid_infos[oid]

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            for primary_key in oid_cache.keys():
                pri_keys = primary_key.split(".")
                oid_cache[primary_key]["ip"] = self.ip
                oid_cache[primary_key]["timestamp"] = timestamp_str
                oid_cache[primary_key]["dest"] = ".".join(pri_keys[0:4])
                oid_cache[primary_key]["mask"] = exchange_maskint(int(pri_keys[4]))
                oid_cache[primary_key]["nexthop"] = ".".join(pri_keys[-4:])
                gateint = ip2decimalism(oid_cache[primary_key]["dest"])
                maskint = ip2decimalism(oid_cache[primary_key]["mask"])
                start = (gateint & maskint)
                end = (gateint | (~maskint) & 0xFFFFFFFF)
                oid_cache[primary_key]["start_ip"] = start
                oid_cache[primary_key]["end_ip"] = end
                oid_cache[primary_key]["pool_len"] = end - start
                if "metric" not in oid_cache[primary_key].keys():
                    oid_cache[primary_key]["metric"] = 0
            return list(oid_cache.values())
        except Exception as e:
            print("路由采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = RouteInfo("10.80.163.98", "Mrtg.Netease", "nx-os")
        res = await a.getRouteTable()
        print(len(res))
        for i in res:
            if i["dest"] == "0.0.0.0":
                print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

