import aiosnmp


class TableName:
    ARP = "ARP"
    DEVICES = "DEVICES"
    GATES = "GATES"
    GATES_IPV6 = "GATES_IPV6"
    LLDPS = "LLDPS"
    MACS = "MACS"
    PHYSICAL = "PHYSICAL"
    PORTS = "PORTS"
    ROUTES = "ROUTES"


SNMP_PORT = 161
SNMP_TIMEOUT = 5
SNMP_RETRY = 3


async def snmpget(ip, oid, community):
    async with aiosnmp.Snmp(
        host=ip,
        port=SNMP_PORT,
        community=community,
        timeout=SNMP_TIMEOUT,
        retries=SNMP_RETRY,
        max_repetitions=1,
    ) as snmp:
        # get
        results = await snmp.get(oid)
        return results[0].value


async def snmpwalk(ip, oid, community, max_repetitions=10):
    async with aiosnmp.Snmp(
        host=ip,
        port=SNMP_PORT,
        community=community,
        timeout=SNMP_TIMEOUT,
        retries=SNMP_RETRY,
        max_repetitions=max_repetitions,
    ) as snmp:
        # bulk_walk
        results = await snmp.bulk_walk(oid)
        respond = {}
        for res in results:
            respond[res.oid[1:]] = res.value
        return respond

def ip2decimalism(ip):
    dec_value = 0
    v_list = ip.split('.')
    v_list.reverse()
    t = 1
    for v in v_list:
        dec_value += int(v) * t
        t = t * (2 ** 8)
    return dec_value

def exchange_maskint(mask_int):
    bin_arr = ['0' for i in range(32)]
    for i in range(mask_int):
        bin_arr[i] = '1'
    tmpmask = [''.join(bin_arr[i * 8:i * 8 + 8]) for i in range(4)]
    tmpmask = [str(int(tmpstr, 2)) for tmpstr in tmpmask]
    return '.'.join(tmpmask)

def waf(dic):
    if isinstance(dic, dict):
        for i in dic.keys():
            if type(dic[i]) == str:
                dic[i] = dic[i].replace("'", "\\'").replace('"', '\\"')
        return dic
    else:
        return dic

async def testRun():
    res = await snmpget(ip="10.162.1.4", oid="1.3.6.1.2.1.47.1.1.1.1.2.67108873", community="Mrtg.Netease")
    print(res)
    # res = await snmpwalk(ip="10.162.1.4", oid="1.3.6.1.2.1.47.1.1.1.1.5", max_repetitions=2, community="Mrtg.Netease")
    # print(res)

if __name__ == '__main__':
    import time
    import asyncio

    t = time.time()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(testRun())
    loop.close()

    print(time.time() - t)