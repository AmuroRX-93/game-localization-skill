import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/game-localization/scripts/audit_ledger.py'
spec = importlib.util.spec_from_file_location('audit_ledger', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    return {'schema_version': 1,
            'scope': {'game': 'Synthetic test', 'platform': 'Synthetic', 'revision': 'demo',
                      'inventory_basis': 'Synthetic fixture only', 'build_sha256': 'a' * 64,
                      'inventory_complete': True},
            'resources': [{'id': 'r1', 'path': 'demo.bin::text', 'kind': 'text',
                           'sha256': 'b' * 64, 'disposition': 'extracted',
                           'expected_entries': 1, 'extraction_complete': True,
                           'evidence': 'Synthetic fixture'}],
            'entries': [{'id': 'e1', 'resource_id': 'r1', 'locator': 'text:1',
                         'source': 'Item {item}', 'target': '物品 {item}',
                         'decision': 'translate', 'review': 'accepted',
                         'review_evidence': 'Synthetic reviewer', 'writeback': 'passed',
                         'writeback_evidence': 'Synthetic readback', 'token_mode': 'ordered',
                         'source_tokens': ['{item}'], 'target_tokens': ['{item}'],
                         'token_evidence': 'Synthetic parser'}],
            'tests': [{'id': 't1', 'scenario': 'Synthetic screen', 'build_sha256': 'a' * 64,
                       'status': 'passed', 'evidence': 'Synthetic test result'}]}


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.doc = fixture()

    def codes(self):
        return {g['code'] for g in mod.audit(self.doc)['gaps']}

    def test_closed_fixture(self):
        self.assertTrue(mod.audit(self.doc)['ledger_consistent_and_closed'])

    def test_inventory_unknown_cannot_close(self):
        self.doc['scope']['inventory_complete'] = False
        self.assertIn('inventory_open', self.codes())

    def test_omitted_entry_detected(self):
        self.doc['entries'] = []
        self.assertIn('entry_count', self.codes())

    def test_duplicate_id_rejected(self):
        self.doc['entries'].append(copy.deepcopy(self.doc['entries'][0]))
        with self.assertRaises(mod.InvalidLedger): mod.audit(self.doc)

    def test_duplicate_physical_locator_rejected(self):
        row = copy.deepcopy(self.doc['entries'][0]); row['id'] = 'e2'
        self.doc['entries'].append(row)
        with self.assertRaises(mod.InvalidLedger): mod.audit(self.doc)

    def test_unknown_resource_rejected(self):
        self.doc['entries'][0]['resource_id'] = 'absent'
        with self.assertRaises(mod.InvalidLedger): mod.audit(self.doc)

    def test_token_loss_detected(self):
        self.doc['entries'][0]['target_tokens'] = []
        self.assertIn('token_mismatch', self.codes())

    def test_ordered_tokens_cannot_reorder(self):
        e = self.doc['entries'][0]
        e['source_tokens'] = ['%s', '%d']; e['target_tokens'] = ['%d', '%s']
        self.assertIn('token_mismatch', self.codes())

    def test_named_tokens_allow_reorder_but_not_duplicate_loss(self):
        e = self.doc['entries'][0]; e['token_mode'] = 'multiset'
        e['source_tokens'] = ['{a}', '{b}']; e['target_tokens'] = ['{b}', '{a}']
        self.assertNotIn('token_mismatch', self.codes())
        e['source_tokens'].append('{a}')
        self.assertIn('token_mismatch', self.codes())

    def test_no_tokens_requires_evidence(self):
        e = self.doc['entries'][0]; e['token_mode'] = 'none'
        e['source_tokens'] = []; e['target_tokens'] = []; del e['token_evidence']
        self.assertIn('token_evidence', self.codes())

    def test_retained_internal_key_must_not_change(self):
        e = self.doc['entries'][0]; e['decision'] = 'retain'; e['reason'] = 'Resource key'
        self.assertIn('protected_changed', self.codes())

    def test_stale_build_test_detected(self):
        self.doc['tests'][0]['build_sha256'] = 'c' * 64
        self.assertIn('stale_test', self.codes())

    def test_unreviewed_or_failed_not_closed(self):
        self.doc['entries'][0]['review'] = 'pending'
        self.doc['tests'][0]['status'] = 'failed'
        self.assertTrue({'review_pending', 'runtime_failed'} <= self.codes())

    def test_false_pass_without_evidence(self):
        del self.doc['entries'][0]['writeback_evidence']
        del self.doc['tests'][0]['evidence']
        self.assertTrue({'writeback_evidence', 'runtime_evidence'} <= self.codes())

    def test_partial_extraction_detected(self):
        self.doc['resources'][0]['extraction_complete'] = False
        self.assertIn('extraction_open', self.codes())

    def test_equal_strings_count_physical_occurrences(self):
        e = copy.deepcopy(self.doc['entries'][0]); e['id'] = 'e2'; e['locator'] = 'text:2'
        self.doc['entries'].append(e); self.doc['resources'][0]['expected_entries'] = 2
        counts = mod.audit(self.doc)['counts']
        self.assertEqual(counts['physical_entries'], 2)
        self.assertEqual(counts['unique_source_strings'], 1)

    def test_translated_entry_cannot_skip_writeback(self):
        self.doc['entries'][0]['writeback'] = 'not_applicable'
        self.assertIn('writeback_required', self.codes())

    def test_invalid_types_fail(self):
        for section, key, bad in [('scope', 'inventory_complete', 'true'),
                                  ('scope', 'build_sha256', 'short')]:
            doc = fixture(); doc[section][key] = bad
            with self.assertRaises(mod.InvalidLedger): mod.audit(doc)
        for bad in [None, [], {'schema_version': True}]:
            with self.assertRaises(mod.InvalidLedger): mod.audit(bad)

    def test_cli_is_read_only_and_returns_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / '中文 sample.json'
            for data, code in [(fixture(), 0), ({**fixture(), 'tests': []}, 1), ({}, 2)]:
                p.write_text(json.dumps(data), encoding='utf-8'); before = p.read_bytes()
                result = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
                self.assertEqual(result.returncode, code)
                json.loads(result.stdout if code != 2 else result.stderr)
                self.assertEqual(p.read_bytes(), before)
            p.write_text('{ broken')
            result = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
