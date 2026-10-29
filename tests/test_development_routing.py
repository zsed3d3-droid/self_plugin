"""Behavior checks for scenario selection and non-destructive profile installation."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


router = load('development_router', 'route-development.py')
installer = load('development_installer', 'setup-development.py')


class RouteTest(unittest.TestCase):
    def skills(self, request):
        return router.route(request)['skills_to_check']

    def test_small_ui_bug_is_fixed_without_replanning_or_extra_review_gate(self):
        plan = router.route({'work_type': 'bugfix', 'has_ui': True})
        skills = plan['skills_to_check']
        self.assertIn('live-browser-session', skills)
        self.assertNotIn('text-wireframe-planner', skills)
        self.assertNotIn('gstack-office-hours', skills)
        self.assertNotIn('gstack-plan-eng-review', skills)
        self.assertNotIn('gstack-review', skills)
        roles = [step['role'] for step in plan['plan']]
        self.assertIn('reproduce-and-fix', roles)
        self.assertEqual(roles.count('browser-verification'), 1)
        self.assertTrue(all(step['execution_status'] == 'not_run' for step in plan['plan']))

    def test_new_ui_flow_connects_requirements_wireframe_and_one_browser_path(self):
        plan = router.route({'work_type': 'feature', 'new_flow': True, 'ambiguous': True, 'framework': 'react'})
        skills = plan['skills_to_check']
        for name in ('gstack-office-hours', 'text-wireframe-planner', 'scenario-ui-ux', 'gstack-plan-eng-review', 'gstack-review', 'gstack-qa'):
            self.assertIn(name, skills)
        self.assertNotIn('live-browser-session', skills)
        self.assertEqual(plan['classification']['framework'], 'react')
        self.assertEqual(plan['execution_status'], 'not_run')

    def test_review_request_has_no_implementation_steps(self):
        plan = router.route({'work_type': 'review', 'has_ui': True, 'behavior_change': True})
        self.assertEqual(plan['mode'], 'review_only')
        self.assertEqual([step['role'] for step in plan['plan']], ['scope', 'review', 'browser-review', 'report'])
        self.assertNotIn('gstack-qa', plan['skills_to_check'])

    def test_backend_never_creates_ui_or_motion_work(self):
        skills = self.skills({'work_type': 'backend'})
        self.assertIn('gstack-plan-eng-review', skills)
        self.assertNotIn('scenario-ui-ux', skills)
        self.assertNotIn('craft-ui-motion', skills)
        self.assertNotIn('live-browser-session', skills)

    def test_copy_uses_only_writing(self):
        self.assertEqual(self.skills({'work_type': 'copy'}), ['plain-writing'])

    def test_motion_inspects_intermediate_states_without_new_flow_interview(self):
        skills = self.skills({'work_type': 'motion'})
        self.assertIn('craft-ui-motion', skills)
        self.assertIn('scenario-ui-ux', skills)
        self.assertNotIn('text-wireframe-planner', skills)
        self.assertNotIn('gstack-office-hours', skills)

    def test_feedback_links_evidence_instead_of_forcing_a_code_workflow(self):
        plan = router.route({'work_type': 'feedback'})
        self.assertEqual([item['role'] for item in plan['plan']], ['feedback-to-evidence', 'report'])
        self.assertNotIn('gstack-plan-eng-review', plan['skills_to_check'])

    def test_invalid_or_contradictory_classification_is_rejected(self):
        for request in ({'work_type': 'other'}, {'work_type': 'ui', 'has_ui': 'false'},
                        {'work_type': 'ui', 'has_ui': False}, {'work_type': 'copy', 'new_flow': True},
                        {'work_type': 'feature', 'framework': []}, {'work_type': 'backend', 'pretend_executed': True}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                router.route(request)

    def test_cli_accepts_stdin_and_produces_machine_readable_plan(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/route-development.py')],
                                input=json.dumps({'work_type': 'ui'}), text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)['classification']['work_type'], 'ui')


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.source = self.root / 'toolkit'
        self.project.mkdir()
        (self.source / 'scripts').mkdir(parents=True)
        for name in ('check-containers.py', 'route-development.py'):
            (self.source / 'scripts' / name).write_bytes((ROOT / 'scripts' / name).read_bytes())
        for skill, plugin in installer.SKILLS.items():
            folder = self.source / 'plugins' / plugin / 'skills' / skill
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'SKILL.md').write_text(f'---\nname: {skill}\ndescription: >-\n  {skill} source-specific capability.\n  Apply for its concrete scenario.\n---\nInstructions.\n')

    def snapshot(self):
        return {str(p.relative_to(self.project)): ('link', p.readlink().as_posix()) if p.is_symlink() else ('file', p.read_bytes())
                for p in self.project.rglob('*') if p.is_file() or p.is_symlink()}

    def install(self):
        installer.install(self.project, self.source)

    def test_reinstall_is_idempotent_and_preserves_root_instructions(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            (self.project / name).write_text('Repository-owned rules\n')
        self.install()
        before = self.snapshot()
        self.install()
        self.assertEqual(before, self.snapshot())
        self.assertEqual((self.project / 'AGENTS.md').read_text(), 'Repository-owned rules\n')
        self.assertEqual((self.project / 'CLAUDE.md').read_text(), 'Repository-owned rules\n')
        wrapper = self.project / '.agents/skills/scenario-ui-ux/SKILL.md'
        self.assertIn('scenario-ui-ux source-specific capability. Apply for its concrete scenario.', wrapper.read_text())
        link = self.project / '.cursor/skills/scenario-ui-ux'
        self.assertEqual((link / 'SKILL.md').resolve(), wrapper.resolve())

    def test_unmanaged_checker_conflict_fails_before_any_generated_writes(self):
        checker = self.project / '.devtools/check-containers.py'
        checker.parent.mkdir()
        checker.write_text('User-owned checker\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Unmanaged destination'):
            self.install()
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project / '.agents').exists())

    def test_managed_helper_updates_but_edited_helper_is_preserved(self):
        self.install()
        (self.source / 'scripts/check-containers.py').write_text('# New source checker\n')
        self.install()
        checker = self.project / '.devtools/check-containers.py'
        self.assertEqual(checker.read_text(), '# New source checker\n')
        checker.write_text('# User changed the installed checker\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Managed file was edited'):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_unknown_discovery_directory_conflict_is_preflighted(self):
        conflict = self.project / '.cursor/skills/scenario-ui-ux'
        conflict.mkdir(parents=True)
        (conflict / 'SKILL.md').write_text('User skill\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Unmanaged skill destination'):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_destination_symlink_cannot_redirect_installer_outside_project(self):
        external = self.root / 'external'
        external.mkdir()
        (self.project / '.agents').symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes project'):
            self.install()
        self.assertEqual(list(external.iterdir()), [])

    def test_legacy_managed_install_can_gain_manifest(self):
        # Old installer used managed markers for text, exact bytes for the checker, and no manifest.
        rules = self.project / '.cursor/rules/da-development.mdc'
        rules.parent.mkdir(parents=True)
        rules.write_text(installer.MARKER + '\nLegacy generated rule\n')
        checker = self.project / '.devtools/check-containers.py'
        checker.parent.mkdir()
        checker.write_bytes((self.source / 'scripts/check-containers.py').read_bytes())
        self.install()
        self.assertTrue((self.project / installer.MANIFEST).is_file())
        self.assertIn('route-development.py', (self.project / '.cursor/rules/da-development.mdc').read_text())

    def test_missing_source_fails_without_partial_install(self):
        (self.source / 'plugins/plain-writing/skills/plain-writing/SKILL.md').unlink()
        with self.assertRaisesRegex(ValueError, 'Source skill missing'):
            self.install()
        self.assertEqual(list(self.project.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
