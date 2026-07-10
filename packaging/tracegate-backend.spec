from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


ROOT = Path(SPECPATH).resolve().parent

datas = collect_data_files("alembic")
for source, destination in (
    (ROOT / "tracegate" / "studio" / "migrations", "tracegate/studio/migrations"),
    (ROOT / "tracegate" / "prompts" / "templates", "tracegate/prompts/templates"),
    (ROOT / "experiments", "experiments"),
    (ROOT / "reports_claim", "reports_claim"),
    (ROOT / "results", "results"),
    (ROOT / "datasets" / "real_min", "datasets/real_min"),
):
    if source.exists():
        datas.append((str(source), destination))

hiddenimports = collect_submodules("alembic") + [
    "sqlalchemy.dialects.sqlite.pysqlite",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
]

analysis = Analysis(
    [str(ROOT / "scripts" / "tracegate_sidecar_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="tracegate-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
