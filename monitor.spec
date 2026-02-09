# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

datas = [('app.py', '.'), ('Monitor.ps1', '.'), ('start_monitor.bat', '.'), ('config.py', '.'), ('data_loader.py', '.'), ('parsers.py', '.'), ('excel_exporter.py', '.'), ('dashboards', 'dashboards'), ('site', 'site')]
datas += copy_metadata('streamlit')
datas += collect_data_files('streamlit')

hidden_imports = [
    'streamlit',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'streamlit.runtime.scriptrunner.script_runner',
    'streamlit.runtime.scriptrunner.exec_code',
    'streamlit.runtime.state',
    'streamlit.runtime.state.session_state',
    'plotly',
    'pandas'
]
hidden_imports += collect_submodules('streamlit')

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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
    name='SystemResourceMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # Keep console for debugging initially, user can change to False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
