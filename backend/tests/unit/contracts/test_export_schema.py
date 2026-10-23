from pathlib import Path

from benchguard.contracts.export_schema import export


def test_export_schema(tmp_path: Path) -> None:
    export(tmp_path)
    assert (tmp_path / "schema.json").is_file()
    assert (tmp_path / "enums.ts").is_file()
    text = (tmp_path / "enums.ts").read_text(encoding="utf-8")
    assert "WRONG_ORDER" in text
