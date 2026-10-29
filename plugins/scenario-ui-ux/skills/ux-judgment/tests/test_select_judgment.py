"""Meaningful metadata, provenance, and read-only lexical routing checks."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "select-judgment.py"
LIBRARY = SKILL / "references" / "author-library.json"
spec = importlib.util.spec_from_file_location("select_judgment", SCRIPT)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


class JudgmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(LIBRARY.read_text())

    def test_complete_normalized_candidates_and_provenance(self):
        self.assertEqual(selector.validate_library(self.data), {"authors": 10, "sources": 24, "recipes": 20})
        repository = SKILL.parents[3]
        original = {}
        for item in self.data["imports"]:
            content = (repository / item["repository_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), item["sha256"])
            original[item["group"]] = json.loads(content)
        for record in self.data["sources"] + self.data["recipes"]:
            node = original[record["origin"]["group"]]
            for part in record["origin"]["json_pointer"].lstrip("/").split("/"):
                node = node[int(part)] if isinstance(node, list) else node[part]
            self.assertEqual(node["id"], record["id"])
        group_b = [r for r in self.data["recipes"] if r["origin"]["group"] == "b"]
        self.assertTrue(all(r["status"] == "candidate" and r["origin"]["original_candidate_status"] == "not_reviewed" for r in group_b))

    def test_escape_and_keyboard_route_without_semantic_inference(self):
        results = selector.select(self.data, [("problem", "ＥＳＣＡＰＥ"), ("task", "ＫＥＹＢＯＡＲＤ")], 3)
        self.assertEqual(results[0]["recipe"]["id"], "uxb-norman-discovery")
        self.assertTrue(results[0]["matched_reasons"])

    def test_relevant_structure_and_tone_are_distinct(self):
        structure = selector.select(self.data, [("problem", "모든 폼이 동시 노출된다")], 1)
        tone = selector.select(self.data, [("tag", "tone-mismatch")], 1)
        self.assertEqual(structure[0]["recipe"]["id"], "uxb-nielsen-task-minimalism")
        self.assertEqual(tone[0]["recipe"]["id"], "uxb-walter-tone")

    def test_unrelated_query_has_no_fallback(self):
        self.assertEqual(selector.select(self.data, [("query", "quantum banana orbital")], 20), [])
        self.assertEqual(selector.select(self.data, [("query", "바나나 궤도 항성")], 20), [])

    def test_real_pin_conflict_precedes_repeated_generic_feedback(self):
        fields = [
            ("problem", "새 위치를 선택했는데 이전 초안이 좌표를 덮어씀, 상태 피드백과 mental model 불일치"),
            ("task", "이미지 위치별 피드백을 보존하고 작성"),
        ]
        before = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        results = selector.select(self.data, fields, 3)
        self.assertEqual([r["recipe"]["id"] for r in results], ["uxb-norman-discovery", "A-DS-1", "A-AB-2"])
        self.assertTrue(all(r["specificity_score"] > 0 for r in results))
        self.assertTrue(all(any(reason["match_type"] == "specific_lexical_concept" for reason in r["matched_reasons"]) for r in results))
        self.assertEqual(json.dumps(self.data, ensure_ascii=False, sort_keys=True), before)

    def test_coordinate_context_routes_without_feedback_or_mental_model_words(self):
        results = selector.select(self.data, [("problem", "선택한 좌표를 이전 초안이 덮어쓴다")], 3)
        self.assertEqual(results[0]["recipe"]["id"], "uxb-norman-discovery")
        self.assertIn(" + ", results[0]["matched_reasons"][0]["matched_term"])

    def test_specific_tag_is_explicit_and_location_alone_is_not_a_bug_claim(self):
        results = selector.select(self.data, [("tag", "state-intent-mismatch")], 1)
        self.assertEqual(results[0]["recipe"]["id"], "uxb-norman-discovery")
        self.assertEqual(selector.select(self.data, [("query", "위치별 과일 판매 지도")], 20), [])

    def test_tone_and_generic_feedback_do_not_become_mapping_issues(self):
        results = selector.select(self.data, [("problem", "오류 문구에 농담이 많다"), ("task", "간결한 피드백 문구")], 3)
        self.assertEqual(results[0]["recipe"]["id"], "uxb-walter-tone")
        self.assertTrue(all(r["specificity_score"] == 0 for r in results))
        generic = selector.select(self.data, [("problem", "피드백"), ("task", "피드백")], 3)
        irene = next(r for r in generic if r["recipe"]["id"] == "A-IA-2")
        self.assertEqual(irene["score"], 5)
        self.assertEqual(irene["specificity_score"], 0)

    def test_specific_route_cannot_reference_an_unknown_recipe(self):
        data = copy.deepcopy(self.data)
        data["search"]["specific_concepts"][0]["targets"][0]["recipe_id"] = "missing-recipe"
        with self.assertRaises(ValueError):
            selector.validate_library(data)

    def test_empty_or_invalid_cli_is_rejected(self):
        for args in ([], ["--limit", "0", "task"], ["--limit", "21", "task"], ["--validate", "task"]):
            result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)

    def test_broken_source_and_promoted_candidate_are_rejected(self):
        for change in ("unknown_source", "promoted", "missing_date", "invalid_date", "duplicate_source"):
            data = copy.deepcopy(self.data)
            if change == "unknown_source":
                data["recipes"][0]["source_ids"] = ["missing"]
            elif change == "promoted":
                data["recipes"][0]["status"] = "adopted"
            elif change == "missing_date":
                data["sources"][0]["date_basis"] = ""
            elif change == "invalid_date":
                data["sources"][0]["published_date"] = "2026-99-99"
            else:
                data["sources"].append(data["sources"][0])
            with self.assertRaises(ValueError):
                selector.validate_library(data)

    def test_invalid_json_root_is_a_validation_error(self):
        with self.assertRaises(ValueError):
            selector.validate_library([])

    def test_cli_is_read_only_and_reports_honest_empty_result(self):
        before = LIBRARY.read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPT), "quantum banana orbital"], capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["semantic"])
        self.assertEqual(payload["candidates"], [])
        self.assertEqual(LIBRARY.read_bytes(), before)

    def test_experience_example_has_no_fabricated_results(self):
        example = json.loads((SKILL / "templates" / "experience.example.json").read_text())
        for field in ("product", "cycle", "symptom", "cause", "change", "evidence", "actual_results", "limitations", "source_recipes", "status"):
            self.assertIn(field, example)
        self.assertEqual(example["status"], "not_run")
        self.assertEqual(example["evidence"], [])
        self.assertIsNone(example["symptom"]["observed"])
        self.assertEqual(example["actual_results"]["user_preference_status"], "not_evaluated")
        recipe_ids = {recipe["id"] for recipe in self.data["recipes"]}
        self.assertTrue(set(example["source_recipes"]) <= recipe_ids)


if __name__ == "__main__":
    unittest.main()
