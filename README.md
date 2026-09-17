# LAN Office Control Center

A secure, local-network remote administration and monitoring tool for Windows PCs.

## Components
- **Controller**: PySide6 desktop GUI running on macOS, Windows, or Linux. Monitors paired computers, displays live system metrics, and tracks activity logs.
- **Agent**: Windows background service built with FastAPI & Uvicorn. Exposes safe, allowlisted API endpoints authenticated via secret tokens and 6-digit pairing codes.

## Features
- **Phase 1 Foundation**: Modern PySide6 desktop dashboard, UDP broadcast discovery, 6-digit pairing code verification, real-time CPU/RAM/Disk metrics.
- **Phase 2 Remote Controls & Network**: Power controls (Lock Workstation, Restart, Shutdown), Wi-Fi status & toggle (On/Off), network interface inspection.
- **Phase 3 Allowed Applications Control**: List running processes, launch allowlisted software (`notepad`, `calc`, `cmd`, `powershell`, `chrome`, etc.), stop allowlisted processes safely. Protected system processes (`explorer.exe`, `lsass.exe`, `svchost.exe`, etc.) are guarded against accidental termination.
- **Phase 4 File & Folder Management**: Logical root sandbox (`shared`, `documents`), path traversal (`..`) blocking, protected OS directory protection (`C:\Windows`, `C:\Program Files`), directory browsing, folder creation, renaming, deletion with confirmation dialog, streaming chunked file transfers with staging `.tmp` cleanup.

## Running the Application

### 1. Start Agent (Windows PC)
```powershell
.venv\Scripts\python -m agent.main
```

### 2. Start Controller (Main PC)
```powershell
.venv\Scripts\python -m controller.main
```

### 3. Run Tests
```powershell
# Unit & Integration Tests (18 tests)
.venv\Scripts\python -m pytest tests/ -v

# Phase 4 Acceptance Suite (28 / 28 criteria)
.venv\Scripts\python -m tests.test_phase4_acceptance
```
