import platform
import time
import psutil
from shared.models.responses import SystemInfoResponse
import agent.config.settings as settings_module


def get_system_info() -> SystemInfoResponse:
    s = settings_module.agent_settings
    vm = psutil.virtual_memory()
    total_ram_gb = round(vm.total / (1024 ** 3), 2)
    used_ram_gb = round(vm.used / (1024 ** 3), 2)
    
    try:
        disk = psutil.disk_usage('/')
        disk_pct = disk.percent
    except Exception:
        disk_pct = 0.0

    try:
        boot_time = psutil.boot_time()
        uptime_sec = round(time.time() - boot_time, 2)
    except Exception:
        uptime_sec = 0.0

    return SystemInfoResponse(
        computer_name=s.computer_name,
        os_name=platform.system(),
        os_version=f"{platform.release()} ({platform.version()})",
        cpu_usage=psutil.cpu_percent(interval=None),
        ram_usage=vm.percent,
        total_ram_gb=total_ram_gb,
        used_ram_gb=used_ram_gb,
        disk_usage=disk_pct,
        uptime_seconds=uptime_sec,
        agent_version=s.agent_version,
    )
