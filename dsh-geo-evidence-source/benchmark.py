"""Live benchmark. No reference accessions are passed to the search function."""
import json
from pathlib import Path
from geo_plugin.core import Client, search, inspect

root = Path(__file__).resolve().parent
(root / 'reports').mkdir(exist_ok=True)
client = Client(root / '.geo-cache')
reference = json.loads((root / 'reference/heart_failure.json').read_text(encoding='utf-8'))
result = search(client, disease='心力衰竭', limit=500, details=12)
(root / 'reports/search.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
checks = []
for expected in reference['positives']:
    accession = expected['accession']
    found = accession in result['accessions']
    observed = inspect(client, accession, samples=True)
    (root / f'reports/{accession}.json').write_text(json.dumps(observed, ensure_ascii=False, indent=2), encoding='utf-8')
    checks.append({'accession': accession, 'retrieved_by_search': found,
                   'search_rank': result['accessions'].index(accession) + 1 if found else None,
                   'gsm_count_matches': observed['gsm_count'] == expected['gsm_count'],
                   'observed_gsm_count': observed['gsm_count'],
                   'sample_records_loaded': len(observed['samples']),
                   'strategy_counts': observed['library_strategy_counts'],
                   'design_evidence': observed['overall_design'],
                   'files': observed['files']})
negative = {acc: acc not in result['accessions'] for acc in reference['negative_for_rnaseq']}
report = {'positive_control_recall': sum(c['retrieved_by_search'] for c in checks) / len(checks),
          'checks': checks, 'array_excluded': negative,
          'total_hits': result['total_hits'], 'retrieved': len(result['accessions']),
          'truncated': result['truncated'], 'detail_errors': result['errors'],
          'limitations': 'Three known positive controls only; not exhaustive recall or measured precision. Ranking was developed against this known reference set, not a blind benchmark. Direct inspections test metadata separately from search recall. Native DSH activation still needs verification.'}
(root / 'reports/benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True, indent=2))
if not all(c['retrieved_by_search'] and c['gsm_count_matches'] and c['sample_records_loaded'] == c['observed_gsm_count'] for c in checks) or not all(negative.values()):
    raise SystemExit(1)
