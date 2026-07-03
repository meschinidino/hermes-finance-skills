from __future__ import annotations

import json
import subprocess
import sys
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
        self.assertEqual(config.beta_for_ticker("AAPL").unlevered, 1.31)

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

    def test_analyze_writes_m1_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(tmp)
            result = analyze("aapl", as_of=date(2026, 6, 29), storage=storage)
            run_dir = Path(tmp) / "runs/AAPL/2026-06-29"
            m1_handoff = storage.get_json("runs/AAPL/2026-06-29/handoff.json")

            self.assertEqual(m1_handoff["status"], "m1_walking_skeleton")
            self.assertEqual(result["ticker"], "AAPL")
            self.assertEqual(result["header"]["produced_by"], "D-3")
            self.assertTrue((run_dir / "spine.json").exists())
            self.assertTrue((run_dir / "handoff.json").exists())
            self.assertTrue((run_dir / "valuation_range.json").exists())
            self.assertTrue((run_dir / "expectations_line.json").exists())
            self.assertTrue((run_dir / "conviction.json").exists())
            self.assertTrue((run_dir / "final_handoff.json").exists())
            self.assertIsNotNone(result["valuation_range"])
            self.assertIsNotNone(result["whats_priced_in"])

    def test_analyze_price_feed_down_still_files_m2a_artifacts(self) -> None:
        class BadFeed:
            def quote(self, ticker: str) -> dict[str, object]:
                raise RuntimeError("offline")

        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(tmp)
            run_dir = Path(tmp) / "runs/AAPL/2026-06-29"

            with self.assertRaisesRegex(ValueError, "conviction requires filed price"):
                analyze("aapl", as_of=date(2026, 6, 29), storage=storage, price_feed=BadFeed())

            self.assertTrue((run_dir / "valuation_range.json").exists())
            self.assertTrue((run_dir / "expectations_line.json").exists())
            valuation_range = storage.get_json("runs/AAPL/2026-06-29/valuation_range.json")
            expectations_line = storage.get_json("runs/AAPL/2026-06-29/expectations_line.json")
            self.assertIn("book_equity_weighting_fallback", valuation_range["flags"])
            self.assertIn("reverse_dcf_blocked_no_observed_price", expectations_line["flags"])
            self.assertTrue(expectations_line["reverse_band_results"]["low"]["blocked"])

    def test_unknown_ticker_cli_rejects_without_traceback_or_run_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "resolver", "SONY"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertFalse((repo_root / "data/runs/SONY").exists())
        self.assertEqual(
            json.loads(result.stdout),
            {
                "status": "rejected",
                "error": {
                    "code": "unknown_ticker",
                    "requested_ticker": "SONY",
                    "enabled_tickers": ["AAPL", "MRNA"],
                    "message": "ticker not enabled in this deployment",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
