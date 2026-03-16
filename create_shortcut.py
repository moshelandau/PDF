"""Create a Windows desktop shortcut for PDF Editor."""

import os
import sys


def create_shortcut():
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        # Fallback: create a .bat shortcut on desktop
        create_bat_shortcut()
        return

    desktop = winshell.desktop()
    shortcut_path = os.path.join(desktop, "PDF Editor.lnk")
    app_dir = os.path.dirname(os.path.abspath(__file__))

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = sys.executable
    shortcut.Arguments = f'"{os.path.join(app_dir, "pdf_editor.py")}"'
    shortcut.WorkingDirectory = app_dir
    shortcut.Description = "PDF Editor"
    shortcut.save()
    print(f"Shortcut created: {shortcut_path}")


def create_bat_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.exists(desktop):
        # Try OneDrive desktop
        desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")

    if not os.path.exists(desktop):
        print("Could not find Desktop folder. Shortcut not created.")
        print("You can run the app with: python pdf_editor.py")
        return

    app_dir = os.path.dirname(os.path.abspath(__file__))
    bat_path = os.path.join(desktop, "PDF Editor.bat")

    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write(f'cd /d "{app_dir}"\n')
        f.write(f'pythonw pdf_editor.py\n')

    print(f"Desktop shortcut created: {bat_path}")


if __name__ == "__main__":
    create_shortcut()
