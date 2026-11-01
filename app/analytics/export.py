"""Xuất kết quả lớn ra file để người dùng tải về thay vì đưa hết vào context model."""

import uuid
from pathlib import Path

import pandas as pd

from app.core.tracing import traced


@traced("analytics")
def export_csv_7z(df: pd.DataFrame, export_dir: Path, prefix: str = "export") -> str:
    """Ghi DataFrame ra CSV (UTF-8 BOM để Excel đọc đúng tiếng Việt), nén .7z, trả đường dẫn file .7z."""
    import py7zr

    export_dir.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{len(df)}_{uuid.uuid4().hex[:8]}"
    csv_path = export_dir / f"{name}.csv"
    archive_path = export_dir / f"{name}.7z"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.write(csv_path, arcname=csv_path.name)
    csv_path.unlink()

    return str(archive_path)
