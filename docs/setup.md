# Setup & Installation Guide

## System Requirements
- Python 3.13+
- Windows 10/11 for Agent service
- macOS / Windows / Linux for Controller GUI application

## Quick Start Guide

### 1. Create Virtual Environment & Install Dependencies
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Windows Agent
On the target office PC:
```powershell
python -m agent.main
```
The Agent Setup window will appear showing:
- Agent ID (e.g. `AGENT-7F3A91`)
- Local IP & Port (8765)
- Pairing Code (e.g. `482913`)

### 3. Run Controller Application
On the controller PC:
```powershell
python -m controller.main
```
The Controller dashboard will launch. Click **+ Add Computer**, enter the Agent's IP, Port, and Pairing Code, then click **Connect & Pair**.
