import os
import sys
import subprocess
import winreg
import uvicorn

try:
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
    sys_path, _ = winreg.QueryValueEx(key, "Path")
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
    user_path, _ = winreg.QueryValueEx(key, "Path")
    os.environ["Path"] = sys_path + ";" + user_path
except Exception:
    pass

if __name__ == "__main__":
    sys.argv = ["uvicorn", "main:app", "--port", "8000"]
    uvicorn.main()
