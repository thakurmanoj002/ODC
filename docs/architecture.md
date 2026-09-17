# Architectural Specification - Phase 1 Architecture Hardening

## Overview
LAN Office Control Center uses a modular client-server architecture designed for local network computer administration and telemetry.

```
+-----------------------------------------------------------------+
|                         Controller                              |
| (Cross-Platform: macOS, Windows, Linux)                         |
|                                                                 |
|  +------------------------+      +---------------------------+  |
|  | PySide6 Desktop GUI    |      | SQLite Database           |  |
|  | (Modular Panels UI)    |      | (computers, capabilities) |  |
|  +-----------+------------+      +-------------+-------------+  |
|              |                                 ^                |
|              v                                 |                |
|  +---------------------------------------------+-------------+  |
|  | AgentClient Service (httpx) & UDP Broadcast Scanner       |  |
|  +----------------------------+------------------------------+  |
+-------------------------------|---------------------------------+
                                |
                         Authenticated LAN
                       HTTP / JSON API (v1)
                                |
+-------------------------------v---------------------------------+
|                       Windows Agent                             |
| (Windows Target PC)                                             |
|                                                                 |
|  +-----------------------------------------------------------+  |
|  | Agent Core: FastAPI Server (/api/v1/...)                  |  |
|  | Auth Middleware, Pairing Manager, Action Registry          |  |
|  +----------------------------+------------------------------+  |
|                               |                                 |
|                               v                                 |
|  +-----------------------------------------------------------+  |
|  | Modular Features Layer (BaseFeature interfaces)           |  |
|  | - agent/features/system       (SystemFeature, psutil)     |  |
|  | - agent/features/network      (NetworkFeature, socket)   |  |
|  | - agent/features/power        (PowerFeature, ctypes)      |  |
|  | - agent/features/applications (ApplicationFeature)        |  |
|  | - agent/features/files        (FilesFeature, PathSandbox) |  |
|  +-----------------------------------------------------------+  |
+-----------------------------------------------------------------+
```

---

## 🛠️ How to Add a New Feature (Developer Guide)

Follow these 7 steps to add a new feature (e.g. `PowerFeature` for restart/shutdown) without rewriting core infrastructure:

### Step 1: Define Interface in `agent/features/base.py`
Define abstract base classes for platform operations:
```python
class BasePowerManager(ABC):
    @abstractmethod
    def lock((self): pass

    @abstractmethod
    def restart(self): pass
```

### Step 2: Implement Provider in `agent/features/<feature>/provider.py`
Create feature directory `agent/features/power/provider.py`:
```python
from agent.features.base import BaseFeature, BasePowerManager

class WindowsPowerManager(BasePowerManager):
    def lock(self):
        # ctypes.windll.user32.LockWorkStation()
        pass

class PowerFeature(BaseFeature):
    @property
    def name(self) -> str:
        return "power"

    def register_actions(self, registry) -> None:
        registry.register(
            action_id="LOCK_PC",
            feature=self.name,
            description="Lock workstation",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_lock,
        )
```

### Step 3: Register Feature in `agent/core/capabilities.py`
Add feature initialization to `CapabilityManager`:
```python
power_feat = PowerFeature()
power_feat.register_actions(action_registry)
self.features.append(power_feat)
```

### Step 4: Add Action Identifier to Protocol Constants
Add action string to `AllowedAction` enum in `shared/constants/protocol.py`.

### Step 5: Create Controller UI Panel
Create modular PySide6 widget in `controller/ui/panels/power_panel.py`:
```python
class PowerControlPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Power Controls", parent)
```

### Step 6: Embed Panel in `ComputerDetailsView`
Import `PowerControlPanel` into `controller/ui/computer_details.py` and conditionally show it based on Agent capabilities.

### Step 7: Add Unit & Integration Tests
Add feature-specific test cases under `tests/agent/` and `tests/integration/`.
