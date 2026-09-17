import json
import socket
import threading
import time
from shared.constants.protocol import (
    DEFAULT_DISCOVERY_PORT,
    DISCOVERY_MAGIC_REQUEST,
)
from shared.models.responses import DiscoveryResponse
from agent.config.settings import agent_settings
from agent.system.network_info import get_local_ip
from agent.utils.logging_config import logger


class DiscoveryResponder:
    def __init__(self, port: int = DEFAULT_DISCOVERY_PORT):
        self.port = port
        self.running = False
        self.thread = None
        self.sock = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"UDP Discovery Responder started on port {self.port}")

    def _run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", self.port))
            self.sock.settimeout(2.0)
        except Exception as e:
            logger.error(f"Failed to bind UDP discovery socket on port {self.port}: {e}")
            return

        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                message = data.decode("utf-8", errors="ignore").strip()
                if message == DISCOVERY_MAGIC_REQUEST:
                    payload = DiscoveryResponse(
                        agent_id=agent_settings.agent_id,
                        computer_name=agent_settings.computer_name,
                        ip_address=get_local_ip(),
                        port=agent_settings.server_port,
                        agent_version=agent_settings.agent_version,
                        pairing_status=agent_settings.pairing_status,
                    ).model_dump_json()
                    self.sock.sendto(payload.encode("utf-8"), addr)
                    logger.info(f"Responded to discovery request from {addr[0]}:{addr[1]}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error handling discovery request: {e}")
                time.sleep(0.5)

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        logger.info("UDP Discovery Responder stopped")
