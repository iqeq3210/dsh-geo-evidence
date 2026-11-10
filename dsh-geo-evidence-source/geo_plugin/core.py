import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ALIASES = {
    "心力衰竭": ["heart failure", "failing heart", "dilated cardiomyopathy", "ischemic cardiomyopathy", "ischaemic cardiomyopathy"],
    "heart failure": ["heart failure", "failing heart", "dilated cardiomyopathy", "ischemic cardiomyopathy", "ischaemic cardiomyopathy"],
}

# GEO study types are broad: CUT&Tag and ATAC may share a type with ChIP-seq,
# or be deposited as Other. Method keywords provide candidate recall;
# per-sample protocols are still needed to verify mixed-method studies.
ASSAYS = {
    'rnaseq': {'type': 'expression profiling by high throughput sequencing', 'terms': []},
    'array': {'type': 'expression profiling by array', 'terms': []},
    'chipseq': {'terms': ['ChIP-seq', 'ChIP seq', 'ChIPseq', 'chromatin immunoprecipitation sequencing']},
    'cuttag': {'terms': ['CUT&Tag', 'CUT and Tag', 'CUT-Tag', 'CUTTag', 'Cleavage Under Targets and Tagmentation']},
    'cutrun': {'terms': ['CUT&RUN', 'CUT and RUN', 'CUT-Run', 'CUTRun', 'Cleavage Under Targets and Release Using Nuclease']},
    'atacseq': {'terms': ['ATAC-seq', 'ATAC seq', 'ATACseq']},
    'scrnaseq': {'type': 'expression profiling by high throughput sequencing', 'terms': ['single-cell RNA', 'single cell RNA', 'scRNA-seq', 'scRNAseq']},
    'snrnaseq': {'type': 'expression profiling by high throughput sequencing', 'terms': ['single-nucleus RNA', 'single nucleus RNA', 'snRNA-seq', 'snRNAseq']},
    'hic': {'terms': ['Hi-C', 'HiC sequencing', 'chromosome conformation capture']},
    'methylation': {'type': 'methylation profiling by high throughput sequencing', 'terms': []},
    'methylation_array': {'type': 'methylation profiling by array', 'terms': []},
    'any': {'terms': []},
}
ASSAY_ALIASES = {
    'rna-seq': 'rnaseq', 'chip': 'chipseq', 'chip-seq': 'chipseq',
    'cut&tag': 'cuttag', 'cut-tag': 'cuttag', 'cut&run': 'cutrun', 'cut-run': 'cutrun',
    'atac-seq': 'atacseq', 'scrna-seq': 'scrnaseq', 'snrna-seq': 'snrnaseq',
    'hi-c': 'hic', '表达芯片': 'array', '转录组': 'rnaseq', '全部': 'any',
}


def normalize_technology(technology):
    key = technology.strip().lower()
    key = ASSAY_ALIASES.get(key, key)
    if key not in ASSAYS:
        raise ValueError('technology must be one of: ' + ', '.join(ASSAYS))
    return key


def term_clause(terms):
    return '(' + ' OR '.join(f'"{term}"[All Fields]' for term in terms) + ')'


class Client:
    def __init__(self, cache=None):
        self.cache = Path(cache) if cache else None
        self.last_request = 0

    def get(self, url):
        target = self.cache / (hashlib.sha256(url.encode()).hexdigest() + '.txt') if self.cache else None
        if target and target.exists() and time.time() - target.stat().st_mtime < 86400:
            return target.read_text(encoding='utf-8')
        for attempt in range(4):
            time.sleep(max(0, .4 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'DSH-GEO-Evidence/1.0'})
                with urllib.request.urlopen(request, timeout=40) as response:
                    text = response.read(20_000_000).decode('utf-8')
                if target:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(text, encoding='utf-8')
                return text
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)


def parse_soft(text):
    records = []
    current = None
    for line in text.splitlines():
        if line.startswith('^') and ' = ' in line:
            kind, accession = line[1:].split(' = ', 1)
            current = {'kind': kind, 'accession': accession, 'fields': {}}
            records.append(current)
        elif current is not None and line.startswith('!') and ' = ' in line:
            key, value = line[1:].split(' = ', 1)
            current['fields'].setdefault(key, []).append(value)
    if not records:
        raise ValueError('NCBI did not return SOFT records (possible service error or browser challenge)')
    return records


def build_query(disease='心力衰竭', organism='Homo sapiens', technology='rnaseq', target=None, tissue=None, method=None):
    terms = ALIASES.get(disease.lower().strip(), [disease.strip()])
    extras = [value for value in (target, tissue, method) if value is not None]
    if not all(terms) or not organism.strip() or any(not value.strip() or any(c in value for c in '"[]\r\n') for value in terms + [organism] + extras):
        raise ValueError('Use plain disease/organism terms without query operators')
    assay = ASSAYS[normalize_technology(technology)]
    clauses = [term_clause(terms), f'"{organism}"[Organism]']
    if assay.get('type'):
        clauses.append(f'"{assay["type"]}"[DataSet Type]')
    if assay['terms']:
        clauses.append(term_clause(assay['terms']))
    clauses.extend(f'"{value}"[All Fields]' for value in extras)
    clauses.append('gse[Entry Type]')
    return ' AND '.join(clauses)


def sample_summary(record):
    f = record['fields']
    return {'accession': record['accession'], 'title': f.get('Sample_title', []),
            'source': f.get('Sample_source_name_ch1', []), 'characteristics': f.get('Sample_characteristics_ch1', []),
            'organism': f.get('Sample_organism_ch1', []), 'library_strategy': f.get('Sample_library_strategy', []),
            'processing': f.get('Sample_data_processing', []), 'relations': f.get('Sample_relation', []),
            'extraction_protocol': f.get('Sample_extract_protocol_ch1', []),
            'treatment_protocol': f.get('Sample_treatment_protocol_ch1', [])}


def inspect(client, accession, samples=False):
    if not re.fullmatch(r'GSE\d+', accession):
        raise ValueError('Expected a GSE accession')
    url = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?' + urllib.parse.urlencode(
        {'acc': accession, 'targ': 'all' if samples else 'self', 'form': 'text', 'view': 'full'})
    records = parse_soft(client.get(url))
    series = next(r for r in records if r['kind'] == 'SERIES' and r['accession'] == accession)
    f = series['fields']
    text = ' '.join(f.get('Series_title', []) + f.get('Series_summary', []) + f.get('Series_overall_design', []))
    files = [v for v in f.get('Series_supplementary_file', []) if v.upper() != 'NONE']
    lowered = text.lower()
    modality = 'single_cell_or_nucleus' if re.search(r'single[ -](cell|nucle)|snrna|scrna', lowered) else 'bulk_or_unspecified'
    file_hints = [{'url': u, 'hint': ('FPKM' if 'fpkm' in u.lower() else 'TPM' if 'tpm' in u.lower() else 'RPKM' if 'rpkm' in u.lower() else 'counts_candidate' if 'count' in u.lower() else 'unknown'), 'verified_content': False} for u in files]
    gsm = [sample_summary(r) for r in records if r['kind'] == 'SAMPLE']
    hints = []
    if any(x['hint'] in ['FPKM', 'TPM', 'RPKM'] for x in file_hints):
        hints.append('Normalized expression file name detected; do not treat as raw counts.')
    if any('non-coding' in x.lower() for x in f.get('Series_type', [])):
        hints.append('Multiple RNA assay types may share donors; GSM count is not donor count.')
    control = bool(re.search(r'control|non[ -]failing|healthy|donor', lowered))
    cardiac = bool(re.search(r'heart|ventric|myocardi|cardiac', lowered))
    return {'accession': accession, 'url': f'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}',
            'evidence_url': url, 'title': f.get('Series_title', [''])[0], 'summary': f.get('Series_summary', []),
            'overall_design': f.get('Series_overall_design', []), 'types': f.get('Series_type', []),
            'platforms': f.get('Series_platform_id', []), 'gsm_count': len(f.get('Series_sample_id', [])),
            'gsm_ids': f.get('Series_sample_id', []), 'relations': f.get('Series_relation', []),
            'files': file_hints, 'modality': modality, 'control_mention': control, 'cardiac_mention': cardiac,
            'score': 3 * control + 3 * cardiac + bool(files) + (modality == 'bulk_or_unspecified'),
            'samples': gsm, 'library_strategy_counts': dict(Counter(s for g in gsm for s in g['library_strategy'])),
            'cautions': hints + ['Donor independence and file content require verification; metadata is not an analysis-ready matrix.']}


def search(client, disease='心力衰竭', organism='Homo sapiens', technology='rnaseq', limit=100, details=20, target=None, tissue=None, method=None):
    if not 1 <= limit <= 500 or not 0 <= details <= limit:
        raise ValueError('Require 1 <= limit <= 500 and 0 <= details <= limit')
    technology = normalize_technology(technology)
    query = build_query(disease, organism, technology, target, tissue, method)
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?' + urllib.parse.urlencode(
        {'db': 'gds', 'term': query, 'retmode': 'json', 'retmax': limit, 'sort': 'relevance', 'tool': 'dsh_geo_evidence'})
    result = json.loads(client.get(url))['esearchresult']
    if result.get('errorlist') or result.get('ERROR'):
        raise ValueError(str(result))
    ids = result['idlist']
    accessions = []
    candidates = []
    for offset in range(0, len(ids), 100):
        summary_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?' + urllib.parse.urlencode(
            {'db': 'gds', 'id': ','.join(ids[offset:offset+100]), 'retmode': 'xml'})
        root = ET.fromstring(client.get(summary_url))
        for doc in root.findall('.//DocSum'):
            items = {x.attrib.get('Name'): x.text for x in doc.findall('Item')}
            acc = items.get('Accession', '')
            if re.fullmatch(r'GSE\d+', acc) and acc not in accessions:
                accessions.append(acc)
                title = items.get('title', '') or ''
                summary = items.get('summary', '') or ''
                content = (title + ' ' + summary).lower()
                score = 5 * bool(re.search(r'heart failure|failing heart', title.lower()))
                score += 3 * bool(re.search(r'left ventric|heart tissue|human heart', content))
                score += 4 * bool(re.search(r'left ventric|human heart|cardiac tissue', title.lower()))
                score += 2 * bool(re.search(r'control|non[ -]failing|healthy donor', content))
                score -= 6 * bool(re.search(r'single[ -](cell|nucle)|snrna|scrna|ipsc|induced pluripotent', content))
                score -= 5 * bool(re.search(r'skeletal muscle|peripheral blood|circular rna|microrna|mirna|cell therapy', title.lower()))
                if technology not in ('rnaseq', 'array'):
                    # Epigenomic assays are not ranked as bulk heart transcriptomes.
                    score = sum(5 for term in ASSAYS[technology]['terms'] if term.lower() in title.lower())
                    score += sum(3 for value in (target, tissue, method) if value and value.lower() in title.lower())
                candidates.append({'accession': acc, 'title': title, 'summary': summary, 'screen_score': score})
    candidates.sort(key=lambda x: x['screen_score'], reverse=True)
    accessions = [c['accession'] for c in candidates]
    studies, errors = [], []
    for acc in accessions[:details]:
        try:
            studies.append(inspect(client, acc))
        except Exception as exc:
            errors.append({'accession': acc, 'error': str(exc)})
    return {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'query': query, 'query_url': url,
            'technology': technology, 'target': target, 'tissue': tissue, 'method': method,
            'assay_caution': 'Method keyword matches identify candidate studies, not verified assay-specific samples. Mixed-method Series may contain other assays; inspect sample protocols and controls.',
            'total_hits': int(result['count']), 'truncated': int(result['count']) > len(ids),
            'accessions': accessions, 'studies': sorted(studies, key=lambda x: x['score'], reverse=True) if technology in ('rnaseq', 'array') else studies,
            'candidates': [{k: v for k, v in c.items() if k != 'summary'} for c in candidates[:50]],
            'candidate_preview_limit': 50,
            'detail_limit': details, 'errors': errors, 'ranking': 'Heuristic metadata relevance, not quality or statistical power.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--request', required=True, help='JSON object: action search or inspect and arguments')
    p.add_argument('--output')
    p.add_argument('--cache', default=str(Path(__file__).resolve().parents[1] / '.geo-cache'))
    args = p.parse_args()
    request = json.loads(args.request)
    action = request.pop('action', 'search')
    client = Client(args.cache)
    if action == 'search':
        result = search(client, **request)
    elif action == 'inspect':
        result = inspect(client, **request)
    else:
        raise ValueError('Unknown action')
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
    else:
        print(text)


if __name__ == '__main__':
    main()
