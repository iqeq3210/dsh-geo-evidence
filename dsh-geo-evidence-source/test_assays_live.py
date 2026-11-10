"""Opt-in NCBI smoke test; no downloads or full sample-family inspection."""
import json
from pathlib import Path
from geo_plugin.core import Client, search

client = Client('.geo-cache')
Path('reports').mkdir(exist_ok=True)
report = []
for technology in ('chipseq', 'cuttag', 'atacseq'):
    result = search(client, disease='K562', technology=technology, limit=5, details=0)
    report.append({key: result[key] for key in ('technology', 'query', 'query_url', 'total_hits', 'accessions', 'errors')})
    if not result['accessions']:
        raise RuntimeError(f'No results for {technology}')
Path('reports/assay-smoke-test.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps([{'technology': r['technology'], 'hits': r['total_hits'], 'returned': len(r['accessions'])} for r in report]))
