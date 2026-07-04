# Hardware Monitor Setup (LibreHardwareMonitor)

The Engineering section's Ship Diagnostics panel can show detailed hardware stats including temperatures, fan speeds, voltages, and GPU info. On Windows, this requires LibreHardwareMonitor.

## Quick Setup

1. **Download LibreHardwareMonitor**
   - Go to: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases
   - Download the latest release ZIP
   - Extract it somewhere (e.g., `C:\Program Files\LibreHardwareMonitor`)

2. **Copy the DLL**
   - Find `LibreHardwareMonitorLib.dll` in the extracted folder
   - Copy it to: `claude-hub/backend/LibreHardwareMonitorLib.dll`

3. **Run as Administrator**
   - For full sensor access, run Claude Hub with admin rights
   - Right-click your terminal → "Run as administrator"
   - Then: `python run.py`

4. **Install Python dependency** (if not already done)
   ```
   pip install pythonnet
   ```

## What You Get

With LibreHardwareMonitor enabled:
- **CPU Temps** - Per-core temperatures
- **Fan Speeds** - All detected fans with RPM
- **GPU Stats** - Temperature, load, clock speeds, VRAM
- **Voltages** - CPU/GPU/motherboard voltages
- **Power Draw** - Wattage readings

Without LHM, the panel still shows:
- CPU usage (overall + per-core)
- Memory/Swap usage
- Disk usage + I/O rates
- Network transfer rates
- Battery status (laptops)
- Process count, uptime

## Troubleshooting

**"LibreHardwareMonitorLib.dll not found"**
- Make sure the DLL is in `backend/` folder
- Or in `C:\Program Files\LibreHardwareMonitor\`

**No temperature/fan data showing**
- Run as administrator
- Some laptops lock sensor access - may need manufacturer tools

**pythonnet installation fails**
- Make sure you have .NET Framework installed
- Try: `pip install pythonnet --pre`

## Files

- `backend/hardware_monitor.py` - LHM integration module
- `backend/LibreHardwareMonitorLib.dll` - (you provide this)
