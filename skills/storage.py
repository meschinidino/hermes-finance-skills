from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class LocalStorage:
    def __init__(self, root: Path | str = Path("data")) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "cache").mkdir(exist_ok=True)
        (self.root / "runs").mkdir(exist_ok=True)
        self.db_path = self.root / "pack.db"
        self._init_db()

    def put_json(self, path: str, payload: dict[str, Any]) -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def get_json(self, path: str) -> dict[str, Any]:
        return json.loads(self._resolve(path).read_text(encoding="utf-8"))

    def append_log(self, table: str, payload: dict[str, Any]) -> None:
        if table != "calibration_log":
            raise ValueError("M0 only supports calibration_log")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "insert into calibration_log(payload_json) values (?)",
                (json.dumps(payload, sort_keys=True),),
            )
            conn.commit()

    def _resolve(self, path: str) -> Path:
        normalized = Path(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError("storage paths must be relative to the storage root")
        return self.root / normalized

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                create table if not exists calibration_log (
                    id integer primary key autoincrement,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            conn.commit()
