import sys
import os
from cx_Freeze import setup, Executable

# Dependencies
build_exe_options = {
    "packages": ["os", "sys", "ctypes", "customtkinter", "requests", "flask", "flask_cors", "plyer", "pystray", "PIL", "threading", "json", "urllib", "shutil"],
    "include_files": [
        ("ui", "ui"),
        ("core", "core"),
        ("app.ico", "app.ico")
    ],
    "excludes": ["tkinter.test", "unittest"]
}

# MSI Options
bdist_msi_options = {
    "add_to_path": True,
    "initial_target_dir": r"[ProgramFilesFolder]\TafimDownloaderPro",
    "install_icon": "app.ico",
    "upgrade_code": "{92348574-3948-4395-9348-283472394857}", # Random GUID
}

base = None
if sys.platform == "win32":
    base = "gui"

setup(
    name="Tafim Downloader Pro",
    version="1.0.0",
    description="High-Speed Premium Downloader",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options
    },
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name="TafimDownloaderPro.exe",
            icon="app.ico",
            shortcut_name="Tafim Downloader Pro",
            shortcut_dir="DesktopFolder",
        ),
        Executable(
            "main.py",
            base=base,
            target_name="TafimDownloaderPro.exe",
            icon="app.ico",
            shortcut_name="Tafim Downloader Pro",
            shortcut_dir="ProgramMenuFolder",
        )
    ]
)
