import json
import os
import copy
import shlex
import sys


SETTINGS_FILE = "app_settings.json"

DEFAULT_SETTINGS = {
    "style": "modern",
    "theme": "dark",
    "grid_columns": 2,
    "autostart_enabled": False,
    "autologin_enabled": False,
    "autologin_user": "admin",
    "recording": {
        "schedule_enabled": False,
        "days": [0, 1, 2, 3, 4, 5, 6],
        "start_time": "00:00",
        "end_time": "23:59",
        "overwrite_disk": True,
        "disk_limit_gb": 50,
    },
}


def _merge_defaults(base, default):
    if not isinstance(base, dict):
        return copy.deepcopy(default)

    merged = copy.deepcopy(default)
    for key, value in default.items():
        if isinstance(value, dict):
            merged[key] = _merge_defaults(base.get(key), value)
        else:
            merged[key] = base.get(key, value)
    return merged


def load_app_settings():
    if not os.path.exists(SETTINGS_FILE) or os.path.getsize(SETTINGS_FILE) == 0:
        return _merge_defaults({}, DEFAULT_SETTINGS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
    except (json.JSONDecodeError, ValueError):
        return _merge_defaults({}, DEFAULT_SETTINGS)

    return _merge_defaults(raw, DEFAULT_SETTINGS)


def save_app_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


def is_windows():
    return sys.platform.startswith("win")


def is_linux():
    return sys.platform.startswith("linux")


def get_windows_startup_script_path():
    startup_dir = os.path.join(
        os.path.expandvars("%APPDATA%"),
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
    )
    return os.path.join(startup_dir, "ASK-Vision.vbs")


def _escape_vbs_string(value):
    return str(value).replace('"', '""')


def resolve_python_executable(project_root):
    candidates = [sys.executable]

    if is_windows():
        candidates.append(os.path.join(project_root, "venv", "Scripts", "pythonw.exe"))
        candidates.append(os.path.join(project_root, "venv", "Scripts", "python.exe"))
    else:
        candidates.append(os.path.join(project_root, "venv", "bin", "python3"))
        candidates.append(os.path.join(project_root, "venv", "bin", "python"))

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return os.path.abspath(candidate)

    return "python3" if not is_windows() else "pythonw.exe"


def sync_windows_autostart(enabled, project_root=None):
    script_path = get_windows_startup_script_path()
    os.makedirs(os.path.dirname(script_path), exist_ok=True)

    if not enabled:
        if os.path.exists(script_path):
            os.remove(script_path)
        return script_path

    project_root = os.path.abspath(project_root or os.path.dirname(__file__))
    pythonw = resolve_python_executable(project_root)
    main_py = os.path.join(project_root, "main.py")
    safe_project_root = _escape_vbs_string(project_root)
    safe_pythonw = _escape_vbs_string(pythonw)
    safe_main_py = _escape_vbs_string(main_py)
    content = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.CurrentDirectory = "{safe_project_root}"\n'
        f'WshShell.Run Chr(34) & "{safe_pythonw}" & Chr(34) & " " & Chr(34) & "{safe_main_py}" & Chr(34), 0\n'
    )

    if not os.path.exists(pythonw):
        content = (
            'Set WshShell = CreateObject("WScript.Shell")\n'
            f'WshShell.CurrentDirectory = "{safe_project_root}"\n'
            f'WshShell.Run "pythonw.exe " & Chr(34) & "{safe_main_py}" & Chr(34), 0\n'
        )

    with open(script_path, "w", encoding="utf-8") as file:
        file.write(content)

    return script_path


def get_linux_autostart_path():
    autostart_dir = os.path.join(os.path.expanduser("~"), ".config", "autostart")
    return os.path.join(autostart_dir, "ask-vision.desktop")


def sync_linux_autostart(enabled, project_root=None):
    desktop_path = get_linux_autostart_path()
    os.makedirs(os.path.dirname(desktop_path), exist_ok=True)

    if not enabled:
        if os.path.exists(desktop_path):
            os.remove(desktop_path)
        return desktop_path

    project_root = os.path.abspath(project_root or os.path.dirname(__file__))
    python_executable = resolve_python_executable(project_root)
    main_py = os.path.join(project_root, "main.py")
    launch_command = (
        f"cd {shlex.quote(project_root)} && "
        f"{shlex.quote(python_executable)} {shlex.quote(main_py)}"
    )
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Version=1.0\n"
        "Name=ASK-Vision\n"
        "Comment=ASK-Vision surveillance system\n"
        f"Path={project_root}\n"
        f"Exec=/usr/bin/env bash -lc {shlex.quote(launch_command)}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )

    with open(desktop_path, "w", encoding="utf-8") as file:
        file.write(content)

    return desktop_path


def sync_autostart(enabled, project_root=None):
    if is_windows():
        return sync_windows_autostart(enabled, project_root)
    if is_linux():
        return sync_linux_autostart(enabled, project_root)
    return None
