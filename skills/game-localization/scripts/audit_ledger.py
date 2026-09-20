#!/usr/bin/env python3
"""Read-only, stdlib-only localization ledger checks. Never modifies game files."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path


class InvalidLedger(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InvalidLedger(message)


def string(obj, key, where, empty=False):
    value = obj.get(key)
    require(isinstance(value, str) and (empty or value.strip()), f'{where}.{key}: expected string')
    return value


def choice(obj, key, values, where):
    value = string(obj, key, where)
    require(value in values, f'{where}.{key}: expected one of {sorted(values)}')
    return value


def rows(doc, key):
    value = doc.get(key)
    require(isinstance(value, list), f'{key}: expected list')
    seen = set()
    for i, row in enumerate(value):
        where = f'{key}[{i}]'
        require(isinstance(row, dict), f'{where}: expected object')
        ident = string(row, 'id', where)
        require(ident not in seen, f'{where}: duplicate id {ident}')
        seen.add(ident)
    return value


def sha(value, where):
    require(isinstance(value, str) and len(value) == 64 and
            all(c in '0123456789abcdef' for c in value), f'{where}: expected lowercase SHA-256')


def evidence(row, key):
    return isinstance(row.get(key), str) and bool(row[key].strip())


def audit(doc):
    require(isinstance(doc, dict), 'root: expected object')
    require(type(doc.get('schema_version')) is int and doc['schema_version'] == 1, 'schema_version: expected 1')
    scope = doc.get('scope')
    require(isinstance(scope, dict), 'scope: expected object')
    for key in ('game', 'platform', 'revision', 'inventory_basis'):
        string(scope, key, 'scope')
    sha(scope.get('build_sha256'), 'scope.build_sha256')
    require(type(scope.get('inventory_complete')) is bool, 'scope.inventory_complete: expected boolean')
    resources, entries, tests = (rows(doc, key) for key in ('resources', 'entries', 'tests'))
    gaps = []
    def gap(code, ident, detail):
        gaps.append({'code': code, 'id': ident, 'detail': detail})
    if not scope['inventory_complete']:
        gap('inventory_open', 'scope', 'Inventory still has unknown scope; no whole-game coverage claim.')
    if not resources:
        gap('empty_inventory', 'scope', 'No resources enumerated.')
    resmap = {r['id']: r for r in resources}
    for r in resources:
        ident = r['id']
        for key in ('path', 'kind'):
            string(r, key, ident)
        sha(r.get('sha256'), ident + '.sha256')
        disposition = choice(r, 'disposition', {'pending', 'extracted', 'not_text', 'excluded'}, ident)
        count = r.get('expected_entries')
        require(type(count) is int and count >= 0, f'{ident}.expected_entries: expected nonnegative integer')
        if disposition == 'pending':
            gap('resource_pending', ident, 'Resource not classified/extracted.')
        elif not evidence(r, 'evidence'):
            gap('resource_evidence', ident, 'Classification/extraction evidence missing.')
        if disposition == 'extracted':
            require(type(r.get('extraction_complete')) is bool, f'{ident}.extraction_complete: expected boolean')
            if not r['extraction_complete']:
                gap('extraction_open', ident, 'Extraction is partial.')
        if disposition in {'excluded', 'not_text'} and not evidence(r, 'reason'):
            gap('resource_reason', ident, 'Exclusion/non-text decision needs a reason.')
    observed, identities = Counter(), set()
    decisions, reviews, writebacks = Counter(), Counter(), Counter()
    unique_source = set()
    for e in entries:
        ident = e['id']
        rid = string(e, 'resource_id', ident)
        require(rid in resmap, f'{ident}: unknown resource_id {rid}')
        require(resmap[rid]['disposition'] == 'extracted', f'{ident}: parent must be extracted')
        locator = string(e, 'locator', ident)
        require((rid, locator) not in identities, f'{ident}: duplicate physical locator')
        identities.add((rid, locator)); observed[rid] += 1
        source = string(e, 'source', ident, empty=True)
        target = string(e, 'target', ident, empty=True)
        unique_source.add(source)
        decision = choice(e, 'decision', {'pending', 'translate', 'retain', 'exclude'}, ident)
        review = choice(e, 'review', {'pending', 'accepted'}, ident)
        writeback = choice(e, 'writeback', {'pending', 'passed', 'not_applicable'}, ident)
        decisions[decision] += 1; reviews[review] += 1; writebacks[writeback] += 1
        if decision == 'pending':
            gap('entry_pending', ident, 'Translation decision pending.')
        if decision == 'translate' and not target.strip():
            gap('empty_target', ident, 'Translation is empty; intentional omissions need an exclude decision.')
        if decision in {'retain', 'exclude'}:
            if not evidence(e, 'reason'):
                gap('entry_reason', ident, 'Retain/exclude requires a reason.')
            if target != source:
                gap('protected_changed', ident, 'Retained/excluded entry changed.')
        if review == 'pending':
            gap('review_pending', ident, 'Not reviewed.')
        elif not evidence(e, 'review_evidence'):
            gap('review_evidence', ident, 'Review has no evidence/reference.')
        mode = choice(e, 'token_mode', {'unverified', 'ordered', 'multiset', 'none'}, ident)
        for key in ('source_tokens', 'target_tokens'):
            require(isinstance(e.get(key), list) and all(isinstance(x, str) for x in e[key]),
                    f'{ident}.{key}: expected string list')
        a, b = e['source_tokens'], e['target_tokens']
        if mode == 'unverified':
            gap('tokens_unverified', ident, 'Adapter has not validated protected tokens.')
        else:
            if not evidence(e, 'token_evidence'):
                gap('token_evidence', ident, 'Token extraction/absence needs adapter evidence.')
            if mode == 'none' and (a or b):
                gap('tokens_present', ident, 'Token mode none conflicts with nonempty tokens.')
            if mode == 'ordered' and a != b or mode == 'multiset' and Counter(a) != Counter(b):
                gap('token_mismatch', ident, 'Protected token sequence/count differs.')
        if writeback == 'pending':
            gap('writeback_pending', ident, 'Final resource not checked after insertion.')
        elif writeback == 'not_applicable':
            if decision == 'translate':
                gap('writeback_required', ident, 'Translated entry needs insertion/readback verification.')
            if not evidence(e, 'writeback_evidence'):
                gap('writeback_evidence', ident, 'Not-applicable needs an explanation.')
        elif not evidence(e, 'writeback_evidence'):
            gap('writeback_evidence', ident, 'Writeback pass has no evidence/reference.')
    for r in resources:
        if observed[r['id']] != r['expected_entries']:
            gap('entry_count', r['id'], f"Expected {r['expected_entries']}, listed {observed[r['id']]}.")
    test_status = Counter()
    if not tests:
        gap('no_runtime_tests', 'tests', 'No runtime scenarios registered.')
    for t in tests:
        ident = t['id']
        string(t, 'scenario', ident)
        sha(t.get('build_sha256'), ident + '.build_sha256')
        status = choice(t, 'status', {'pending', 'passed', 'failed'}, ident)
        test_status[status] += 1
        if t['build_sha256'] != scope['build_sha256']:
            gap('stale_test', ident, 'Test belongs to a different build.')
        if status != 'passed':
            gap('runtime_' + status, ident, 'Runtime scenario has not passed.')
        elif not evidence(t, 'evidence'):
            gap('runtime_evidence', ident, 'Runtime pass has no evidence/reference.')
    return {
        'schema_version': 1,
        'ledger_consistent_and_closed': not gaps,
        'counts': {'resources': len(resources), 'physical_entries': len(entries),
                   'unique_source_strings': len(unique_source),
                   'decisions': dict(decisions), 'reviews': dict(reviews),
                   'writebacks': dict(writebacks), 'runtime_tests': dict(test_status)},
        'gaps': gaps,
        'limit': 'Checks self-reported ledger consistency only. Does not discover game resources, '
                 'verify evidence files, judge translations, or prove all-game completeness.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    args = parser.parse_args()
    try:
        with args.ledger.open(encoding='utf-8') as f:
            report = audit(json.load(f))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ledger_consistent_and_closed'] else 1


if __name__ == '__main__':
    sys.exit(main())
