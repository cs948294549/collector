# MAC_table
from utils.snmp_tool import snmpwalk, snmpget
import time

class MACTable(object):
    '''
    华三(默认)
    mac = 1.3.6.1.2.1.17.7.1.2.2.1.2
    if_id = 1.3.6.1.2.1.17.1.4.1.2

    华为
    if_id = 1.3.6.1.4.1.2011.5.25.42.2.1.3.1.4

    思科
    vlanid = 1.3.6.1.4.1.9.9.46.1.3.1.1.4
    mac = 1.3.6.1.2.1.17.4.3.1.2
    if_id = 1.3.6.1.2.1.17.1.4.1.2

    浪潮
    if_id = 1.3.6.1.4.1.48797.110.1.1.3
    mac = 1.3.6.1.4.1.48797.110.1.1.2
    vlan = 1.3.6.1.4.1.48797.110.1.1.4

    '''
    def __init__(self, ip, community="public", sys_type="default"):
        self.ip = ip
        self.community = community
        self.sys_type = sys_type

    async def getMACTables(self):
        if self.sys_type == "h3c" or self.sys_type == "default":
            mac_table = await self.__getDefaultMACtable()
            return mac_table
        elif self.sys_type == "huawei":
            mac_table = await self.__getHuaweiMACtable()
            return mac_table
        elif "inspur" in self.sys_type:
            mac_table = await self.__getInspurMACtable()
            return mac_table
        # elif "cisco" in self.sys_type:
        #     mac_table = await self.__getCiscoMACtable()
        #     return mac_table
        else:
            mac_table = await self.__getDefaultMACtable()
            return mac_table

    async def __getDefaultMACtable(self):
        '''
        逻辑接口 = 1.3.6.1.2.1.17.7.1.2.2.1.2 [primary]
        OID = VLAN_ID[1] MAC[6]  VALUE=逻辑接口ID
        逻辑接口转接口ID = 1.3.6.1.2.1.17.1.4.1.2 [primary]
        OID = 逻辑接口ID[1] VALUE=接口ID
        '''
        oid_nodes = {
            "dot_index": "1.3.6.1.2.1.17.7.1.2.2.1.2",
        }
        # header = 80 byte
        # batch = 39+16 = 55, 最大batch = 1500/60 = 25,最好设置在20以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = []
            dot_indexs = []
            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["dot_index"], max_repetitions=10)
            for oid in oid_infos.keys():
                dot_index = oid_infos[oid]
                if dot_index is None:
                    return None
                if dot_index not in dot_indexs:
                    dot_indexs.append(dot_index)
                key = oid.replace(oid_nodes["dot_index"], "")[1:]
                mac_info = {}
                mac_info["ip"] = self.ip
                mac_info["timestamp"] = timestamp_str
                oid_list = key.split(".")
                mac_info["vlan_id"] = oid_list[0]
                mac_info["mac_address"] = ":".join([hex(int(i)).replace("0x", "").zfill(2).upper() for i in oid_list[1:]])
                mac_info["dot_index"] = dot_index
                oid_cache.append(mac_info)

            dot_dict = {}
            up_link = []
            for dot in dot_indexs:
                if str(dot) != "0":
                    port_id = await snmpget(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.17.1.4.1.2.%s" % str(dot))
                    if port_id is not None:
                        dot_dict[dot] = port_id

                        port_alias = await snmpget(ip=self.ip, community=self.community,
                                                   oid="1.3.6.1.2.1.31.1.1.1.18.%s" % str(port_id))
                        if port_alias is not None:
                            port_alias = port_alias.decode("utf-8", "ignore")
                            if "uT" in port_alias or "pT:" in port_alias:
                                up_link.append(str(port_id))

                        port_name = await snmpget(ip=self.ip, community=self.community,
                                                  oid="1.3.6.1.2.1.2.2.1.2.%s" % str(port_id))
                        if port_name is not None:
                            port_name = port_name.decode("utf-8", "ignore")
                            if port_name in ["Bridge-Aggregation1", "Port-channel 1", "Port-channel1",
                                             "Port-channel10", "Port-Channel1000", "AggregatePort 1", "agg1"]:
                                up_link.append(str(port_id))
                    else:
                        dot_dict[dot] = 0
                else:
                    dot_dict[dot] = 0

            # 过滤上联
            fianl_mactable = []
            for mac in oid_cache:
                if mac["dot_index"] in dot_dict.keys():
                    mac["port_id"] = dot_dict[mac["dot_index"]]
                    if str(mac["port_id"]) in up_link:
                        continue
                    elif str(mac["port_id"]) == "0":
                        continue
                    else:
                        fianl_mactable.append(mac)

            return fianl_mactable
        except Exception as e:
            print("MAC采集异常=", self.ip, str(e))
            return None

    async def __getHuaweiMACtable(self):
        '''
        逻辑接口 = 1.3.6.1.4.1.2011.5.25.42.2.1.3.1.4 [primary]
        OID = MAC[6] VLAN_ID[1] VSI[1]  VALUE=接口ID
        '''
        oid_nodes = {
            "port_id": "1.3.6.1.4.1.2011.5.25.42.2.1.3.1.4",
        }
        # header = 80 byte
        # batch = 20 , 最大batch = 1500/ 20 = 70,最好设置在20以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = []
            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["port_id"], max_repetitions=20)
            port_ids = []
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                port_id = oid_infos[oid]
                key = oid.replace(oid_nodes["port_id"], "")[1:]
                mac_info = {}
                mac_info["ip"] = self.ip
                mac_info["timestamp"] = timestamp_str
                oid_list = key.split(".")
                mac_info["vlan_id"] = oid_list[6]
                mac_info["mac_address"] = ":".join(
                    [hex(int(i)).replace("0x", "").zfill(2).upper() for i in oid_list[0:6]])
                mac_info["port_id"] = port_id
                if port_id not in port_ids:
                    port_ids.append(port_id)
                oid_cache.append(mac_info)
            # 去除上联
            up_link = []
            for i in port_ids:
                port_alias = await snmpget(ip=self.ip, community=self.community,
                                           oid="1.3.6.1.2.1.31.1.1.1.18.%s" % str(i))
                # print("===", i, port_alias)
                if port_alias is not None:
                    port_alias = port_alias.decode("utf-8", "ignore")
                    if "uT" in port_alias or "pT:" in port_alias:
                        up_link.append(str(i))

                port_name = await snmpget(ip=self.ip, community=self.community,
                                          oid="1.3.6.1.2.1.2.2.1.2.%s" % str(i))
                if port_name is not None:
                    port_name = port_name.decode("utf-8", "ignore")
                    if port_name in ["Bridge-Aggregation1", "Port-channel 1", "Port-channel1",
                                     "Port-channel10", "Port-Channel1000", "AggregatePort 1", "agg1"]:
                        up_link.append(str(i))

            fianl_mactable = []
            for mac in oid_cache:
                if str(mac["port_id"]) in up_link:
                    continue
                elif str(mac["port_id"]) == "0":
                    continue
                else:
                    fianl_mactable.append(mac)
            return fianl_mactable
        except Exception as e:
            print("MAC采集异常=", self.ip, str(e))
            return None

    async def __getInspurMACtable(self):
        '''
        if_id = 1.3.6.1.4.1.48797.110.1.1.3
        mac = 1.3.6.1.4.1.48797.110.1.1.2
        vlan = 1.3.6.1.4.1.48797.110.1.1.4
        '''
        oid_nodes = {
            "port_id": "1.3.6.1.4.1.48797.110.1.1.3",
            "mac": "1.3.6.1.4.1.48797.110.1.1.2",
            "vlan_id": "1.3.6.1.4.1.48797.110.1.1.4"
        }
        # header = 80 byte
        # batch = 20 , 最大batch = 1500/ 20 = 70,最好设置在20以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            oid_cache = {}
            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["mac"], max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                mac_byte = oid_infos[oid]
                key = oid.replace(oid_nodes["mac"], "")[1:]
                mac_info = {}
                mac_info["ip"] = self.ip
                mac_info["timestamp"] = timestamp_str
                mac_info["mac_address"] = ":".join(
                    [hex(int(i)).replace("0x", "").zfill(2).upper() for i in mac_byte])
                oid_cache[key] = mac_info

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["vlan_id"], max_repetitions=20)
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                vlan_id = oid_infos[oid]
                key = oid.replace(oid_nodes["vlan_id"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["vlan_id"] = vlan_id

            oid_infos = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["port_id"],
                                       max_repetitions=20)

            port_ids = []
            for oid in oid_infos.keys():
                if oid_infos[oid] is None:
                    return None
                port_id = str(int(oid_infos[oid]))
                key = oid.replace(oid_nodes["port_id"], "")[1:]
                if key in oid_cache.keys():
                    oid_cache[key]["port_id"] = port_id
                    if port_id not in port_ids:
                        port_ids.append(port_id)

            # 去除上联
            up_link = []
            for i in port_ids:
                port_alias = await snmpget(ip=self.ip, community=self.community,
                                           oid="1.3.6.1.2.1.31.1.1.1.18.%s" % str(i))
                if port_alias is not None:
                    port_alias = port_alias.decode("utf-8", "ignore")
                    if "uT" in port_alias or "pT:" in port_alias:
                        up_link.append(str(i))

                port_name = await snmpget(ip=self.ip, community=self.community,
                                          oid="1.3.6.1.2.1.2.2.1.2.%s" % str(i))
                if port_name is not None:
                    port_name = port_name.decode("utf-8", "ignore")
                    if port_name in ["Bridge-Aggregation1", "Port-channel 1", "Port-channel1",
                                     "Port-channel10", "Port-Channel1000", "AggregatePort 1", "agg1"]:
                        up_link.append(str(i))

            fianl_mactable = []
            for mac in oid_cache.values():
                if str(mac["port_id"]) in up_link:
                    continue
                elif str(mac["port_id"]) == "0":
                    continue
                else:
                    fianl_mactable.append(mac)
            return fianl_mactable
        except Exception as e:
            print("MAC采集异常=", self.ip, str(e))
            return None

    async def __getCiscoMACtable(self):
        '''
        VLANID = 1.3.6.1.4.1.9.9.46.1.3.1.1.4.1 [primary]
        MAC = 1.3.6.1.2.1.17.4.3.1.2 [primary]
        逻辑接口ID = 1.3.6.1.2.1.17.1.4.1.2 [primary]
        OID = 逻辑接口ID[1] VALUE=接口ID
        '''
        oid_nodes = {
            "oid_vlans": "1.3.6.1.4.1.9.9.46.1.3.1.1.4.1",
            "oid_macs": "1.3.6.1.2.1.17.4.3.1.2",
        }
        try:
            get_vlans = await snmpwalk(ip=self.ip, community=self.community, oid=oid_nodes["oid_vlans"], max_repetitions=20)
            vlan_ids = []
            for oid in get_vlans.keys():
                if get_vlans[oid] is None:
                    return None
                key = oid.replace(oid_nodes["oid_vlans"], "")[1:]
                if key not in vlan_ids:
                    vlan_ids.append(key)

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            mac_tables = []
            for vlan_id in vlan_ids:
                try:
                    get_macs = await snmpwalk(ip=self.ip, community=self.community + "@" + str(vlan_id), oid=oid_nodes["oid_macs"], max_repetitions=20)
                except Exception as e:
                    continue
                oid_cache = []
                dot_indexs = []
                if get_macs is not None:
                    for oid in get_macs.keys():
                        if get_macs[oid] is None:
                            continue
                        dot_index = get_macs[oid]
                        key = oid.replace(oid_nodes["oid_macs"], "")[1:]
                        mac_info = {}
                        mac_info["ip"] = self.ip
                        mac_info["timestamp"] = timestamp_str
                        oid_list = key.split(".")
                        mac_info["vlan_id"] = vlan_id
                        mac_info["mac_address"] = ":".join(
                            [hex(int(i)).replace("0x", "").zfill(2).upper() for i in oid_list[0:6]])
                        mac_info["dot_index"] = dot_index
                        oid_cache.append(mac_info)
                        if dot_index not in dot_indexs:
                            dot_indexs.append(dot_index)

                dot_dict = {}
                up_link = []
                for dot in dot_indexs:
                    if str(dot) != "0":
                        port_id = await snmpget(ip=self.ip, community=self.community + "@" + str(vlan_id),
                                                oid="1.3.6.1.2.1.17.1.4.1.2.%s" % str(dot))
                        if port_id is not None:
                            dot_dict[dot] = port_id
                            port_alias = await snmpget(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.31.1.1.1.18.%s" % str(port_id))
                            if port_alias is not None:
                                port_alias = port_alias.decode("utf-8", "ignore")
                                if "uT" in port_alias or "pT:" in port_alias:
                                    up_link.append(str(port_id))

                            port_name = await snmpget(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.2.2.1.2.%s" % str(port_id))
                            if port_name is not None:
                                port_name = port_name.decode("utf-8", "ignore")
                                if port_name in ["Bridge-Aggregation1","Port-channel 1", "Port-channel1",
                                                 "Port-channel10", "Port-Channel1000", "AggregatePort 1", "agg1"]:
                                    up_link.append(str(port_id))
                        else:
                            dot_dict[dot] = 0
                    else:
                        dot_dict[dot] = 0

                fianl_mactable = []
                for mac in oid_cache:
                    if mac["dot_index"] in dot_dict.keys():
                        mac["port_id"] = dot_dict[mac["dot_index"]]
                        if str(mac["port_id"]) in up_link:
                            continue
                        elif str(mac["port_id"]) == "0":
                            continue
                        else:
                            fianl_mactable.append(mac)
                mac_tables += fianl_mactable
            return mac_tables
        except Exception as e:
            print("MAC采集异常=", self.ip, str(e))
            return None

if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = MACTable("10.163.102.122", "Mrtg.Netease", "dell")
        res = await a.getMACTables()
        print(len(res))
        for i in res:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)

