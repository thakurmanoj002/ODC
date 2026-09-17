# Security Model & Policy

## Core Principles
1. **No Arbitrary Shell Execution**: The application explicitly lacks any generic command execution endpoints (`/shell`, `/cmd`, `/powershell`, `/execute`).
2. **Transparent Operation**: The Agent displays a setup window with its Agent ID, local IP, port, and pairing status. It does not run covertly.
3. **Mandatory Pairing & Authentication**: Unauthenticated callers are rejected with HTTP 401. Access to system information requires a secret token granted during pairing.
4. **Local Network Scoped**: The service is designed for execution within trusted private LAN environments.
