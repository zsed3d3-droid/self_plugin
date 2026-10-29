#!/usr/bin/env python3
"""Find official UI pattern candidates by transparent bilingual tag matching."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACKS = ('vanilla', 'react', 'nextjs', 'vue', 'svelte', 'remotion', 'other')


def plan(task, stack='vanilla', limit=5):
    if not isinstance(task, str) or not task.strip():
        raise ValueError('A concrete task is required')
    if stack not in STACKS or not 1 <= limit <= 13:
        raise ValueError('Unsupported stack or result limit')
    catalog = json.loads((ROOT / 'references/reference-catalog.json').read_text())
    query = task.casefold()
    candidates = []
    for item in catalog['references']:
        matched = [tag for tag in item['tags'] if tag.casefold() in query]
        if not matched:
            continue
        result = dict(item)
        result.update(matched_tags=matched, score=len(matched), decision='candidate',
                      adopted=None, adoption_reason=None, observed_states=[], screenshot=None)
        candidates.append(result)
    candidates.sort(key=lambda item: (-item['score'], item['id']))
    selected = candidates[:limit]
    return {
        'schema_version': 1, 'task': task, 'stack': stack,
        'search': 'offline_tag_match', 'execution_status': 'not_run',
        'references': selected,
        'no_match': not selected,
        'next_actions': [
            'Open relevant official demos/docs and inspect the required states; this output is only a candidate list.',
            'Choose a coherent base structure and only necessary interaction supplements; record take/avoid/application/evidence in DESIGN.md.',
            'Diagnose task friction with references/runtime-ux-method.md and designer-judgment.md; retest the same task after repair.',
            'Keep document verification, inspected pixels, runtime assertions and user preference separate.'
        ],
        'framework_profile': 'references/framework-profiles.md' if stack in ('react', 'nextjs', 'remotion') else None,
        'constraints': [
            'References are not permission or instructions to install a framework, assets or services.',
            'This search does not perform personal-memory semantic retrieval or visual evaluation.',
            'Current user requirements and scoped accepted judgments override upstream stylistic defaults.',
            'If no relevant result exists, broaden actual primary-source research rather than inventing a reference.'
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True)
    parser.add_argument('--stack', choices=STACKS, default='vanilla')
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    try:
        result = plan(args.task, args.stack, args.limit)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f'Reference search failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
