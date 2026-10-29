#!/usr/bin/env python3
"""Return a deterministic work plan from a classified request; never execute skills.

Usage: python3 route-development.py --request '{"work_type":"ui","new_flow":true}'
       printf '%s' '{"work_type":"bugfix","has_ui":true}' | python3 route-development.py

Classification remains the agent's responsibility. This small router is not a
semantic search engine and cannot prove that the input describes the real task.
"""
import argparse
import json
import sys

WORK_TYPES = {'feature', 'ui', 'bugfix', 'review', 'backend', 'copy', 'motion', 'feedback'}
FLAGS = {'new_flow', 'ambiguous', 'behavior_change', 'has_ui'}
ALLOWED = {'work_type', 'framework'} | FLAGS


def route(request):
    if not isinstance(request, dict):
        raise ValueError('Request must be a JSON object')
    unknown = set(request) - ALLOWED
    if unknown:
        raise ValueError(f'Unknown request fields: {", ".join(sorted(unknown))}')
    work = request.get('work_type')
    if work not in WORK_TYPES:
        raise ValueError(f'work_type must be one of: {", ".join(sorted(WORK_TYPES))}')
    for field in FLAGS:
        if field in request and type(request[field]) is not bool:
            raise ValueError(f'{field} must be a JSON boolean')
    framework = request.get('framework')
    if framework is not None and (not isinstance(framework, str) or len(framework) > 80):
        raise ValueError('framework must be a string with at most 80 characters')
    new_flow = request.get('new_flow', False)
    ambiguous = request.get('ambiguous', False)
    has_ui = request.get('has_ui', work in {'ui', 'motion'} or new_flow)
    behavior = request.get('behavior_change', work in {'feature', 'backend', 'bugfix'} or new_flow)
    if work in {'ui', 'motion'} and not has_ui:
        raise ValueError('UI or motion work requires has_ui=true; reclassify the request if no interface is touched')
    if work in {'copy', 'feedback'} and new_flow:
        raise ValueError('A new flow requires feature/ui/backend classification, not copy/feedback')
    plan = []

    def step(role, skills, reason, evidence):
        plan.append({'role': role, 'skills': skills, 'reason': reason,
                     'required_evidence': evidence, 'execution_status': 'not_run'})

    if work == 'copy':
        step('write', ['plain-writing'], 'Write or revise the requested text while preserving facts and uncertainty.',
             ['Requested audience, meaning and output constraints remain intact.'])
    elif work == 'feedback':
        step('feedback-to-evidence', ['da-development-method'],
             'Link the user correction to its triggering task, change and result; retrieve relevant accepted/rejected precedents.',
             ['Original user wording and topic/project scope.', 'Result after the correction and whether the user accepted it.',
              'Repeated corrections become scoped rule changes with provenance, rather than disappearing in chat.'])
        step('report', ['plain-writing'], 'State the recorded correction and next action briefly.',
             ['User judgement and automated test results are reported separately.'])
    else:
        step('scope', ['da-development-method'],
             'Apply the current repository harness and user decisions before choosing the necessary workflow.',
             ['Current task scope, relevant source/version and existing service instructions.'])
        if work == 'review':
            step('review', ['gstack-review'], 'Review the requested changes without treating a review-only request as authorization to implement.',
                 ['Findings linked to concrete code, observed behavior or a reproducible case.'])
            if has_ui:
                step('browser-review', ['live-browser-session', 'ux-judgment'],
                     'Inspect the interface as the user and reproduce important interactions; retain review-only scope.',
                     ['Observed scenario results, errors and inspected screenshots.',
                      'No writes outside the currently authorized test scope.'])
        else:
            if ambiguous:
                step('requirements', ['gstack-office-hours'],
                     'Resolve material uncertainty in the product goal without repeating information already supplied.',
                     ['Concise user, action, expected outcome, exceptions and unresolved assumptions.'])
            if new_flow and has_ui:
                step('wireframe', ['text-wireframe-planner'],
                     'Connect the new user journey from entry through action to result before implementing its layout.',
                     ['A text flow with success, empty/error/cancel states relevant to the actual task.'])
            if work in {'feature', 'backend'} and behavior:
                step('engineering-plan', ['gstack-plan-eng-review'],
                     'Review the changed API, state or service boundaries; omit a second product-planning round.',
                     ['Affected contracts, persistence/container boundary and a focused verification plan.'])
            if has_ui:
                step('interface', ['scenario-ui-ux', 'ux-judgment'],
                     'Use relevant design references and designer judgment to choose structure, disclosure and shared components for this scenario; record the decisions in DESIGN.md.',
                     ['Relevant user preferences with scope, source and result.',
                      'Reference decisions: take, avoid, application and inspected evidence; reuse existing decisions for small fixes.',
                      'Observed UX symptom, causal hypothesis, repair and same-task verification where a flow problem exists.',
                      'Readable grouping, spacing and preserved keyboard/interaction paths.'])
            if work == 'motion':
                step('motion', ['craft-ui-motion'],
                     'Implement purposeful motion in the existing interface and inspect intermediate states.',
                     ['Trigger-relative continuity, interruption/repeated input and reduced-motion behavior.'])
            if work == 'bugfix':
                step('reproduce-and-fix', ['da-development-method'],
                     'Use a minimal reproducible failure to establish the cause, fix it and re-run that case.',
                     ['The causal failure before the fix and outcome after it.',
                      'A focused regression check only where its ongoing value justifies maintenance.'])
            else:
                step('implement', ['da-development-method'],
                     'Implement the scoped change with existing components; use TDD for material behavior rather than importing a second full methodology.',
                     ['Working behavior and relevant contract checks; no tests that merely restate implementation.'])
            # Small fixes do not gain a second review/model gate merely because the router exists.
            if work in {'feature', 'backend'} and behavior:
                step('review', ['gstack-review'],
                     'Inspect the material behavior change once before delivery.',
                     ['Concrete issues resolved within the already authorized scope.'])
            if has_ui:
                browser_skill = 'gstack-qa' if new_flow else 'live-browser-session'
                step('browser-verification', [browser_skill],
                     'Run one browser verification path: broader flow QA for new journeys, focused live-session verification for local changes.',
                     ['Actual user-scenario assertions and inspected screenshots.',
                      'Console/request failures and relevant intermediate motion states.',
                      'Run the configured project design gate once; missing/stale required evidence is not a pass.',
                      'Record functional checks separately from user satisfaction.'])
        step('report', ['plain-writing'], 'Report the result, supporting checks and unverified limits concisely.',
             ['Only checks actually executed are marked passed.'])
    return {
        'schema_version': 1,
        'classification': {'work_type': work, 'new_flow': new_flow, 'ambiguous': ambiguous,
                           'behavior_change': behavior, 'has_ui': has_ui, 'framework': framework},
        'mode': 'review_only' if work == 'review' else 'scoped_work',
        'plan': plan,
        'skills_to_check': list(dict.fromkeys(skill for item in plan for skill in item['skills'])),
        'execution_status': 'not_run',
        'requirements': [
            'Verify that each selected skill exists before using it; an absent gstack installation is not an executed review or QA.',
            'The plan selects workflow roles, not permissions. Preserve the current action/event/path authorization contract.',
            'No extra user approval or larger-model approval is created for an already authorized small fix.',
            'Do not perform two independent browser QA runs for the same purpose.',
            'This router uses classified fields, not semantic retrieval; check classification against the real request and retrieve relevant evidence separately.'
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', help='Classified request as a JSON object; otherwise read stdin')
    args = parser.parse_args()
    try:
        raw = args.request if args.request is not None else sys.stdin.read()
        result = route(json.loads(raw))
    except (ValueError, TypeError) as error:
        parser.exit(2, f'Invalid request: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
