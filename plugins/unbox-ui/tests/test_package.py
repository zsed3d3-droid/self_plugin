"""Validate Unbox UI packaging without external dependencies or app mutations."""

import json
from pathlib import Path
import re
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parents[1]


class PackageTest(unittest.TestCase):
    def test_manifests_and_marketplace(self):
        manifest = json.loads((PLUGIN / "plugin.json").read_text())
        self.assertEqual(manifest, json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text()))
        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        entries = json.loads((REPO / ".agents/plugins/marketplace.json").read_text())["plugins"]
        matching = [entry for entry in entries if entry["name"] == manifest["name"]]
        self.assertEqual(len(matching), 1)
        self.assertEqual((REPO / matching[0]["source"]["path"]).resolve(), PLUGIN)
        self.assertEqual(matching[0]["policy"]["installation"], "AVAILABLE")
        self.assertEqual(matching[0]["category"], manifest["interface"]["category"])
        skills_root = (PLUGIN / manifest["skills"]).resolve()
        self.assertTrue(skills_root.is_relative_to(PLUGIN))
        skills = {path.name: path for path in skills_root.iterdir() if path.is_dir()}
        self.assertEqual(set(skills), {"unbox-ui"})
        for name, path in skills.items():
            self.assertTrue((path / "SKILL.md").is_file())
            self.assertTrue((path / "agents/openai.yaml").is_file())
        for prompt in manifest["interface"]["defaultPrompt"]:
            names = re.findall(r"\$([a-z0-9-]+)", prompt)
            self.assertTrue(names)
            for name in names:
                self.assertIn(name, skills)

    def test_local_document_links_resolve_within_plugin(self):
        for document in PLUGIN.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
                if "://" not in target and not target.startswith("#"):
                    resolved = (document.parent / target.split("#")[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(PLUGIN), str(resolved))
                    self.assertTrue(resolved.is_file(), str(resolved))


if __name__ == "__main__":
    unittest.main()
