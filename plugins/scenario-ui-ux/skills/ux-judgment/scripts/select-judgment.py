#!/usr/bin/env python3
"""Read-only lexical UX recipe selection. No models, network, or code changes."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit


DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "references" / "author-library.json"
EVIDENCE_KINDS = {
    "principle_synthesis", "reported_user_research", "author_case_retrospective",
    "reported_client_case", "reasoned_essay",
}
NOTICE = "오프라인 태그·명시적 동의어·키워드 검색이다. 의미검색·UX 진단·사용자 만족 검증은 수행하지 않는다."


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*|[가-힣]+", normalized)


def lexical_match(text_tokens: list[str], term: str) -> bool:
    """Exact Latin tokens; Korean prefix permits attached particles, not semantics."""
    wanted = tokens(term)
    if not wanted:
        return False
    for start in range(len(text_tokens) - len(wanted) + 1):
        found = text_tokens[start:start + len(wanted)]
        if all(
            actual == expected or (
                len(expected) >= 2
                and re.fullmatch(r"[가-힣]+", expected)
                and actual.startswith(expected)
            )
            for actual, expected in zip(found, wanted)
        ):
            return True
    return False


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def nonempty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def valid_date(value: object, *, allow_partial: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    if allow_partial and re.fullmatch(r"\d{4}(?:-\d{2})?", value):
        value += "-01-01" if len(value) == 4 else "-01"
    try:
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and bool(date.fromisoformat(value))
    except ValueError:
        return False


def validate_library(data: dict) -> dict[str, int]:
    require(isinstance(data, dict), "library root must be an object")
    require(data.get("format") == "ux-judgment-library/v1", "unsupported library format")
    require(data.get("promotion", {}).get("automatic") is False, "automatic promotion is forbidden")
    require(data.get("search", {}).get("semantic") is False, "selector must remain lexical")
    aliases = data.get("search", {}).get("aliases")
    require(isinstance(aliases, dict) and bool(aliases), "missing lexical aliases")
    require(all(nonempty_strings(value) for value in aliases.values()), "invalid aliases")
    groups = {}
    for item in data.get("imports", []):
        require(item.get("group") not in groups, "duplicate research group")
        require(bool(re.fullmatch(r"[a-f0-9]{64}", item.get("sha256", ""))), "missing research SHA-256")
        require(bool(item.get("repository_path")), "missing research path")
        groups[item["group"]] = item
    require(bool(groups), "missing research provenance")
    authors = {author["id"]: author for author in data.get("authors", [])}
    require(bool(authors) and len(authors) == len(data.get("authors", [])), "missing or duplicate authors")
    sources = {}
    for source in data.get("sources", []):
        source_id = source.get("id")
        require(isinstance(source_id, str) and source_id not in sources, "missing or duplicate source ID")
        url = urlsplit(source.get("canonical_url", ""))
        require(url.scheme == "https" and bool(url.netloc), "source requires canonical HTTPS URL")
        require(source.get("author_id") in authors, "unknown source author")
        require(source.get("evidence_kind") in EVIDENCE_KINDS, "unknown evidence kind")
        require(bool(source.get("date_basis")) and valid_date(source.get("checked_at")), "missing source date provenance")
        require("published_date" in source, "publication date must be present or explicitly null")
        require(source["published_date"] is None or valid_date(source["published_date"], allow_partial=True), "invalid publication date")
        require(bool(source.get("author_claim_ko")), "missing author claim")
        require(source.get("claim_attribution") == "author_statement_or_report", "source claim attribution missing")
        require(source.get("independent_outcome_verification") is False, "unverified outcome upgraded")
        require(source.get("origin", {}).get("group") in groups, "unknown source origin")
        require(bool(source.get("origin", {}).get("json_pointer")), "missing source pointer")
        sources[source_id] = source
    require(bool(sources), "missing sources")
    recipes = set()
    for recipe in data.get("recipes", []):
        recipe_id = recipe.get("id")
        require(isinstance(recipe_id, str) and recipe_id not in recipes, "missing or duplicate recipe ID")
        require(recipe.get("status") == "candidate", "research recipe cannot become a user decision")
        require(recipe.get("author_id") in authors, "unknown recipe author")
        refs = recipe.get("source_ids")
        require(nonempty_strings(refs) and all(ref in sources for ref in refs), "unknown recipe source")
        attribution = recipe.get("claim_vs_inference", {})
        require(attribution.get("implementation_attribution") == "our_operational_hypothesis", "missing inference attribution")
        require(attribution.get("source_claim_ids") == refs, "claim and source references differ")
        require(attribution.get("actual_product_outcome") == "not_run", "research outcome upgraded")
        require(attribution.get("user_preference") == "not_evaluated", "user preference upgraded")
        for field in ("problem_tags", "task_tags", "keywords", "small_repair_ko", "preserve_ko", "tradeoffs_ko", "countercases_ko"):
            require(nonempty_strings(recipe.get(field)), f"missing recipe {field}")
        require(bool(recipe.get("trigger_ko")) and bool(recipe.get("diagnosis_question_ko")), "missing causal entry")
        experiment = recipe.get("same_case_verification", {})
        require(experiment.get("execution_status") == "not_run", "planned experiment marked executed")
        require(experiment.get("functional_result") == "not_run", "planned functional result marked executed")
        require(experiment.get("user_preference_result") == "not_evaluated", "planned preference marked evaluated")
        require(bool(experiment.get("cases_ko") or experiment.get("fixture")), "missing experiment case")
        require(recipe.get("origin", {}).get("group") in groups, "unknown recipe origin")
        require(bool(recipe.get("origin", {}).get("json_pointer")), "missing recipe pointer")
        recipes.add(recipe_id)
    require(bool(recipes), "missing recipes")
    concept_ids = set()
    for concept in data["search"].get("specific_concepts", []):
        concept_id = concept.get("id")
        require(isinstance(concept_id, str) and concept_id not in concept_ids, "missing or duplicate specific concept")
        require(nonempty_strings(concept.get("terms")), "missing specific concept terms")
        context_groups = concept.get("context_groups", [])
        require(isinstance(context_groups, list) and len(context_groups) >= 2 and all(nonempty_strings(group) for group in context_groups), "specific context needs multiple lexical groups")
        require(bool(concept.get("reason_ko")), "missing specific match explanation")
        require(concept.get("attribution") == "our_lexical_routing_adapter_not_author_claim", "specific routing must not become an author claim")
        require(bool(concept.get("targets")), "missing specific concept targets")
        for target in concept["targets"]:
            require(target.get("recipe_id") in recipes, "unknown specific concept recipe")
            require(type(target.get("weight")) is int and 1 <= target["weight"] <= 100, "invalid specific concept weight")
        concept_ids.add(concept_id)
    for author in authors.values():
        require(nonempty_strings(author.get("source_ids")), "author has no source references")
        require(all(ref in sources for ref in author["source_ids"]), "unknown author source")
    return {"authors": len(authors), "sources": len(sources), "recipes": len(recipes)}


def select(data: dict, fields: list[tuple[str, str]], limit: int) -> list[dict]:
    aliases = data["search"]["aliases"]
    authors = {author["id"]: author for author in data["authors"]}
    sources = {source["id"]: source for source in data["sources"]}
    prepared = [(field, tokens(text)) for field, text in fields if text.strip()]
    ranked = []
    for recipe in data["recipes"]:
        reasons = []
        for concept in data["search"].get("specific_concepts", []):
            target = next((target for target in concept["targets"] if target["recipe_id"] == recipe["id"]), None)
            if target is None:
                continue
            for field, query_tokens in prepared:
                matched = next((term for term in [concept["id"], *concept["terms"]] if lexical_match(query_tokens, term)), None)
                if matched is None and field != "tag":
                    context = [next((term for term in group if lexical_match(query_tokens, term)), None) for group in concept["context_groups"]]
                    if all(context):
                        matched = " + ".join(context)
                if matched is not None:
                    reasons.append({"input_field": field, "match_type": "specific_lexical_concept", "tag": concept["id"], "matched_term": matched, "weight": target["weight"], "explanation_ko": concept["reason_ko"]})
                    break
        for field, query_tokens in prepared:
            for kind in ("problem", "task"):
                for tag in recipe[kind + "_tags"]:
                    matched = next((term for term in [tag, *aliases.get(tag, [])] if lexical_match(query_tokens, term)), None)
                    if matched is None:
                        continue
                    weight = 6 if field == "tag" else (5 if field == kind else 2 if field in ("problem", "task") else 3)
                    reasons.append({"input_field": field, "match_type": "tag_or_explicit_alias", "tag": tag, "matched_term": matched, "weight": weight})
            matched_terms = {reason["matched_term"] for reason in reasons if reason["input_field"] == field}
            if field != "tag":
                for term in recipe.get("keywords", []):
                    if term not in matched_terms and lexical_match(query_tokens, term):
                        reasons.append({"input_field": field, "match_type": "curated_keyword", "matched_term": term, "weight": 1})
        if not reasons:
            continue
        # Repeating "feedback" in problem and task is one signal, not two votes.
        signal_weights = {}
        for reason in reasons:
            key = (reason["match_type"] == "specific_lexical_concept", reason.get("tag", tuple(tokens(reason["matched_term"]))))
            signal_weights[key] = max(signal_weights.get(key, 0), reason["weight"])
        specificity_score = sum(weight for (specific, _), weight in signal_weights.items() if specific)
        author = authors[recipe["author_id"]]
        ranked.append({"score": sum(signal_weights.values()), "specificity_score": specificity_score, "matched_reasons": reasons, "author": {key: author[key] for key in ("id", "name", "canonical_home")}, "recipe": recipe, "sources": [sources[source_id] for source_id in recipe["source_ids"]]})
    return sorted(ranked, key=lambda result: (-result["specificity_score"], -result["score"], result["recipe"]["id"]))[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=NOTICE)
    parser.add_argument("query", nargs="?", default="", help="free text; lexical matching only")
    parser.add_argument("--problem", default="", help="symptom or problem tags")
    parser.add_argument("--task", default="", help="task text or tags")
    parser.add_argument("--tag", action="append", default=[], help="explicit tag; repeatable")
    parser.add_argument("--limit", type=int, default=3, help="1–20 candidates; default 3")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--validate", action="store_true", help="validate metadata; does not verify UX or user approval")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 20:
        parser.error("--limit must be between 1 and 20")
    fields = [("query", args.query), ("problem", args.problem), ("task", args.task)] + [("tag", tag) for tag in args.tag]
    has_query = any(text.strip() for _, text in fields)
    if not args.validate and not has_query:
        parser.error("provide a query, --problem, --task, or --tag")
    if args.validate and has_query:
        parser.error("--validate cannot be combined with a search")
    try:
        data = json.loads(args.library.read_text(encoding="utf-8"))
        counts = validate_library(data)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"library error: {error}\n")
    if args.validate:
        print(json.dumps({"valid": True, "scope": "metadata_only", **counts, "notice": NOTICE}, ensure_ascii=False, indent=2))
        return 0
    candidates = select(data, fields, args.limit)
    result = {"match_method": data["search"]["method"], "semantic": False, "notice": NOTICE, "query": {"text": args.query, "problem": args.problem, "task": args.task, "tags": args.tag}, "candidate_count": len(candidates), "candidates": candidates}
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(NOTICE)
        if not candidates:
            print("매칭 후보 없음. 명시적인 증상·과업 태그로 다시 좁히십시오.")
        for index, candidate in enumerate(candidates, 1):
            recipe = candidate["recipe"]
            print(f"\n{index}. {recipe['id']} · {recipe['title_ko']} ({candidate['author']['name']}, candidate)")
            print("매칭: " + "; ".join(f"{reason['input_field']}:{reason['matched_term']}" for reason in candidate["matched_reasons"]))
            print("진단: " + recipe["diagnosis_question_ko"])
            for label, field in (("수리 후보", "small_repair_ko"), ("보존", "preserve_ko"), ("역효과", "tradeoffs_ko"), ("맞지 않는 경우", "countercases_ko")):
                print(label + ": " + " / ".join(recipe[field]))
            print("동일 사례 검증: " + json.dumps(recipe["same_case_verification"], ensure_ascii=False))
            for source in candidate["sources"]:
                print(f"근거: {source['canonical_url']} · {source['published_date'] or '게시일 미공개'} · {source['evidence_kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
