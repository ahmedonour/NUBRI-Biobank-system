# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['google.auth', 'google.auth.transport.requests', 'google.oauth2', 'google.oauth2.credentials', 'google_auth_oauthlib', 'google_auth_oauthlib.flow', 'google_auth_httplib2', 'googleapiclient', 'googleapiclient.discovery', 'googleapiclient.http', 'psycopg2', 'psycopg2.extras', 'qrcode', 'barcode', 'cv2', 'pyzbar.pyzbar', 'PyQt5.QtPrintSupport', 'escpos.printer', 'app.database.backup', 'app.database.auth', 'app.qr_code.qr_handler', 'app.gui.label_designer'],
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
