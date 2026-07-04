"""
Hardware Monitor - LibreHardwareMonitor Integration
Provides detailed hardware stats (temps, fans, voltages) on Windows

Supports three modes:
1. LHM Web Server (localhost:8085) - no admin needed for Claude Hub
2. LHM DLL direct - requires admin
3. Basic psutil - fallback
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# Global state
_lhm_available = False
_lhm_web_available = False
_computer = None
_lhm_error = None

LHM_WEB_PORT = 8085
LHM_WEB_URL = f"http://localhost:{LHM_WEB_PORT}/data.json"


def check_lhm_web_server():
    """Check if LHM web server is running."""
    global _lhm_web_available
    try:
        response = urlopen(LHM_WEB_URL, timeout=1)
        if response.status == 200:
            _lhm_web_available = True
            print("[HardwareMonitor] LHM web server detected")
            return True
    except:
        pass
    _lhm_web_available = False
    return False


def get_stats_from_web_server():
    """Fetch sensor data from LHM's web server."""
    try:
        response = urlopen(LHM_WEB_URL, timeout=2)
        data = json.loads(response.read().decode('utf-8'))
        return parse_lhm_web_data(data)
    except Exception as e:
        print(f"[HardwareMonitor] Web server fetch failed: {e}")
        return None


def parse_lhm_web_data(data):
    """Parse LHM web server JSON into our format."""
    stats = {
        "temps": [],
        "fans": [],
        "voltages": [],
        "loads": [],
        "powers": [],
        "clocks": [],
        "gpu": None,
    }

    def process_node(node, hardware_name=""):
        name = node.get("Text", "")

        # Determine hardware name from top-level nodes
        if node.get("ImageURL", "").endswith(("cpu.png", "nvidia.png", "ati.png", "intel.png")):
            hardware_name = name

        # Check for sensor values
        value_str = node.get("Value", "")
        if value_str and value_str != "-":
            try:
                value = float(value_str.split()[0].replace(',', '.'))
            except:
                value = None

            if value is not None:
                sensor_type = node.get("SensorType", "")
                entry = {
                    "hardware": hardware_name,
                    "name": name,
                    "value": value,
                }

                if "C" in value_str or "Temperature" in sensor_type:
                    entry["unit"] = "C"
                    stats["temps"].append(entry)
                elif "RPM" in value_str or "Fan" in sensor_type:
                    entry["unit"] = "RPM"
                    stats["fans"].append(entry)
                elif "V" in value_str and "W" not in value_str:
                    entry["unit"] = "V"
                    stats["voltages"].append(entry)
                elif "W" in value_str or "Power" in sensor_type:
                    entry["unit"] = "W"
                    stats["powers"].append(entry)
                elif "MHz" in value_str or "Clock" in sensor_type:
                    entry["unit"] = "MHz"
                    stats["clocks"].append(entry)
                elif "%" in value_str or "Load" in sensor_type:
                    entry["unit"] = "%"
                    stats["loads"].append(entry)

        for child in node.get("Children", []):
            process_node(child, hardware_name)

    for child in data.get("Children", []):
        process_node(child)

    # Build GPU info
    gpu_temps = [t for t in stats["temps"] if "GPU" in t.get("hardware", "").upper()]
    gpu_loads = [l for l in stats["loads"] if "GPU" in l.get("hardware", "").upper()]
    gpu_clocks = [c for c in stats["clocks"] if "GPU" in c.get("hardware", "").upper()]
    gpu_fans = [f for f in stats["fans"] if "GPU" in f.get("hardware", "").upper()]

    if gpu_temps or gpu_loads:
        stats["gpu"] = {
            "name": gpu_temps[0]["hardware"] if gpu_temps else "GPU",
            "temps": [{"name": t["name"], "value": t["value"]} for t in gpu_temps],
            "loads": [{"name": l["name"], "value": l["value"]} for l in gpu_loads],
            "clocks": [{"name": c["name"], "value": c["value"]} for c in gpu_clocks],
            "fans": [{"name": f["name"], "value": f["value"]} for f in gpu_fans],
            "memory": None
        }

    return stats


def find_lhm_executable():
    """Find LibreHardwareMonitor executable."""
    possible_paths = [
        Path(__file__).parent / "LibreHardwareMonitor.exe",
        Path(__file__).parent.parent / "LibreHardwareMonitor.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe",
        Path.home() / "Downloads" / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe",
    ]
    for p in possible_paths:
        if p.exists():
            return p
    return None


def launch_lhm_with_web_server():
    """Launch LibreHardwareMonitor with web server enabled (triggers UAC)."""
    exe_path = find_lhm_executable()
    if not exe_path:
        return {
            "success": False,
            "error": "LibreHardwareMonitor.exe not found. Download from https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases"
        }
    try:
        ps_command = f'Start-Process -FilePath "{exe_path}" -ArgumentList "--WebServer" -Verb RunAs'
        subprocess.Popen(["powershell", "-Command", ps_command], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "message": "LibreHardwareMonitor launching. Accept the admin prompt."}
    except Exception as e:
        return {"success": False, "error": f"Failed to launch: {e}"}


def init_libre_hardware_monitor():
    """Initialize LibreHardwareMonitor. Call once at startup."""
    global _lhm_available, _computer, _lhm_error

    if check_lhm_web_server():
        return True

    if _computer is not None:
        return _lhm_available

    try:
        import clr

        dll_paths = [
            Path(__file__).parent / "LibreHardwareMonitorLib.dll",
            Path(__file__).parent.parent / "LibreHardwareMonitorLib.dll",
            Path(os.environ.get("PROGRAMFILES", "")) / "LibreHardwareMonitor" / "LibreHardwareMonitorLib.dll",
            Path(os.environ.get("LOCALAPPDATA", "")) / "LibreHardwareMonitor" / "LibreHardwareMonitorLib.dll",
        ]

        dll_path = None
        for p in dll_paths:
            if p.exists():
                dll_path = p
                break

        if not dll_path:
            _lhm_error = "LibreHardwareMonitorLib.dll not found"
            print(f"[HardwareMonitor] {_lhm_error}")
            return False

        clr.AddReference(str(dll_path))
        from LibreHardwareMonitor.Hardware import Computer, SensorType

        _computer = Computer()
        _computer.IsCpuEnabled = True
        _computer.IsGpuEnabled = True
        _computer.IsMemoryEnabled = True
        _computer.IsMotherboardEnabled = True
        _computer.IsControllerEnabled = True
        _computer.IsStorageEnabled = True
        _computer.IsNetworkEnabled = True
        _computer.Open()

        _lhm_available = True
        print("[HardwareMonitor] LibreHardwareMonitor DLL initialized successfully")
        return True

    except ImportError as e:
        _lhm_error = f"pythonnet not installed: {e}"
        print(f"[HardwareMonitor] {_lhm_error}")
        return False
    except Exception as e:
        # Extract first line only to avoid .NET stack trace spam
        error_str = str(e)
        newline_char = chr(10)
        error_msg = error_str.split(newline_char)[0] if newline_char in error_str else error_str
        _lhm_error = f"DLL unavailable: {error_msg}"
        print(f"[HardwareMonitor] {_lhm_error} (web server mode available as fallback)")
        return False


def get_hardware_stats():
    """Get detailed hardware statistics. Tries web server first, then DLL."""
    global _computer, _lhm_available, _lhm_web_available

    if _lhm_web_available or check_lhm_web_server():
        stats = get_stats_from_web_server()
        if stats:
            return stats

    if not _lhm_available or _computer is None:
        return None

    try:
        from LibreHardwareMonitor.Hardware import SensorType

        stats = {"temps": [], "fans": [], "voltages": [], "loads": [], "powers": [], "clocks": [], "gpu": None}

        for hardware in _computer.Hardware:
            hardware.Update()
            for subhardware in hardware.SubHardware:
                subhardware.Update()

            hw_name = str(hardware.Name)
            hw_type = str(hardware.HardwareType)

            for sensor in hardware.Sensors:
                if sensor.Value is None:
                    continue
                entry = {"hardware": hw_name, "name": str(sensor.Name), "value": float(sensor.Value)}
                sensor_type = sensor.SensorType

                if sensor_type == SensorType.Temperature:
                    entry["unit"] = "C"
                    stats["temps"].append(entry)
                elif sensor_type == SensorType.Fan:
                    entry["unit"] = "RPM"
                    stats["fans"].append(entry)
                elif sensor_type == SensorType.Voltage:
                    entry["unit"] = "V"
                    stats["voltages"].append(entry)
                elif sensor_type == SensorType.Power:
                    entry["unit"] = "W"
                    stats["powers"].append(entry)
                elif sensor_type == SensorType.Clock:
                    entry["unit"] = "MHz"
                    stats["clocks"].append(entry)
                elif sensor_type == SensorType.Load:
                    entry["unit"] = "%"
                    stats["loads"].append(entry)

            for subhw in hardware.SubHardware:
                sub_name = str(subhw.Name)
                for sensor in subhw.Sensors:
                    if sensor.Value is None:
                        continue
                    entry = {"hardware": f"{hw_name} - {sub_name}", "name": str(sensor.Name), "value": float(sensor.Value)}
                    sensor_type = sensor.SensorType

                    if sensor_type == SensorType.Temperature:
                        entry["unit"] = "C"
                        stats["temps"].append(entry)
                    elif sensor_type == SensorType.Fan:
                        entry["unit"] = "RPM"
                        stats["fans"].append(entry)
                    elif sensor_type == SensorType.Voltage:
                        entry["unit"] = "V"
                        stats["voltages"].append(entry)
                    elif sensor_type == SensorType.Power:
                        entry["unit"] = "W"
                        stats["powers"].append(entry)
                    elif sensor_type == SensorType.Clock:
                        entry["unit"] = "MHz"
                        stats["clocks"].append(entry)
                    elif sensor_type == SensorType.Load:
                        entry["unit"] = "%"
                        stats["loads"].append(entry)

            if "GPU" in hw_type or "Gpu" in hw_type:
                gpu_info = {"name": hw_name, "temps": [], "loads": [], "clocks": [], "fans": [], "memory": None}
                for sensor in hardware.Sensors:
                    if sensor.Value is None:
                        continue
                    stype = sensor.SensorType
                    sname = str(sensor.Name)
                    sval = float(sensor.Value)

                    if stype == SensorType.Temperature:
                        gpu_info["temps"].append({"name": sname, "value": sval})
                    elif stype == SensorType.Load:
                        gpu_info["loads"].append({"name": sname, "value": sval})
                    elif stype == SensorType.Clock:
                        gpu_info["clocks"].append({"name": sname, "value": sval})
                    elif stype == SensorType.Fan:
                        gpu_info["fans"].append({"name": sname, "value": sval})
                    elif stype == SensorType.SmallData and "Memory" in sname:
                        gpu_info["memory"] = {"name": sname, "value": sval}
                stats["gpu"] = gpu_info

        return stats

    except Exception as e:
        print(f"[HardwareMonitor] Error reading sensors: {e}")
        return None


def get_lhm_status():
    """Get the status of LibreHardwareMonitor integration."""
    global _lhm_web_available
    check_lhm_web_server()
    return {
        "available": _lhm_available or _lhm_web_available,
        "web_server": _lhm_web_available,
        "dll_loaded": _lhm_available,
        "error": _lhm_error,
        "exe_found": find_lhm_executable() is not None
    }


def cleanup():
    """Clean up LHM resources."""
    global _computer
    if _computer is not None:
        try:
            _computer.Close()
        except:
            pass
        _computer = None
