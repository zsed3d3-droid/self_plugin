"""Protect source selection from unrelated results and invented verification claims."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reference_plan', ROOT / 'plugins/scenario-ui-ux/skills/scenario-ui-ux/scripts/reference-plan.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReferencePlanTests(unittest.TestCase):
    def test_korean_control_task_recovers_official_patterns(self):
        result = module.plan('상태 드롭다운과 기한 달력', limit=5)
        ids = {item['id'] for item in result['references']}
        self.assertIn('radix-select', ids)
        self.assertIn('reactaria-date', ids)
        self.assertIsNone(result['framework_profile'])

    def test_no_results_are_not_invented(self):
        result = module.plan('zzzzzx-unrelated')
        self.assertTrue(result['no_match'])
        self.assertEqual(result['references'], [])

    def test_candidates_do_not_claim_execution_or_adoption(self):
        result = module.plan('create dialog', stack='react')
        self.assertEqual(result['execution_status'], 'not_run')
        self.assertIsNotNone(result['framework_profile'])
        for item in result['references']:
            self.assertFalse(item['visual_inspected'])
            self.assertIsNone(item['adopted'])
            self.assertIsNone(item['screenshot'])

    def test_invalid_task_or_limit_rejected(self):
        for task, limit in [('', 5), ('dialog', 0), ('dialog', 14)]:
            with self.assertRaises(ValueError):
                module.plan(task, limit=limit)


if __name__ == '__main__':
    unittest.main()
