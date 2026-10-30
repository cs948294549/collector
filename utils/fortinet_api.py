# 飞塔 FortiGate REST monitor 接口（/api/v2/monitor/*）
#
# 用途：补 SNMP MIB 拿不到的数据。飞塔 MIB 只暴露 fgWc 表里的静态配置和少量运行态，
#       信道利用率、LLDP 邻居、终端真实 VLAN 这些只有 REST 接口有。
# 约定：任何失败（未配 token / 连不上 / 超时 / 非 200 / 非 JSON / status 非 success）
#       一律返回 None，调用方拿到 None 就保持 SNMP 采集结果不变，飞塔独有字段留 None。
import asyncio
import logging

import aiohttp

try:
    from config.config import fortinet_config
except ImportError:
    # 老部署的 config.py 里还没有这一节，缺配置不能影响整个采集
    fortinet_config = {}

logger = logging.getLogger(__name__)

DEFAULT_PORT = 443
DEFAULT_VDOM = "root"
DEFAULT_TIMEOUT = 15
API_PREFIX = "/api/v2/monitor/"

# 同一台设备只在第一次缺 token 时告警，避免每轮每模块刷屏
_no_token_warned = set()


def _cfg(key, default=None):
    return (fortinet_config or {}).get(key, default)


def get_token(ip):
    '''按 AC 管理 IP 取 token，取不到再看全局 token'''
    tokens = _cfg("tokens", {}) or {}
    return tokens.get(ip) or _cfg("token", "") or ""


def mask(token):
    '''日志里不出现明文 token'''
    if not token or len(token) <= 8:
        return "***"
    return token[:4] + "***" + token[-4:]


async def fetch_monitor(ip, path, vdom=None, params=None, timeout=None):
    '''
    调 /api/v2/monitor/<path>，返回 results；失败返回 None

    Args:
        ip: FortiGate 管理 IP（wifi_ac.mgmt_ip）
        path: monitor 路径，如 wifi/managed_ap / wifi/client
        vdom: 默认取配置里的 vdom
        params: 额外 query 参数
        timeout: 默认取配置里的 timeout
    '''
    if not _cfg("enabled", False):
        return None

    token = get_token(ip)
    if not token:
        if ip not in _no_token_warned:
            _no_token_warned.add(ip)
            logger.warning(f"Fortinet API 未配置 token，跳过 REST 补采: {ip}")
        return None

    port = int(_cfg("port", DEFAULT_PORT))
    vdom = vdom or _cfg("vdom", DEFAULT_VDOM)
    timeout = timeout or _cfg("timeout", DEFAULT_TIMEOUT)
    # 设备是自签证书，默认不校验；需要严格校验时在 config 里把 verify_ssl 置 True
    verify_ssl = _cfg("verify_ssl", False)
    url = "https://%s:%s%s%s" % (ip, port, API_PREFIX, str(path).lstrip("/"))

    # FortiOS 7.4 起不再接受 URL 上的 access_token，只能用 Bearer 头
    headers = {"Authorization": "Bearer %s" % token}
    query = {"vdom": vdom}
    query.update(params or {})

    try:
        connector = aiohttp.TCPConnector(ssl=None if verify_ssl else False)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as session:
            async with session.get(url, params=query, headers=headers) as resp:
                if resp.status == 401:
                    logger.warning(f"Fortinet API {ip} token 无效或已过期（{mask(token)}），降级回 SNMP")
                    return None
                if resp.status != 200:
                    body = (await resp.text() or "")[:120].replace("\n", " ")
                    logger.warning(f"Fortinet API {ip} {path} 返回 HTTP {resp.status}: {body}")
                    return None
                data = await resp.json(content_type=None)
    except asyncio.TimeoutError:
        logger.warning(f"Fortinet API {ip} {path} 超时 {timeout}s，降级回 SNMP")
        return None
    except aiohttp.ClientError as e:
        logger.warning(f"Fortinet API {ip} {path} 连接失败: {e}，降级回 SNMP")
        return None
    except (ValueError, OSError) as e:
        logger.warning(f"Fortinet API {ip} {path} 响应解析失败: {e}，降级回 SNMP")
        return None

    if not isinstance(data, dict):
        logger.warning(f"Fortinet API {ip} {path} 响应不是对象，降级回 SNMP")
        return None
    if data.get("status") != "success":
        logger.warning(f"Fortinet API {ip} {path} status={data.get('status')}，降级回 SNMP")
        return None

    return data.get("results")
