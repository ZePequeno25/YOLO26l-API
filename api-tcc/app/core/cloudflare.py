import ipaddress
from fastapi import Request

CLOUDFLARE_IPV4 = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22"
]

CLOUDFLARE_IPV6 = [
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32"
]

CLOUDFLARE_NETWORKS = [ipaddress.ip_network(ip) for ip in CLOUDFLARE_IPV4 + CLOUDFLARE_IPV6]

def is_cloudflare_ip(ip: str) -> bool:
    """Verifica se o IP fornecido pertence aos intervalos da Cloudflare."""
    try:
        ip_addr = ipaddress.ip_address(ip)
        for network in CLOUDFLARE_NETWORKS:
            if ip_addr in network:
                return True
    except ValueError:
        pass
    return False

def get_real_client_ip(request: Request) -> str:
    """
    Retorna o IP real do cliente.
    Prioriza o cabeçalho CF-Connecting-IP se a requisição vier de um IP da Cloudflare,
    evitando que o sistema seja enganado por IP spoofing.
    """
    direct_ip = None
    if request.client:
        direct_ip = request.client.host

    # Se a conexao direta for de um IP da Cloudflare, confiamos no cabeçalho
    if direct_ip and is_cloudflare_ip(direct_ip):
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()

    # Fallback para X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if direct_ip:
        return direct_ip

    return "unknown"
