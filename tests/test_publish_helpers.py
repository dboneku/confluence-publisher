import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


publish = load_module("confluence_publish_script", "scripts/publish.py")


class TestPublishHelpers(unittest.TestCase):
    def test_save_regulation_config_adds_schema_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                publish.save_regulation_config({"regulation": "iso27001"})
                cfg = publish.load_regulation_config()

        self.assertEqual(cfg["schema_version"], 1)
        self.assertEqual(cfg["regulation"], "iso27001")

    def test_ingest_file_falls_back_when_doc_lint_fix_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "sample.docx"
            source.write_bytes(b"placeholder")
            dummy_fix = Path(tmpdir) / "fix.py"
            dummy_fix.write_text("# stub\n", encoding="utf-8")

            with patch.object(publish, "get_doc_lint", return_value=(None, dummy_fix)), \
                 patch.object(publish.subprocess, "run", return_value=SimpleNamespace(returncode=1, stderr="boom", stdout="")), \
                 patch.object(publish, "docx_to_adf", side_effect=lambda path: {"path": Path(path).name}):
                result = publish.ingest_file(str(source))

        self.assertEqual(result["path"], "sample.docx")

    def test_main_single_file_go_skips_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "sample.docx"
            source.write_bytes(b"placeholder")
            adf = {"version": 1, "type": "doc", "content": []}

            with patch.object(sys, "argv", [
                "publish.py",
                "--file", str(source),
                "--space", "DOCS",
                "--go",
            ]), \
                patch.object(publish, "ATLASSIAN_URL", "https://example.atlassian.net"), \
                patch.object(publish, "list_spaces", return_value=[]), \
                patch.object(publish, "ingest_file", return_value=adf), \
                patch.object(publish, "_extract_text_from_adf", return_value=""), \
                patch.object(publish, "check_template_sections", return_value=[]), \
                patch.object(publish, "validate_naming_convention", return_value=(True, "")), \
                patch.object(publish, "load_regulation_config", return_value={}), \
                patch.object(publish, "strip_title_heading_from_adf", side_effect=lambda doc, title: doc), \
                patch.object(publish, "fix_adf_heading_numbers", return_value=(adf, 0)), \
                patch.object(publish, "wrap_with_print_controls", side_effect=lambda doc, title, doc_id=None: doc), \
                patch.object(publish, "load_style_policy", return_value=(None, {})), \
                patch.object(publish, "resolve_space_id", return_value="123"), \
                patch.object(publish, "find_existing_page", return_value=None), \
                patch.object(publish, "create_page", return_value={"id": "1", "spaceId": "123", "title": "sample"}), \
                patch.object(publish, "page_url", return_value="https://example.atlassian.net/wiki/sample"), \
                patch.object(publish, "input", side_effect=AssertionError("prompt should be skipped when --go is used")):
                publish.main()


if __name__ == "__main__":
    unittest.main()
