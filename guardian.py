import time
import os
import sys
import psutil
import json
import ctypes
import subprocess
import winreg  # Only works on Windows

# --- CONFIGURATION ---
BLOCK_HOSTS = ["instagram.com", "www.instagram.com", "api.instagram.com", "i.instagram.com"]
REDDIT_LIMIT_SECONDS = 600  # 10 Minutes
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts" if os.name == 'nt' else "/etc/hosts"
REDIRECT_IP = "127.0.0.1"

# --- ADMIN CHECK ---
def is_admin():
    try:
        if os.name == 'nt':
            return ctypes.windll.shell32.IsUserAnAdmin()
        return os.geteuid() == 0
    except:
        return False

def elevate():
    """Relaunches the script with Administrator privileges."""
    if os.name == 'nt':
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    else:
        print("Root required. Run with: sudo python3 guardian.py")
    sys.exit()

# --- 1. INSTAGRAM BLOCKING (HOSTS FILE) ---
def block_instagram():
    try:
        with open(HOSTS_PATH, 'r+') as file:
            content = file.read()
            buffer = ""
            for site in BLOCK_HOSTS:
                if site not in content:
                    buffer += f"\n{REDIRECT_IP} {site}"
            
            if buffer:
                file.write(buffer)
                print("[ACTIVE] Instagram blocked in Hosts file.")
    except PermissionError:
        print("[ERROR] Failed to modify Hosts file. Admin rights needed.")

# --- 2. YOUTUBE SHORTS BLOCKING (POLICIES) ---
def enforce_firefox():
    """Injects STRICT policies.json into Firefox."""
    # Updated: Explicit HTTPS paths to bypass PWA caching issues
    policy_data = {
        "policies": {
            "WebsiteFilter": {
                "Block": [
                    "https://www.youtube.com/shorts/*",
                    "https://m.youtube.com/shorts/*",
                    "https://youtube.com/shorts/*",
                    "https://www.youtube.com/reel/*"
                ],
                "BlockMessage": "DOOMSCROLLING BLOCKED. Get back to work."
            }
        }
    }
    
    targets = []
    if os.name == 'nt':
        # Windows: Check Standard + Developer Edition + Local AppData
        base_paths = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA")
        ]
        for base in base_paths:
            if base:
                # Check for standard "Mozilla Firefox" folder
                f_path = os.path.join(base, "Mozilla Firefox")
                if os.path.exists(f_path): 
                    targets.append(os.path.join(f_path, "distribution"))
                
                # Check for "Firefox Developer Edition"
                dev_path = os.path.join(base, "Firefox Developer Edition")
                if os.path.exists(dev_path):
                    targets.append(os.path.join(dev_path, "distribution"))
    else:
        # Linux Paths
        targets = ["/etc/firefox/policies", "/usr/lib/firefox/distribution"]

    success = False
    for folder in targets:
        try:
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "policies.json"), "w") as f:
                json.dump(policy_data, f, indent=2)
            print(f"[ACTIVE] Firefox Policy injected: {folder}")
            success = True
        except Exception as e: 
            print(f"[LOG] Skipped Firefox path {folder}: {e}")
    
    if not success:
        print("[WARNING] Could not find Firefox installation folder.")

def enforce_chrome_edge_windows():
    """Injects Registry keys for Chrome & Edge (User + System)."""
    if os.name != 'nt': return
    
    # We write to both HKLM (System) and HKCU (User) to ensure it sticks
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    paths = [
        r"SOFTWARE\Policies\Google\Chrome\URLBlocklist",
        r"SOFTWARE\Policies\Microsoft\Edge\URLBlocklist"
    ]
    
    for hive in hives:
        for path in paths:
            try:
                key = winreg.CreateKey(hive, path)
                # "1" is the key name, value is the URL pattern
                winreg.SetValueEx(key, "1", 0, winreg.REG_SZ, "https://www.youtube.com/shorts/*")
                winreg.CloseKey(key)
                print(f"[ACTIVE] Registry Policy set: {path}")
            except Exception: pass

def enforce_chrome_linux():
    """Injects Managed Policies for Linux Browsers."""
    if os.name == 'nt': return
    paths = ["/etc/opt/chrome/policies/managed", "/etc/chromium/policies/managed"]
    data = {"URLBlocklist": ["https://www.youtube.com/shorts/*"]}
    
    for p_dir in paths:
        if os.path.exists(os.path.dirname(p_dir)):
            try:
                os.makedirs(p_dir, exist_ok=True)
                with open(os.path.join(p_dir, "block_shorts.json"), "w") as f:
                    json.dump(data, f)
                print(f"[ACTIVE] Linux Policy injected: {p_dir}")
            except PermissionError:
                print(f"[ERROR] Need Root for {p_dir}")

# --- 3. REDDIT MONITOR ---
def check_and_kill_reddit(start_time):
    reddit_active = False
    proc_to_kill = None

    # Scan processes
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info.get('cmdline', []) or [])
            # Check for reddit in browser title/cmdline
            if "reddit.com" in cmdline.lower():
                reddit_active = True
                proc_to_kill = proc
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if reddit_active:
        if start_time is None:
            start_time = time.time()
            print(f"[WATCHDOG] Reddit detected. Timer started.")
        
        elapsed = time.time() - start_time
        if elapsed > REDDIT_LIMIT_SECONDS:
            print("[ACTION] Time limit reached. Killing browser.")
            try:
                proc_to_kill.terminate()
            except: pass
            return None # Reset timer
        return start_time
    else:
        return None

# --- MAIN EXECUTION ---
def main():
    if not is_admin():
        elevate()

    print("--- GUARDIAN STARTED ---")
    
    # Apply Blocks
    block_instagram()
    enforce_firefox()
    enforce_chrome_edge_windows()
    enforce_chrome_linux()
    
    print("\n[INFO] If Youtube Shorts are not blocked, clear your Browser Cache.")
    print("[INFO] Monitoring for Reddit usage...")
    
    reddit_timer = None
    
    while True:
        reddit_timer = check_and_kill_reddit(reddit_timer)
        time.sleep(5)

if __name__ == "__main__":
    main()