# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


def _collect(mod):
    data, binaries, hidden = collect_all(mod)
    return data, binaries


cv2_data, cv2_binaries = _collect('cv2')
barcode_data, barcode_binaries = _collect('barcode')
pyzbar_data, pyzbar_binaries = _collect('pyzbar')
pil_data, pil_binaries = _collect('PIL')
numpy_data, numpy_binaries = _collect('numpy')
qt5_data, qt5_binaries = _collect('PyQt5')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=cv2_binaries + barcode_binaries + pyzbar_binaries + pil_binaries + numpy_binaries + qt5_binaries,
    datas=cv2_data + barcode_data + pyzbar_data + pil_data + numpy_data + qt5_data,
    hiddenimports=['google.auth', 'google.auth.transport.requests', 'google.oauth2', 'google.oauth2.credentials', 'google_auth_oauthlib', 'google_auth_oauthlib.flow', 'google_auth_httplib2', 'googleapiclient', 'googleapiclient.discovery', 'googleapiclient.http', 'psycopg2', 'psycopg2.extras', 'qrcode', 'barcode', 'cv2', 'pyzbar.pyzbar', 'numpy', 'PyQt5.QtPrintSupport', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.QtCore', 'escpos.printer', 'app.database.backup', 'app.database.auth', 'app.qr_code.qr_handler', 'app.gui.label_designer'],
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
    [],
    name='BioBank DB',
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
    icon=['app.ico'],
)
app = BUNDLE(
    exe,
    name='BioBank DB.app',
    icon='app.ico',
    bundle_identifier=None,
)
