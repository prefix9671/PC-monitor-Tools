# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

manual_site_dir = Path('.artifacts/manual-site')
if not manual_site_dir.exists():
    manual_site_dir = Path('site')
lhm_bundle_dir = Path('.artifacts/vendor/lhm-bundle')

datas = [
    ('app.py', '.'),
    ('cli.py', '.'),
    ('collectors', 'collectors'),
    ('inspector_logs', 'inspector_logs'),
    ('start_monitor.bat', '.'),
    ('config.py', '.'),
    ('data_loader.py', '.'),
    ('parsers.py', '.'),
    ('excel_exporter.py', '.'),
    ('dashboards', 'dashboards'),
    (str(manual_site_dir), 'site'),
]
if lhm_bundle_dir.exists():
    datas.append((str(lhm_bundle_dir), 'lhm-bundle'))
datas += copy_metadata('streamlit')
datas += collect_data_files('streamlit')
datas += collect_data_files('pythonnet')
datas += collect_data_files('clr_loader')

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
    'pandas',
    'clr',
    'pythonnet',
    'clr_loader',
]
hidden_imports += collect_submodules(
    'streamlit',
    filter=lambda name: not name.startswith('streamlit.external.langchain'),
)
hidden_imports += collect_submodules('pythonnet')
hidden_imports += collect_submodules('clr_loader')

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
    excludes=['streamlit.external.langchain'],
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
