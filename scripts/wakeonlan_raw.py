import socket

def wake_on_lan(
    mac_address: str,
    dest_ip: str,
    port: int = 9,
    use_broadcast: bool = False
) -> bool:
    """
    发送WOL魔术包
    :param mac_address: 目标MAC AA:BB:CC:DD:EE:FF
    :param dest_ip: 目标IP，单播填设备IP；广播填网段广播如10.172.21.255
    :param port: wol端口7/9
    :param use_broadcast: True=广播模式；False=单播模式（直接发给目标IP）
    :return: bool
    """
    mac_clean = mac_address.replace(":", "").replace("-", "").strip()
    if len(mac_clean) != 12:
        print(f"MAC格式错误：{mac_address}")
        return False

    mac_bytes = bytes.fromhex(mac_clean)
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            if use_broadcast:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(magic_packet, (dest_ip, port))

        mode = "广播" if use_broadcast else "单播"
        print(f"✅ {mode}魔术包发送成功 | MAC:{mac_address} 目的IP:{dest_ip}:{port}")
        return True
    except Exception as err:
        print(f"❌ 发送失败: {str(err)}")
        return False

if __name__ == "__main__":
    # ========== 单播用法：知道目标IP+MAC，直接填设备IP ==========
    target_mac = "1A:2D:84:59:15:7A"
    target_ip  = "172.16.34.20"
    wake_on_lan(target_mac, target_ip, port=9, use_broadcast=False)

    # ========== 广播用法（原来的方式） ==========
    # wake_on_lan(target_mac, "10.172.21.255", port=9, use_broadcast=True)