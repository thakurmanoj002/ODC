import socket
from shared.models.responses import NetworkInfoResponse


def get_local_ip() -> str:
    """Retrieve local IP address on LAN."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect, but helps determine local outbound interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_network_info() -> NetworkInfoResponse:
    hostname = socket.gethostname()
    local_ip = get_local_ip()
    return NetworkInfoResponse(
        local_ip=local_ip,
        hostname=hostname,
        connection_info="LAN Active",
        network_state="CONNECTED",
    )
