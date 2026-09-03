from utils.snmp_tool import snmpwalk, snmpget
import re
import time


def GetDeviceType(sysdesc):
    check_desc = sysdesc.upper()
    if "H3C" in check_desc or "HPE" in check_desc:
        return 'h3c'
    elif "HUAWEI" in check_desc or "HUARONG" in check_desc or "FUTUREMATRIX" in check_desc:
        return 'huawei'
    elif "INSPUR" in check_desc:
        return 'inspur'
    elif "CISCO" in check_desc:
        if "IOS XR" in check_desc:
            return "cisco ios-xr"
        elif "NX-OS" in check_desc:
            return "cisco nx-os"
        elif "IOS" in check_desc:
            return "cisco ios"
        else:
            return "cisco"
    elif "ARISTA" in check_desc:
        return "arista"
    elif "RUIJIE" in check_desc:
        return "ruijie"
    elif "DELL" in check_desc:
        return "dell"
    elif "JUNIPER" in check_desc:
        return "juniper"
    if "HILLSTONE" in check_desc:
        return "hillstone"
    else:
        return "default"


class DeviceInfo(object):
    '''
    设备信息主要包含设备基础信息，如设备名称、设备描述
    1.3.6.1.2.1.1.5.0 设备名称
    1.3.6.1.2.1.1.1.0 设备描述
    1.3.6.1.2.1.1.6.0 资产号
    '''
    def __init__(self, ip, community="public"):
        self.ip = ip
        self.community = community

    async def getDeviceTable(self):
        device_table = await self.__getDeviceTable_EX()
        return device_table

    async def __getDeviceTable_EX(self):
        oid_nodes = {
            "sysname": "1.3.6.1.2.1.1.5.0",
            "sysdesc": "1.3.6.1.2.1.1.1.0",
            "syscontact": "1.3.6.1.2.1.1.6.0"

        }
        # 40字节每节点，batch = 4*40, 最大batch = 1500/160 = 12,最好设置在10以下
        # 解析 oid索引=[目的地址4位][掩码4位][TOS 1位][下一跳地址 4位]
        try:
            dev_info = {}
            dev_info["ip"] = self.ip
            sysname = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["sysname"])
            dev_info["sysname"] = sysname.decode("utf-8", "ignore")

            # 处理特定设备的 sysDescr 错误 - 按 IP 匹配
            if self.ip == "10.39.224.72":
                sysdesc_str = "Cisco NX-OS(tm) Nexus9000 C9508 (8 Slot), Software (NXOS 64-bit), Version 10.2(5), RELEASE SOFTWARE Copyright (c) 2002-2022 by Cisco Systems, Inc. Compiled 4/24/2022 3:00:00"
            else:
                sysdesc = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["sysdesc"])
                sysdesc_str = sysdesc.decode("utf-8", "ignore")


            dev_info["sysdesc"] = sysdesc_str
            syscontact = await snmpget(ip=self.ip, community=self.community, oid=oid_nodes["syscontact"])
            dev_info["syscontact"] = syscontact.decode("utf-8", "ignore")

            timestamp = int(time.time())
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            dev_info["timestamp"] = timestamp_str

            dev_type = GetDeviceType(dev_info["sysdesc"])
            dev_info["sys_type"] = dev_type
            print("======", dev_info)
            try:
                if dev_type == "huawei":
                    patch_array = await snmpwalk(ip=self.ip, community=self.community,
                                                 oid="1.3.6.1.4.1.2011.5.25.19.1.8.5.1.1.4")
                    patch = list(patch_array.values())[0]
                    if patch is not None:
                        patch = patch.decode("utf-8", "ignore")
                        if patch.strip() == "None":
                            patch = ""
                    else:
                        patch = ""

                    sys_desc = dev_info["sysdesc"]

                    reg_patch = re.compile(r'Version\s+(?:\S+)\s+\(?([^)]+)\)?')
                    reg_model = re.compile(r'(?:(?:HUAWEI)|(?:Huarong)|(?:FUTUREMATRIX))\s*((?:\S+-)+\S+)', re.I)
                    desc_array = sys_desc.split("\n")
                    if "\n" in sys_desc:
                        hardware = desc_array[0].strip()
                        if "HUAWEI" in hardware.upper() or "HUARONG" in hardware.upper() or "FUTUREMATRIX" in hardware.upper():
                            hardware = ""
                    else:
                        hardware = ""

                    version_array = reg_patch.findall(sys_desc)
                    version = ""
                    if len(version_array) > 0:
                        version_str = version_array[0]
                        version = version_str.split()[1]
                        if version_str.split()[0].upper() not in hardware.upper():
                            mode_array = reg_model.findall(sys_desc)
                            if len(mode_array) > 0:
                                hardware = mode_array[0]
                            else:
                                hardware = version_str.split()[0]
                    dev_info["hardware"] = hardware
                    dev_info["version"] = version
                    dev_info["features"] = patch
                    return dev_info
                elif dev_type == "h3c":
                    sys_desc = dev_info["sysdesc"]
                    phy_type = await snmpwalk(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.47.1.1.1.1.5")
                    pids = []
                    for oid, value in phy_type.items():
                        value = str(value)
                        if value == "3":
                            pids.append(oid.split(".")[-1])
                        elif value == "9":
                            pids.append(oid.split(".")[-1])

                    hardware = ""
                    x_oid = ""

                    for oid in pids:
                        hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                     oid="1.3.6.1.2.1.47.1.1.1.1.13.{}".format(oid))
                        if hardware_str is None:
                            continue
                        hardware_str = hardware_str.decode("utf-8", "ignore")
                        if hardware_str.strip() != "":
                            hardware = hardware_str.strip()
                            x_oid = oid
                            break

                    version = await snmpget(ip=self.ip, community=self.community,
                                            oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(x_oid))
                    if version is not None:
                        version = version.decode("utf-8", "ignore").strip()
                    else:
                        version = ""
                    # 预处理，去除厂商标记
                    hardware = hardware.replace("H3C", "").replace("HPE", "").strip()
                    # 仅保留版本号di
                    re_versions = re.compile(r'.*(Release.*)')
                    re_features = re.compile(r'.*(Feature.*)')
                    if "Release" not in version:
                        if "Feature" in version:
                            version = re_features.findall(version)[0].strip().replace("Feature", "Release")
                        else:
                            version = re_versions.findall(sys_desc)[0].strip()
                    else:
                        version = re_versions.findall(version)[0].strip()

                    patch_type = await snmpwalk(ip=self.ip, community=self.community, oid="1.3.6.1.4.1.25506.2.3.1.7.2.1.5")
                    patch_pids = []
                    patch_name = ""
                    for key, value in patch_type.items():
                        if value is not None:
                            if str(value) == "4":
                                patch_pids.append(key.split(".")[-1])

                    patch_names = []
                    for pid in patch_pids:
                        patch_status = await snmpget(ip=self.ip, community=self.community, oid="1.3.6.1.4.1.25506.2.3.1.7.2.1.7.{}".format(pid))
                        if str(patch_status) == "1":
                            patch_name = await snmpget(ip=self.ip, community=self.community, oid="1.3.6.1.4.1.25506.2.3.1.7.2.1.2.{}".format(pid))
                            if patch_name is not None:
                                patch_name = patch_name.decode("utf-8", "ignore")
                                patch_name = patch_name.upper()
                                patch_names.append(patch_name)
                    if len(patch_names) > 0:
                        reg_patch = re.compile(r'-?([^-]+)\.BIN')
                        reg_data = reg_patch.findall(patch_names[-1])
                    else:
                        reg_data = []
                    if len(reg_data) > 0:
                        patch = reg_data[0]
                    else:
                        patch = ""

                    dev_info["hardware"] = hardware
                    dev_info["version"] = version
                    dev_info["features"] = patch
                    return dev_info
                elif dev_type == "dell":
                    sys_desc = dev_info["sysdesc"]
                    re_version = re.compile(r'Software\s+Version:\s+(\S+)')
                    version = re_version.findall(sys_desc)[0]
                    hardware = "Force10"
                    dev_info["hardware"] = hardware
                    dev_info["version"] = version
                    dev_info["features"] = ""
                    return dev_info
                elif dev_type == "hillstone":
                    sys_desc = dev_info["sysdesc"]
                    re_hardware = re.compile(r'Hillstone.*\s+((?:[A-Z0-9]+-)+(?:[A-Z0-9]+))')
                    hardware = re_hardware.findall(sys_desc)[0]
                    sys_version = await snmpget(ip=self.ip, community=self.community, oid="1.3.6.1.4.1.28557.2.2.1.2.0")
                    if sys_version is not None:
                        sys_version = sys_version.decode("utf-8", "ignore")
                    else:
                        sys_version = ""

                    re_version = re.compile(r'Version\s+\S+\s+(\S+)')
                    version = re_version.findall(sys_version)[0]

                    dev_info["hardware"] = hardware
                    dev_info["version"] = version
                    dev_info["features"] = ""
                    return dev_info
                elif dev_type == "cisco ios-xr":
                    sys_desc = dev_info["sysdesc"]
                    re_version = re.compile(r'Version\s+([\d\.]+)')
                    version = re_version.findall(sys_desc)[0]

                    re_hardware = re.compile(r'Cisco\s+IOS\s+XR\s+Software\s+\(([^)]+)\)')
                    hardware = re_hardware.findall(sys_desc)[0]

                    dev_info["hardware"] = hardware
                    dev_info["version"] = version
                    dev_info["features"] = ""
                    return dev_info
                elif "cisco" in dev_type:
                    phy_type = await snmpwalk(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.47.1.1.1.1.5")

                    oid_11 = []
                    oid_3 = []
                    oid_9 = []

                    for oid, value in phy_type.items():
                        if value is not None:
                            type_str = str(value)
                            if type_str == "11":
                                oid_11.append(oid.split(".")[-1])
                            elif type_str == "3":
                                oid_3.append(oid.split(".")[-1])
                            elif type_str == "9":
                                oid_9.append(oid.split(".")[-1])
                            else:
                                continue
                    hardware = ""
                    for x_oid in oid_11:
                        hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                 oid="1.3.6.1.2.1.47.1.1.1.1.13.{}".format(x_oid))
                        if hardware_str is not None:
                            hardware_str = hardware_str.decode("utf-8", "ignore")
                            if hardware_str.strip() != "" and hardware_str.strip() != "N/A":
                                hardware = hardware_str.strip()
                                break

                    if hardware == "":
                        for x_oid in oid_3:
                            hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                         oid="1.3.6.1.2.1.47.1.1.1.1.13.{}".format(x_oid))
                            if hardware_str is not None:
                                hardware_str = hardware_str.decode("utf-8", "ignore")
                                if hardware_str.strip() != "" and hardware_str.strip() != "N/A":
                                    hardware = hardware_str.strip()
                                    break

                    if hardware == "":
                        for x_oid in oid_9:
                            hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                         oid="1.3.6.1.2.1.47.1.1.1.1.13.{}".format(x_oid))
                            if hardware_str is not None:
                                hardware_str = hardware_str.decode("utf-8", "ignore")
                                if hardware_str.strip() != "" and hardware_str.strip() != "N/A":
                                    hardware = hardware_str.strip()
                                    break

                    version = ""
                    for x_oid in oid_11:
                        version_str = await snmpget(ip=self.ip, community=self.community,
                                                     oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(x_oid))
                        if version_str is not None:
                            version_str = version_str.decode("utf-8", "ignore")
                            if version_str.strip() != "" and version_str.strip() != "N/A":
                                version = version_str.strip()
                                break

                    if version == "":
                        for x_oid in oid_3:
                            version_str = await snmpget(ip=self.ip, community=self.community,
                                                         oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(x_oid))
                            if version_str is not None:
                                version_str = version_str.decode("utf-8", "ignore")
                                if version_str.strip() != "" and version_str.strip() != "N/A":
                                    version = version_str.strip()
                                    break

                    if version == "":
                        for x_oid in oid_9:
                            version_str = await snmpget(ip=self.ip, community=self.community,
                                                         oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(x_oid))
                            if version_str is not None:
                                version_str = version_str.decode("utf-8", "ignore")
                                if version_str.strip() != "" and version_str.strip() != "N/A":
                                    version = version_str.strip()
                                    break
                    # 预处理，去除厂商标记
                    hardware = hardware.replace("Chassis", "").strip()

                    dev_info["version"] = version
                    dev_info["hardware"] = hardware
                    dev_info["features"] = ""
                    return dev_info
                elif dev_type == "juniper":
                    phy_type = await snmpwalk(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.47.1.1.1.1.5")

                    pids = []
                    for oid, value in phy_type.items():
                        value = str(value)
                        if value == "3":
                            pids.append(oid.split(".")[-1])
                        elif value == "9":
                            pids.append(oid.split(".")[-1])

                    hardware = ""
                    x_oid = ""
                    # for oid in pids:
                    #     hardware_str = await snmpget(ip=self.ip, community=self.community,
                    #                                  oid="1.3.6.1.2.1.47.1.1.1.1.13.{}".format(oid))
                    #     if hardware_str is None:
                    #         continue
                    #     hardware_str = hardware_str.decode("utf-8", "ignore")
                    #     if hardware_str.strip() != "":
                    #         hardware = hardware_str.strip()
                    #         x_oid = oid
                    #         break
                    if hardware == "":
                        for oid in pids:
                            hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                         oid="1.3.6.1.2.1.47.1.1.1.1.7.{}".format(oid))
                            if hardware_str is None:
                                continue
                            hardware_str = hardware_str.decode("utf-8", "ignore")
                            if hardware_str.strip() != "":
                                hardware = hardware_str.strip()
                                x_oid = oid
                                break
                    hardware = "MX960"
                    version = await snmpget(ip=self.ip, community=self.community,
                                            oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(x_oid))
                    if version is not None:
                        version = version.decode("utf-8", "ignore").strip()
                    else:
                        version = ""
                    if version == "":
                        for oid in pids:
                            version_str = await snmpget(ip=self.ip, community=self.community,
                                                        oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(oid))
                            if version_str is None:
                                continue
                            version_str = version_str.decode("utf-8", "ignore")
                            if version_str.strip() != "":
                                version = version_str.strip()
                                break

                    # 预处理，去除厂商标记
                    hardware = hardware.replace("Chassis", "").strip()

                    dev_info["version"] = version
                    dev_info["hardware"] = hardware
                    dev_info["features"] = ""
                    return dev_info
                else:
                    phy_type = await snmpwalk(ip=self.ip, community=self.community, oid="1.3.6.1.2.1.47.1.1.1.1.5")

                    pids = []
                    for oid, value in phy_type.items():
                        value = str(value)
                        if value == "3":
                            pids.append(oid.split(".")[-1])
                        elif value == "9":
                            pids.append(oid.split(".")[-1])

                    hardware = ""
                    x_oid = ""

                    for oid in pids:
                        hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                     oid="1.3.6.1.2.1.47.1.1.1.1.13.{}".format(oid))
                        if hardware_str is None:
                            continue
                        hardware_str = hardware_str.decode("utf-8", "ignore")
                        if hardware_str.strip() != "":
                            hardware = hardware_str.strip()
                            x_oid = oid
                            break

                    if hardware == "":
                        for oid in pids:
                            hardware_str = await snmpget(ip=self.ip, community=self.community,
                                                     oid="1.3.6.1.2.1.47.1.1.1.1.7.{}".format(oid))
                            if hardware_str is None:
                                continue
                            hardware_str = hardware_str.decode("utf-8", "ignore")
                            if hardware_str.strip() != "":
                                hardware = hardware_str.strip()
                                x_oid = oid
                                break

                    version = await snmpget(ip=self.ip, community=self.community,
                                            oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(x_oid))
                    if version is not None:
                        version = version.decode("utf-8", "ignore").strip()
                    else:
                        version = ""
                    if version == "":
                        for oid in pids:
                            version_str = await snmpget(ip=self.ip, community=self.community,
                                                     oid="1.3.6.1.2.1.47.1.1.1.1.10.{}".format(oid))
                            if version_str is None:
                                continue
                            version_str = version_str.decode("utf-8", "ignore")
                            if version_str.strip() != "":
                                version = version_str.strip()
                                break

                    # 预处理，去除厂商标记
                    hardware = hardware.replace("Chassis", "").strip()

                    dev_info["version"] = version
                    dev_info["hardware"] = hardware
                    dev_info["features"] = ""
                    return dev_info
            except Exception as e:
                print("设备版本采集失败==", self.ip, str(e))
                dev_info["version"] = ""
                dev_info["hardware"] = ""
                dev_info["features"] = ""
                return dev_info
        except Exception as e:
            print("设备信息采集失败==", self.ip, str(e))
            return None



if __name__ == '__main__':
    import asyncio
    t = time.time()

    async def test():
        a = DeviceInfo("10.163.87.92", "Mrtg.Netease")
        res = await a.getDeviceTable()
        print(res)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()

    print(time.time() - t)


