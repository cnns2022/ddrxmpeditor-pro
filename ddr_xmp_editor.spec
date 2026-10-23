# -*- mode: python ; coding: utf-8 -*-
#
# DDR XMP Editor Pro — PyInstaller onefile build
# V1.14: bundle MSVC x64 runtime to fix "VCRUNTIME140.dll 0xc000012f"
# on clean Windows; UPX disabled (conflicts with VC runtime DLLs).

import os

# Path of local 64-bit MSVC runtime DLLs
VC_DLL_DIR = r'C:\Users\EDY\AppData\Local\Programs\Python\Python313'
_VC_RUNTIME = ['vcruntime140.dll', 'vcruntime140_1.dll']

def _collect_vc_runtime():
    items = []
    for dll in _VC_RUNTIME:
        p = os.path.join(VC_DLL_DIR, dll)
        if os.path.exists(p):
            items.append((dll, p, 'BINARY'))
    return items


a = Analysis(
    ['ddr_xmp_editor.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['ddr5_spd_model', 'ddr5_utils', 'ddr4_spd_model'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    _collect_vc_runtime(),
    name='DDR_XMP_Editor_Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=['vcruntime*.dll', 'msvcp*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)