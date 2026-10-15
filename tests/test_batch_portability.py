from __future__ import annotations

import csv
import json
import os
import queue
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from norway_company_agent.pipeline import _collect, failed_profile
from norway_company_agent.batch import read_organisation_inputs


class BatchPortabilityTests(unittest.TestCase):
    def test_unrecognized_json_shape_cannot_silently_become_an_empty_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'batch.json'
            for body in [{'companies':['123456789']},{'organisation_numbers':'123456789'},{}]:
                path.write_text(json.dumps(body))
                with self.assertRaises(ValueError):read_organisation_inputs(path)
            path.write_text(json.dumps({'organisation_number':'123456789'}))
            self.assertEqual(read_organisation_inputs(path),[{'organisation_number':'123456789'}])

    def test_real_evaluator_handles_unseen_out_of_order_batch_larger_than_100_without_personal_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            orgs = [str(100000000+i) for i in range(103)][::-1]
            batch = root/'official-input.jsonl'
            batch.write_text(''.join(json.dumps({'organisation_number':org, 'name':'Untrusted input name'})+'\n' for org in orgs))
            bulk = root/'frozen-registry.csv'
            with bulk.open('w') as handle:
                writer=csv.writer(handle);writer.writerow(['organisasjonsnummer','navn','organisasjonsform.kode'])
                for org in orgs[:-1]:writer.writerow([org,'Registry '+org,'AS'])
            command = [sys.executable,str(ROOT/'scripts/evaluate_signalpost.py'),
                '--organisations',str(batch),'--bulk',str(bulk),'--output-dir',str(root/'run'),
                '--run-id','unseen-batch','--modules','registry','--workers','4',
                '--deadline-seconds','30','--evaluator-timeout-seconds','40','--nav-jobs']
            result = subprocess.run(command,env={**os.environ,'NAV_API_TOKEN':'','TAVILY_API_KEY':'','BRAVE_SEARCH_API_KEY':''},
                                    capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stderr)
            rows=list(map(json.loads,(root/'run/envelopes.jsonl').read_text().splitlines()))
            self.assertEqual([r['organisation_number'] for r in rows],orgs)
            self.assertEqual(len(rows),103)
            self.assertEqual(rows[0]['legal_identity']['name'],'Registry '+orgs[0])
            self.assertIsNone(rows[-1]['legal_identity']['name'])
            report=json.loads((root/'run/report.json').read_text())
            self.assertEqual(report['operations']['requests'],0)
            self.assertEqual(report['operations']['third_party_cost_usd'],0)
            self.assertFalse(report['shared_sources']['nav_jobs']['scan_complete'])
            self.assertTrue(json.loads((root/'run/evaluator-status.json').read_text())['package_accepted'])

    def test_nav_is_scanned_once_for_the_batch_and_survives_other_module_failure(self):
        profiles=[{'organisation_number':str(100000000+i),'name':'Company '+str(i),'evidence':{}} for i in range(3)]
        records={p['organisation_number']:{'status':'source_error','note':'Partial source'} for p in profiles}
        config={'nav_jobs':True,'snapshot_dir':tempfile.gettempdir(), 'deadline':time.monotonic()+5,
                'nav_timeout':1,'nav_max_requests':10,'nav_max_pages':1,'nav_max_details':1,
                'nav_lookback_days':184,'modules':['registry','nav_jobs']}
        output=queue.Queue()
        def worker(profile,config):return failed_profile(profile,config['modules'],'Other source failed')
        with patch('norway_company_agent.pipeline.collect_jobs',return_value=(records,{'metrics':{},'scan_complete':False})) as scan:
            _collect(profiles,config,3,output,worker)
        self.assertEqual(scan.call_count,1)
        self.assertEqual(output.get_nowait()['_batch_source'],'nav_jobs')
        results=[output.get_nowait() for _ in profiles]
        self.assertTrue(all(r['evidence']['nav_jobs']['note']=='Partial source' for r in results))


if __name__=='__main__':
    unittest.main()
