import importlib.util
import unittest
from pathlib import Path


def load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


adf_tools = load_module("publisher_adf_tools", "scripts/publisherlib/adf_tools.py")


class TestAdfTools(unittest.TestCase):
    def test_wrap_with_print_controls_replaces_existing_footer(self):
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {"type": "paragraph", "attrs": {"textAlign": "right"}, "content": [{"type": "text", "text": "Document classification: Internal", "marks": [{"type": "em"}]}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Body"}]},
                {"type": "rule"},
                {"type": "panel", "attrs": {"panelType": "warning"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "⚠  UNCONTROLLED WHEN PRINTED"}]}]},
            ],
        }

        wrapped = adf_tools.wrap_with_print_controls(adf, "Policy Title", doc_id="ABC-001")
        text = adf_tools.node_text({"content": wrapped["content"]})

        self.assertIn("Document classification: Internal", text)
        self.assertIn("UNCONTROLLED WHEN PRINTED", text)
        self.assertIn("ABC-001", text)
        self.assertEqual(sum(1 for node in wrapped["content"] if node.get("type") == "rule"), 1)

    def test_diff_adf_ignores_doc_control_changes(self):
        old_adf = {
            "version": 1,
            "type": "doc",
            "content": adf_tools.wrap_with_print_controls({
                "version": 1,
                "type": "doc",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Body"}]}],
            }, "Old Title")["content"],
        }
        new_adf = {
            "version": 1,
            "type": "doc",
            "content": adf_tools.wrap_with_print_controls({
                "version": 1,
                "type": "doc",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Body"}]}],
            }, "New Title")["content"],
        }

        changed, summary = adf_tools.diff_adf(old_adf, new_adf)

        self.assertFalse(changed)
        self.assertEqual(summary, [])