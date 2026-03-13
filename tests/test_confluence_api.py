import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


confluence_api = load_module("publisher_confluence_api", "scripts/publisherlib/confluence_api.py")


class TestConfluenceApi(unittest.TestCase):
    def test_create_page_includes_parent_and_labels(self):
        response = Mock()
        response.json.return_value = {"id": "100"}
        response.raise_for_status.return_value = None

        with patch.object(confluence_api.requests, "post", return_value=response) as mock_post:
            result = confluence_api.create_page(
                "https://example.atlassian.net",
                {"Authorization": "Basic token"},
                "123",
                "Policy Title",
                {"version": 1, "type": "doc", "content": []},
                parent_id="456",
                labels=["policy", "approved"],
            )

        self.assertEqual(result["id"], "100")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["spaceId"], "123")
        self.assertEqual(payload["parentId"], "456")
        self.assertEqual(payload["metadata"]["labels"], [{"name": "policy"}, {"name": "approved"}])
        self.assertEqual(json.loads(payload["body"]["value"]), {"version": 1, "type": "doc", "content": []})

    def test_resolve_parent_id_ignores_blank_title(self):
        with patch.object(confluence_api.requests, "get") as mock_get:
            result = confluence_api.resolve_parent_id(
                "https://example.atlassian.net",
                {"Authorization": "Basic token"},
                "DOCS",
                "   ",
            )

        self.assertIsNone(result)
        mock_get.assert_not_called()

    def test_fetch_page_adf_decodes_atlas_doc_body(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "title": "Example Page",
            "body": {
                "atlas_doc_format": {
                    "value": json.dumps({"version": 1, "type": "doc", "content": []})
                }
            },
        }

        with patch.object(confluence_api.requests, "get", return_value=response):
            adf, title = confluence_api.fetch_page_adf(
                "https://example.atlassian.net",
                {"Authorization": "Basic token"},
                "42",
            )

        self.assertEqual(title, "Example Page")
        self.assertEqual(adf["type"], "doc")


if __name__ == "__main__":
    unittest.main()