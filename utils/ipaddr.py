import socket
import struct

def ip2decimalism(ip):
    dec_value = 0
    v_list = ip.split('.')
    v_list.reverse()
    t = 1
    for v in v_list:
        dec_value += int(v) * t
        t = t * (2 ** 8)
    return dec_value


def decimalism2ip(dec_value):
    ip = ''
    t = 2 ** 8
    for _ in range(4):
        v = dec_value % t
        ip = '.' + str(v) + ip
        dec_value = dec_value // t
    ip = ip[1:]
    return ip


def length2netmask(mask_int):
    bin_arr = ['0' for i in range(32)]
    for i in range(mask_int):
        bin_arr[i] = '1'
    tmpmask = [''.join(bin_arr[i * 8:i * 8 + 8]) for i in range(4)]
    tmpmask = [str(int(tmpstr, 2)) for tmpstr in tmpmask]
    return '.'.join(tmpmask)


def netmask2length(netmask):
    return sum([bin(int(i)).count("1") for i in netmask.split(".")])


def wildcard2length(wildcard):
    """反掩码转前缀长度（Cisco ACL wildcard mask）"""
    return 32 - netmask2length(wildcard)


def getstartend(dest, mask):
    gateint = ip2decimalism(dest)
    maskint = ip2decimalism(mask)
    start = (gateint & maskint)
    end = (gateint | (~maskint) & 0xFFFFFFFF)
    return start, end


def getNet(dest, mask):
    gateint = ip2decimalism(dest)
    maskint = ip2decimalism(mask)
    start = (gateint & maskint)
    return decimalism2ip(start)



def getMaskByteByLen(mask_length):
    if not 0 <= mask_length <= 32:
        raise ValueError("Invalid mask length. Must be between 0 and 32.")
        # 计算子网掩码的二进制表示
    mask_binary = '1' * mask_length + '0' * (32 - mask_length)
    # 将二进制表示分成 4 个 8 位组
    mask_octets = [int(mask_binary[i:i + 8], 2) for i in range(0, 32, 8)]
    # 将每个 8 位组转换为十进制并使用点分十进制表示
    mask_ip = '.'.join(str(octet) for octet in mask_octets)
    return mask_ip

def getMaskByteByLenV6(mask_length):
    if not 0 <= mask_length <= 128:
        raise ValueError("Invalid mask length. Must be between 0 and 32.")
        # 计算子网掩码的二进制表示
    mask_binary = '1' * mask_length + '0' * (128 - mask_length)
    # 将二进制表示分成 4 个 8 位组
    mask_octets = [hex(int(mask_binary[i:i + 8], 2))[2:].zfill(2) for i in range(0, 128, 8)]
    # 将每个 8 位组转换为十进制并使用点分十进制表示
    mask_ipv6 = ''.join(str(octet) for octet in mask_octets)
    return socket.inet_ntop(socket.AF_INET6, bytes.fromhex(mask_ipv6))

def getIPaddressByte(ip_addr):
    '''
    使用 socket.inet_aton 函数将 IPv4 地址字符串转换为 32 位二进制格式。
    使用 socket.inet_ntoa 函数将 32 位二进制格式转换为 IPv4 地址字符串。
    :param ip_addr:
    :return:
    '''
    return socket.inet_pton(socket.AF_INET, ip_addr)

def getIPaddressStr(ip_byte):
    return socket.inet_ntop(socket.AF_INET, ip_byte)

def getIPaddressByteV6(ipv6_addr):
    return socket.inet_pton(socket.AF_INET6, ipv6_addr)

def getIPaddressStrV6(ipv6_byte):
    return socket.inet_ntop(socket.AF_INET6, ipv6_byte)

def getStartEnd(net):
    if "/" not in net:
        return None
    else:
        addr, mask = net.split("/")
        if ":" in addr:
            # v6
            v6_byte = getIPaddressByteV6(ipv6_addr=addr)
            v6_mask_byte = getIPaddressByteV6(ipv6_addr=getMaskByteByLenV6(mask_length=int(mask)))

            # 计算开始
            start = b''
            for _i in range(16):
                start += (int(v6_byte[_i]) & int(v6_mask_byte[_i])).to_bytes(1, byteorder="big")

            # 计算结束
            end = b''
            for _i in range(16):
                # broadcast_int = network_int | (0xFFFFFFFF ^ mask_int)
                end += (int(v6_byte[_i]) | (int(v6_mask_byte[_i]) ^ 0xff)).to_bytes(1, byteorder="big")

            return {"start": start.hex(), "end": end.hex()}
            pass
        else:
            # v4
            v4_byte = getIPaddressByte(ip_addr=addr)
            v4_mask_byte = getIPaddressByte(ip_addr=getMaskByteByLen(mask_length=int(mask)))

            # 计算开始
            start = b''
            for _i in range(4):
                start += (int(v4_byte[_i]) & int(v4_mask_byte[_i])).to_bytes(1, byteorder="big")

            # 计算结束
            end = b''
            for _i in range(4):
                # broadcast_int = network_int | (0xFFFFFFFF ^ mask_int)
                end += (int(v4_byte[_i]) | (int(v4_mask_byte[_i]) ^ 0xff)).to_bytes(1, byteorder="big")

            return {"start": start.hex(), "end": end.hex()}


def testV6check():
    v6_nets = ["fd01:3011::/32", "fd01:3011::/36", "fd01:3011:1000::/36",
               "fd01:3011:2000::/36", "fd01:3011:3000::/36", "fd01:3011:4000::/36",
               "fd01:3012::/32"]

    check_v6 = "fd01:3011:1000::/40"

    check_st = getStartEnd(net=check_v6)
    print("检查",check_st)

    for item in v6_nets:
        it = getStartEnd(net=item)
        print("条目==", it)

        if check_st["start"] >= it["start"] and check_st["start"] <= it["end"]:
            print("命中===", it, item)

def testV4check():
    v4_nets = ["10.17.0.0/16", "10.17.0.0/19", "10.17.32.0/20", "10.35.0.0/16", "10.35.1.0/24",
               '10.35.2.0/24', "10.35.3.0/24", "10.35.4.0/24", "10.35.1.0/22"]

    check_v4 = "10.35.2.128/25"

    check_st = getStartEnd(net=check_v4)
    print(check_st)

    for item in v4_nets:
        it = getStartEnd(net=item)
        if check_st["start"] >= it["start"] and check_st["start"] <= it["end"]:
            print("命中===", it, item, getIPaddressStr(ip_byte=bytes.fromhex(it["start"])), getIPaddressStr(ip_byte=bytes.fromhex(it["end"])))


def test_ipam_tree(data_ips):

    tree_data = sorted(data_ips, key=lambda x: (ip2decimalism(x["ip"]), int(x["mask"])))

    tree = []

    # 全局变量为tree，后续的操作对tree进行更新

    for item in tree_data:
        new_item = item
        new_item["id"] = item["ip"] + "_" + item["mask"]
        new_item["start"], new_item["end"] = getstartend(item["ip"], length2netmask(int(item["mask"])))
        new_item["children"] = []

        tree_stack = [tree]

        while len(tree_stack) > 0:
            child_array = tree_stack.pop()

            is_child = False

            # 检查当前节点是否归属于栈内的子节点
            for node in child_array:
                if node["start"] <= new_item["start"] and new_item["end"] <= node["end"]:
                    if "children" not in node:
                        node["children"] = []

                    # 是子节点，则当前节点添加到栈内
                    tree_stack.append(node["children"])
                    is_child = True
                    break

            # 不是子节点，则添加到兄弟节点
            if is_child is False:
                child_array.append(new_item)
    return tree

if __name__ == '__main__':
    import json
    # testV4check()
    # testV6check()

    # it = getStartEnd(net="2409:2000::1000:1A:0:2/96")
    #
    # print(it)
    #
    # print(getIPaddressStrV6(ipv6_byte=bytes.fromhex(it["start"])))
    # print(getIPaddressStrV6(ipv6_byte=bytes.fromhex(it["end"])))

    # ret = [
    #     {"ip": "192.168.1.0", "mask": "24"},
    #     {"ip": "192.168.4.0", "mask": "22"},
    #     {"ip": "192.168.2.0", "mask": "24"},
    #     {"ip": "192.168.3.0", "mask": "24"},
    #     {"ip": "192.168.4.0", "mask": "24"},
    #     {"ip": "192.168.5.0", "mask": "24"},
    #     {"ip": "192.168.6.0", "mask": "24"},
    #     {"ip": "192.168.0.0", "mask": "22"},
    #     {"ip": "192.168.7.0", "mask": "24"},
    #     {"ip": "192.168.0.0", "mask": "16"},
    # ]
    # tree = test_ipam_tree(ret)
    # print(json.dumps(tree, indent=4, ensure_ascii=False))
    aa = wildcard2length("0.0.3.255")
    print(aa)




