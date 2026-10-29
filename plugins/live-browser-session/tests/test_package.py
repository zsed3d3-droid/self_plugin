"""Offline discovery, link and script checks for the live browser session plugin."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parents[1]
SCRIPTS = PLUGIN / 'skills/live-browser-session/scripts'


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
        self.assertEqual(names, {'live-browser-session'})
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

    def test_shell_script_syntax(self):
        subprocess.run(['bash', '-n', str(SCRIPTS / 'browser-session.sh')], check=True)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_node_script_syntax(self):
        for name in ('cdp-close.mjs', 'page-guard.mjs'):
            subprocess.run(['node', '--check', str(SCRIPTS / name)], check=True)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_write_allow_rules(self):
        script = (
            "const { isAllowed } = await import(process.argv[1]);"
            "const allow = [/^POST \\/api\\/demo\\/switch\\//];"
            "const cases = [['GET','/a',true],['head','/a',true],['OPTIONS','/a',true],"
            "['POST','/api/demo/switch/1',true],['POST','/api/demo/login/1',false],"
            "['DELETE','/api/demo/switch/1',false],['PATCH','/x',false]];"
            "for (const [m,p,want] of cases) if (isAllowed(m,p,allow) !== want) { console.error(m,p); process.exit(1); }"
        )
        url = (SCRIPTS / 'page-guard.mjs').as_uri()
        subprocess.run(['node', '--input-type=module', '-e', script, url], check=True)

    def test_stop_refuses_folder_without_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            keep = Path(folder) / 'keep.txt'
            keep.write_text('user data')
            env = dict(os.environ, LBS_PORT='65531')
            result = subprocess.run(['bash', str(SCRIPTS / 'browser-session.sh'), 'stop', '--profile', folder],
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(keep.is_file())

    def test_stop_requires_profile(self):
        result = subprocess.run(['bash', str(SCRIPTS / 'browser-session.sh'), 'stop'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
