from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from resolver import analyze
from skills._primitives import Number, Provenance, Ratifiable
from skills.config import load_config
from skills.storage import LocalStorage


class M0ScaffoldTest(unittest.TestCase):
    def test_config_loads_required_conventions(self) -> None:
        config = load_config("config/conventions.yaml")

        self.assertEqual(config.schema_version, "1.0")
        self.assertEqual(config.tax.marginal_rate, 0.25)
        self.assertIn("AAPL", config.betas)

    def test_config_rejects_missing_required_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "bad.yaml"
            config_path.write_text('schema_version: "1.0"\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required config key"):
                load_config(config_path)

    def test_primitives_enforce_derivation_and_evidence(self) -> None:
        provenance = Provenance(
            tag="computed",
            form="computed",
            period="FY2025",
            accession=None,
            source_name=None,
            retrieved_at=datetime.now(timezone.utc),
        )

        with self.assertRaisesRegex(ValueError, "derivation"):
            Number(value=1.0, unit="ratio", kind="estimate", provenance=provenance)

        with self.assertRaises(ValidationError):
            Number(value=1.0, unit="ratio", kind="fact")

        with self.assertRaises(ValidationError):
            Provenance(
                tag="bad",
                form="8-K",
                period="FY2025",
                accession=None,
                source_name="EDGAR",
                retrieved_at=datetime.now(timezone.utc),
            )

        with self.assertRaisesRegex(ValueError, "evidence"):
            Ratifiable(draft="Watch", evidence=[])

    def test_storage_writes_reads_and_initializes_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(tmp)
            storage.put_json("runs/AAPL/2026-06-29/test.json", {"ticker": "AAPL"})

            self.assertEqual(storage.get_json("runs/AAPL/2026-06-29/test.json")["ticker"], "AAPL")
            self.assertTrue((Path(tmp) / "pack.db").exists())

    def test_analyze_writes_m0_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(tmp)
            result = analyze("aapl", as_of=date(2026, 6, 29), storage=storage)

            self.assertEqual(result["status"], "m0_stub")
            self.assertEqual(result["ticker"], "AAPL")
            self.assertTrue((Path(tmp) / "runs/AAPL/2026-06-29/m0_stub.json").exists())


if __name__ == "__main__":
    unittest.main()
