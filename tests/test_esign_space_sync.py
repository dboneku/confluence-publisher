import importlib.util
import sys
import unittest
from pathlib import Path


def load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sync_script = load_module(
    "esign_space_sync_script",
    "scripts/sync_esign_space_settings.py",
)


class TestESignSpaceSyncHelpers(unittest.TestCase):
    def test_filter_spaces_keeps_current_global_spaces(self):
        spaces = [
            {"key": "QA", "name": "Quality", "status": "current", "type": "global"},
            {"key": "~nick", "name": "Nick personal", "status": "current", "type": "personal"},
            {"key": "OLD", "name": "Old", "status": "archived", "type": "global"},
        ]

        result = sync_script.filter_spaces(spaces)

        self.assertEqual([space["key"] for space in result], ["QA"])

    def test_filter_spaces_honors_include_and_exclude(self):
        spaces = [
            {"key": "OPS", "name": "Ops", "status": "current", "type": "global"},
            {"key": "QA", "name": "Quality", "status": "current", "type": "global"},
        ]

        result = sync_script.filter_spaces(
            spaces,
            include_keys={"OPS", "QA"},
            exclude_keys={"QA"},
        )

        self.assertEqual([space["key"] for space in result], ["OPS"])

    def test_build_settings_url_substitutes_template_values(self):
        url = sync_script.build_settings_url(
            "{baseUrl}/wiki/spaces/{spaceKey}/settings/apps/{appPath}",
            "https://oversite-health.atlassian.net",
            "QA",
            "com.digitalrose.edoc__space-settings",
        )

        self.assertEqual(
            url,
            "https://oversite-health.atlassian.net/wiki/spaces/QA/settings/apps/com.digitalrose.edoc__space-settings",
        )

    def test_render_plan_includes_admins_and_doc_types(self):
        plan = sync_script.render_plan(
            spaces=[{"key": "QA", "name": "Quality"}],
            document_types=sync_script.DEFAULT_DOCUMENT_TYPES,
            admins=sync_script.DEFAULT_ADMINS,
        )

        self.assertIn("POL: Policy", plan)
        self.assertIn("nick@clinicaloversite.com", plan)
        self.assertIn("QA :: Quality", plan)


if __name__ == "__main__":
    unittest.main()