import os
import tempfile
import unittest

try:
    import pandas  # noqa: F401
    import pipeline
except ModuleNotFoundError:  # pragma: no cover - depends on local test env
    pipeline = None


@unittest.skipIf(pipeline is None, "pipeline dependencies not installed")
class TestPipelineFastPath(unittest.TestCase):
    def test_csv_pipeline_redacts_email_and_returns_fast_metadata(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
            tmp.write("timestamp,value,email\n2026-01-01,1,test@example.com\n")
            path = tmp.name

        try:
            result = pipeline.process_file_pipeline(path, "finance_leads.csv")
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
        finally:
            os.remove(path)

        self.assertIn("[EMAIL_REDACTED]", content)
        self.assertGreaterEqual(result["quality_score"], 0)
        self.assertIn("predicted_category", result)
        self.assertIn("pii_report", result)
        self.assertEqual(1, result["pii_report"]["redacted_cells"])


if __name__ == "__main__":
    unittest.main()
