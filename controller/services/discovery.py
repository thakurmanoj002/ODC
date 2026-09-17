import socket
import json
from typing import List
from shared.constants.protocol import (
    DEFAULT_DISCOVERY_PORT,
    DISCOVERY_MAGIC_REQUEST,
)
from shared.models.responses import DiscoveryResponse
from controller.utils.logging_config import logger


def discover_agents(timeout: float = 2.0, port: int = DEFAULT_DISCOVERY_PORT) -> List[DiscoveryResponse]:
    discovered: List[DiscoveryResponse] = []
    seen_ids = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        # Send broadcast request
        sock.sendto(DISCOVERY_MAGIC_REQUEST.encode("utf-8"), ("<broadcast>", port))
        logger.info(f"Broadcasted LAN discovery request on UDP port {port}")

        while True:
            try:
                data, addr = sock.recvfrom(2048)
                payload_str = data.decode("utf-8", errors="ignore")
                discovery_resp = DiscoveryResponse.model_validate_json(payload_str)
                
                # Update IP if reported loopback or empty
                if not discovery_resp.ip_address or discovery_resp.ip_address.startswith("127."):
                    discovery_resp.ip_address = addr[0]

                if discovery_resp.agent_id not in seen_ids:
                    seen_ids.add(discovery_resp.agent_id)
                    discovered.append(discovery_resp)
                    logger.info(f"Discovered Agent {discovery_resp.agent_id} at {discovery_resp.ip_address}:{discovery_resp.port}")
            except socket.timeout:
                break
            except Exception as e:
                logger.debug(f"Failed to parse discovery response: {e}")
                continue

    except Exception as e:
        logger.error(f"LAN discovery scan failed: {e}")
    finally:
        sock.close()

    return discovered
