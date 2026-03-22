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


policy = load_module("publisher_policy", "scripts/publisherlib/policy.py")


class TestPolicyHelpers(unittest.TestCase):
    def test_fix_adf_heading_numbers_strips_number_from_existing_heading(self):
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": "1. Purpose"}],
                }
            ],
        }

        fixed, changes = policy.fix_adf_heading_numbers(adf)

        self.assertEqual(changes, 1)
        self.assertEqual(fixed["content"][0]["type"], "heading")
        self.assertEqual(fixed["content"][0]["attrs"]["level"], 1)
        self.assertEqual(fixed["content"][0]["content"][0]["text"], "Purpose")

    def test_fix_adf_heading_numbers_converts_short_numbered_paragraphs_to_headings(self):
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "1. Scope"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Body text that stays a paragraph."}],
                },
            ],
        }

        fixed, changes = policy.fix_adf_heading_numbers(adf)

        self.assertEqual(changes, 1)
        self.assertEqual(fixed["content"][0]["type"], "heading")
        self.assertEqual(fixed["content"][0]["attrs"]["level"], 1)
        self.assertEqual(fixed["content"][0]["content"][0]["text"], "Scope")
        self.assertEqual(fixed["content"][1]["type"], "paragraph")

    def test_fix_adf_heading_numbers_uses_adjacent_one_then_two_heuristic(self):
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "1. Purpose"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "2. Definitions"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "3. Requirements"}]},
            ],
        }

        fixed, changes = policy.fix_adf_heading_numbers(adf)

        self.assertEqual(changes, 3)
        self.assertEqual(fixed["content"][0]["attrs"]["level"], 1)
        self.assertEqual(fixed["content"][1]["attrs"]["level"], 2)
        self.assertEqual(fixed["content"][2]["attrs"]["level"], 2)
        self.assertEqual(fixed["content"][2]["content"][0]["text"], "Requirements")

    def test_fix_adf_heading_numbers_converts_ordered_list_items_to_headings(self):
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "orderedList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Purpose"}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Definitions"}],
                                }
                            ],
                        },
                    ],
                }
            ],
        }

        fixed, changes = policy.fix_adf_heading_numbers(adf)

        self.assertEqual(changes, 2)
        self.assertEqual([node["type"] for node in fixed["content"]], ["heading", "heading"])
        self.assertEqual(fixed["content"][0]["attrs"]["level"], 1)
        self.assertEqual(fixed["content"][1]["attrs"]["level"], 2)
        self.assertEqual(fixed["content"][0]["content"][0]["text"], "Purpose")
        self.assertEqual(fixed["content"][1]["content"][0]["text"], "Definitions")


if __name__ == "__main__":
    unittest.main()