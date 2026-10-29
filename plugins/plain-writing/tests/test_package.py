"""Offline discovery and document-link checks for the writing plugin."""
import json
from pathlib import Path
import re
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parents[1]


class PackageTest(unittest.TestCase):
    def test_discovery(self):
        manifest = json.loads((PLUGIN / 'plugin.json').read_text())
        self.assertEqual(manifest, json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text()))
        self.assertEqual(manifest['name'], PLUGIN.name)
        self.assertRegex(manifest['version'], r'^\d+\.\d+\.\d+$')
        entries = json.loads((REPO / '.agents/plugins/marketplace.json').read_text())['plugins']
        matching = [entry for entry in entries if entry['name'] == manifest['name']]
        self.assertEqual(len(matching), 1)
        self.assertEqual((REPO / matching[0]['source']['path']).resolve(), PLUGIN)
        self.assertEqual(matching[0]['policy']['installation'], 'AVAILABLE')
        skills = (PLUGIN / manifest['skills']).resolve()
        self.assertTrue(skills.is_relative_to(PLUGIN))
        names = {path.parent.name for path in skills.glob('*/SKILL.md')}
        self.assertEqual(names, {'plain-writing'})
        for prompt in manifest['interface']['defaultPrompt']:
            invoked = set(re.findall(r'\$([a-z0-9-]+)', prompt))
            self.assertTrue(invoked)
            self.assertLessEqual(invoked, names)
        for name in names:
            self.assertTrue((skills / name / 'agents/openai.yaml').is_file())

    def test_document_links(self):
        documents = list(PLUGIN.rglob('*.md'))
        self.assertTrue(documents)
        for document in documents:
            for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                resolved = (document.parent / target.split('#')[0]).resolve()
                self.assertTrue(resolved.is_relative_to(PLUGIN), str(resolved))
                self.assertTrue(resolved.is_file(), str(resolved))


if __name__ == '__main__':
    unittest.main()
