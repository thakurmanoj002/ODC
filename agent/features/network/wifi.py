import subprocess
import re
from typing import Optional, Dict, Any, Tuple
from shared.constants.protocol import ErrorCode
import agent.config.settings as settings_module
from agent.utils.logging_config import logger


class WindowsWifiManager:
    def __init__(self):
        pass

    def get_wireless_adapter_name(self) -> Optional[str]:
        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                match = re.search(r"^\s*Name\s*:\s*(.+)$", res.stdout, re.MULTILINE)
                if match:
                    return match.group(1).strip()

            res_if = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res_if.returncode == 0:
                for line in res_if.stdout.splitlines():
                    if "Wi-Fi" in line or "Wireless" in line or "WLAN" in line:
                        parts = line.strip().split()
                        if parts:
                            return parts[-1]
        except Exception as e:
            logger.debug(f"Error auto-detecting Wi-Fi adapter name: {e}")
        return None

    def get_wifi_status(self) -> Dict[str, Any]:
        adapter = self.get_wireless_adapter_name()
        if not adapter:
            return {
                "available": False,
                "state": "UNAVAILABLE",
                "ssid": None,
                "adapter": None,
                "error_code": ErrorCode.WIFI_ADAPTER_NOT_FOUND.value,
            }

        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = res.stdout

            state = "DISCONNECTED"
            ssid = None

            if "State" in output or "State              :" in output:
                state_match = re.search(r"^\s*State\s*:\s*(.+)$", output, re.MULTILINE)
                if state_match:
                    raw_state = state_match.group(1).strip().lower()
                    if "connected" in raw_state:
                        state = "CONNECTED"
                    elif "disconnected" in raw_state:
                        state = "DISCONNECTED"

            ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", output, re.MULTILINE)
            if ssid_match:
                ssid = ssid_match.group(1).strip()

            res_if = subprocess.run(
                ["netsh", "interface", "show", "interface", f"name={adapter}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "Disabled" in res_if.stdout or "disabled" in res_if.stdout:
                state = "DISABLED"

            return {
                "available": True,
                "state": state,
                "ssid": ssid,
                "adapter": adapter,
                "error_code": None,
            }
        except Exception as e:
            logger.error(f"Failed to query Wi-Fi status: {e}")
            return {
                "available": False,
                "state": "UNKNOWN",
                "ssid": None,
                "adapter": adapter,
                "error_code": ErrorCode.WIFI_OPERATION_FAILED.value,
            }

    def set_wifi_state(self, enable: bool) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("Wi-Fi toggle blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        status = self.get_wifi_status()
        if not status["available"]:
            return False, "Wi-Fi adapter is not available on this system.", ErrorCode.WIFI_ADAPTER_NOT_FOUND.value

        adapter = status["adapter"]
        current_state = status["state"]

        if enable and current_state in ("CONNECTED", "DISCONNECTED"):
            return True, "Wi-Fi is already enabled.", None

        if not enable and current_state == "DISABLED":
            return True, "Wi-Fi is already disabled.", None

        admin_state = "enabled" if enable else "disabled"
        cmd = ["netsh", "interface", "set", "interface", f"name={adapter}", f"admin={admin_state}"]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                action_text = "enabled" if enable else "disabled"
                logger.info(f"Wi-Fi adapter '{adapter}' set to {admin_state}")
                return True, f"Wi-Fi adapter '{adapter}' {action_text} successfully.", None
            else:
                err_msg = res.stderr or res.stdout
                if "Administrator" in err_msg or "privilege" in err_msg or "elevation" in err_msg or res.returncode != 0:
                    logger.warning("Failed to set Wi-Fi state: Administrator elevation required.")
                    return False, "Administrator permission required to change Wi-Fi state.", ErrorCode.PERMISSION_DENIED.value
                return False, f"Failed to set Wi-Fi state: {err_msg}", ErrorCode.WIFI_OPERATION_FAILED.value
        except Exception as e:
            logger.error(f"Error toggling Wi-Fi state: {e}")
            return False, f"Wi-Fi state change failed: {str(e)}", ErrorCode.WIFI_OPERATION_FAILED.value
