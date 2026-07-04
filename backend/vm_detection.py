"""
VM DETECTION
Detects if the ship is running in a virtual machine / sandbox.
"""

import os
import subprocess
import platform
import re
from pathlib import Path
from typing import Tuple
from datetime import datetime

# Known VM indicators
VM_MAC_PREFIXES = [
    "00:05:69",  # VMware
    "00:0C:29",  # VMware
    "00:1C:14",  # VMware
    "00:50:56",  # VMware
    "08:00:27",  # VirtualBox
    "52:54:00",  # QEMU/KVM
    "00:16:3E",  # Xen
    "00:15:5D",  # Hyper-V
]

VM_PROCESS_NAMES = [
    "vmtoolsd",
    "vmwaretray",
    "vboxservice",
    "vboxtray",
    "qemu-ga",
    "spice-vdagent",
]

VM_REGISTRY_KEYS = [
    r"SOFTWARE\VMware, Inc.\VMware Tools",
    r"SOFTWARE\Oracle\VirtualBox Guest Additions",
    r"SOFTWARE\Microsoft\Virtual Machine\Guest\Parameters",
]

VM_HARDWARE_STRINGS = [
    "vmware",
    "virtualbox",
    "vbox",
    "qemu",
    "virtual",
    "xen",
    "hyper-v",
    "parallels",
]

VM_FILES = [
    "/sys/class/dmi/id/product_name",  # Linux
    "/sys/class/dmi/id/sys_vendor",    # Linux
    "/proc/scsi/scsi",                 # Linux
]


def check_mac_address() -> bool:
    """Check if any MAC address matches known VM prefixes."""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("getmac", shell=True).decode()
        else:
            output = subprocess.check_output("ip link show", shell=True).decode()

        for prefix in VM_MAC_PREFIXES:
            if prefix.lower().replace(":", "-") in output.lower():
                return True
            if prefix.lower() in output.lower():
                return True
    except:
        pass
    return False


def check_processes() -> bool:
    """Check if any VM-related processes are running."""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("tasklist", shell=True).decode().lower()
        else:
            output = subprocess.check_output("ps aux", shell=True).decode().lower()

        for proc in VM_PROCESS_NAMES:
            if proc.lower() in output:
                return True
    except:
        pass
    return False


def check_hardware_strings() -> bool:
    """Check system info for VM-related strings."""
    try:
        if platform.system() == "Windows":
            # Check BIOS info
            output = subprocess.check_output(
                "wmic bios get manufacturer,smbiosbiosversion",
                shell=True
            ).decode().lower()

            # Check system info
            output += subprocess.check_output(
                "wmic computersystem get manufacturer,model",
                shell=True
            ).decode().lower()
        else:
            # Linux - check DMI info
            output = ""
            for f in VM_FILES:
                try:
                    with open(f, 'r') as file:
                        output += file.read().lower()
                except:
                    pass

        for vm_string in VM_HARDWARE_STRINGS:
            if vm_string in output:
                return True
    except:
        pass
    return False


def check_registry() -> bool:
    """Windows only: check for VM registry keys."""
    if platform.system() != "Windows":
        return False

    try:
        import winreg
        for key_path in VM_REGISTRY_KEYS:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                winreg.CloseKey(key)
                return True
            except:
                pass
    except:
        pass
    return False


def check_hypervisor_present() -> bool:
    """Check if hypervisor bit is set in CPUID (indicates VM)."""
    try:
        if platform.system() == "Windows":
            # Check systeminfo for hypervisor
            output = subprocess.check_output("systeminfo", shell=True).decode().lower()
            if "hypervisor" in output or "virtual" in output:
                return True
        else:
            # Linux - check /proc/cpuinfo
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read().lower()
                    if "hypervisor" in cpuinfo:
                        return True
            except:
                pass
    except:
        pass
    return False


def check_suspicious_environment() -> bool:
    """Check for suspiciously clean/artificial environment."""
    suspicious_signs = 0

    # Very few files in common locations (sandbox indicator)
    try:
        home = Path.home()
        if home.exists():
            file_count = len(list(home.iterdir()))
            if file_count < 5:  # Suspiciously empty home
                suspicious_signs += 1
    except:
        pass

    # No browser history/cache (sandbox indicator)
    browser_paths = [
        Path.home() / "AppData/Local/Google/Chrome",
        Path.home() / "AppData/Local/Mozilla/Firefox",
        Path.home() / ".config/google-chrome",
        Path.home() / ".mozilla/firefox",
    ]
    has_browser = any(p.exists() for p in browser_paths)
    if not has_browser:
        suspicious_signs += 1

    # Very recent system install time (fresh VM)
    try:
        if platform.system() == "Windows":
            # Check Windows install date
            output = subprocess.check_output(
                'wmic os get installdate',
                shell=True
            ).decode()
            # Parse date and check if < 7 days old
            match = re.search(r'(\d{14})', output)
            if match:
                install_date = datetime.strptime(match.group(1)[:8], "%Y%m%d")
                if (datetime.now() - install_date).days < 7:
                    suspicious_signs += 1
    except:
        pass

    return suspicious_signs >= 2


def detect_vm() -> Tuple[bool, list]:
    """
    Run all VM detection checks.
    Returns (is_vm, detection_methods).
    """
    detections = []

    if check_mac_address():
        detections.append("mac_address")

    if check_processes():
        detections.append("vm_processes")

    if check_hardware_strings():
        detections.append("hardware_strings")

    if check_registry():
        detections.append("registry_keys")

    if check_hypervisor_present():
        detections.append("hypervisor")

    if check_suspicious_environment():
        detections.append("suspicious_environment")

    # If 2+ detection methods trigger, we're confident it's a VM
    is_vm = len(detections) >= 2

    return is_vm, detections


def run_detection_and_update_state():
    """
    Run VM detection and update trust state accordingly.
    Called on startup if DISTRIBUTION_MODE is true.
    """
    try:
        from .trust_system import load_trust_state, save_trust_state, trigger_space_madness
    except ImportError:
        from trust_system import load_trust_state, save_trust_state, trigger_space_madness

    state = load_trust_state()

    # Only run if trust system is enabled
    if not state.get("enabled"):
        return {"checked": False, "reason": "trust_system_disabled"}

    is_vm, methods = detect_vm()

    state["last_check"] = datetime.now().isoformat()
    state["vm_detected"] = is_vm
    state["detection_methods"] = methods if is_vm else []

    if is_vm and not state.get("user_acknowledged_vm"):
        # VM detected and user hasn't acknowledged - progress madness
        current_stage = state.get("space_madness_stage", 0)
        if current_stage < 5:
            trigger_space_madness(current_stage + 1)
            print(f"[VM Detection] Space madness progressed to stage {current_stage + 1}", flush=True)

    save_trust_state(state)

    return {
        "checked": True,
        "is_vm": is_vm,
        "methods": methods,
        "space_madness_stage": state.get("space_madness_stage", 0)
    }


# For testing
if __name__ == "__main__":
    is_vm, methods = detect_vm()
    print(f"VM Detected: {is_vm}")
    print(f"Detection methods: {methods}")
