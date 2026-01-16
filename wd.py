import subprocess
import time
import sys
import os
import psutil

# Name of the script to protect
TARGET_SCRIPT = "guardian.py"

def is_guardian_running():
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid: continue
            
            cmdline = proc.info.get('cmdline', [])
            if cmdline:
                cmd_str = " ".join(cmdline)
                if TARGET_SCRIPT in cmd_str:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def start_guardian():
    print(f"Starting {TARGET_SCRIPT}...")
    if os.name == 'nt':
        # Windows: Run without console window (pythonw)
        interpreter = sys.executable.replace("python.exe", "pythonw.exe")
        subprocess.Popen([interpreter, TARGET_SCRIPT], shell=True)
    else:
        # Linux: Run in background
        subprocess.Popen([sys.executable, TARGET_SCRIPT])

def main():
    print("Watchdog active. Protecting Guardian.")
    while True:
        if not is_guardian_running():
            start_guardian()
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        main()