#!/usr/bin/env python3
"""
Build script for creating Mac executable
Run this on a Mac: python3 build_mac.py
"""

import subprocess
import sys
import os
from pathlib import Path

def build_mac_app():
    """Build the Mac application using PyInstaller"""
    
    # Check if we're on macOS
    if sys.platform != 'darwin':
        print("❌ This script must be run on macOS")
        return False
    
    print("🍎 Building Mac application...")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Install PyInstaller if not already installed
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Create Mac-specific spec file
    mac_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LCReportDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""
    
    # Write Mac spec file
    with open("LCReportDownloader_mac.spec", "w") as f:
        f.write(mac_spec)
    
    # Build the app
    print("🔨 Building executable...")
    subprocess.run([sys.executable, "-m", "PyInstaller", "LCReportDownloader_mac.spec"], check=True)
    
    print("✅ Mac app built successfully!")
    print("📁 Find your app in: dist/LCReportDownloader.app")
    
    return True

if __name__ == "__main__":
    build_mac_app()
