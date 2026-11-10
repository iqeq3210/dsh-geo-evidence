import unittest
from geo_plugin.core import build_query, parse_soft, inspect, ASSAYS, normalize_technology


class CoreTests(unittest.TestCase):
    def test_assay_categories_and_aliases(self):
        for category in ASSAYS:
            with self.subTest(category=category):
                query = build_query('K562', technology=category)
                self.assertIn('gse[Entry Type]', query)
                self.assertIn('"K562"[All Fields]', query)
        self.assertEqual(normalize_technology('CUT&Tag'), 'cuttag')
        self.assertEqual(normalize_technology('ChIP-seq'), 'chipseq')
        self.assertEqual(normalize_technology('表达芯片'), 'array')

    def test_epigenomic_methods_do_not_require_expression_type(self):
        for technology in ('chipseq', 'cuttag', 'cutrun', 'atacseq', 'hic'):
            query = build_query('K562', technology=technology)
            self.assertNotIn('expression profiling', query)
            self.assertNotIn('[DataSet Type]', query)
        self.assertIn('"CUT&Tag"[All Fields]', build_query(technology='cuttag'))

    def test_target_tissue_custom_method_and_validation(self):
        query = build_query('K562', technology='any', target='H3K27ac', tissue='heart', method='PRO-seq')
        for value in ('H3K27ac', 'heart', 'PRO-seq'):
            self.assertIn(f'"{value}"[All Fields]', query)
        with self.assertRaises(ValueError):
            build_query(target='CTCF" OR mouse[Organism]')
        with self.assertRaises(ValueError):
            build_query(technology='made-up')

    def test_query_filters_and_expansion(self):
        query = build_query('心力衰竭')
        self.assertIn('ischaemic cardiomyopathy', query)
        self.assertIn('gse[Entry Type]', query)
        self.assertIn('Homo sapiens', query)
        self.assertNotIn('GSE55296', query)
        self.assertIn('expression profiling by array', build_query(technology='array'))

    def test_query_rejects_injected_operators(self):
        with self.assertRaises(ValueError):
            build_query('x" OR mouse[Organism]')

    def test_challenge_is_error_not_empty_study(self):
        with self.assertRaises(ValueError):
            parse_soft('<html>Checking your browser</html>')

    def test_mixed_assays_and_normalized_file(self):
        class Fixture:
            def get(self, _url):
                return '''^SERIES = GSE1
!Series_title = Heart failure
!Series_type = Non-coding RNA profiling by high throughput sequencing
!Series_sample_id = GSM1
!Series_sample_id = GSM2
!Series_supplementary_file = ftp://example/GSE1_FPKM.txt.gz
^SAMPLE = GSM1
!Sample_library_strategy = RNA-Seq
^SAMPLE = GSM2
!Sample_library_strategy = miRNA-Seq
'''
        result = inspect(Fixture(), 'GSE1', samples=True)
        self.assertEqual(result['gsm_count'], 2)
        self.assertEqual(result['library_strategy_counts'], {'RNA-Seq': 1, 'miRNA-Seq': 1})
        self.assertEqual(result['files'][0]['hint'], 'FPKM')
        self.assertFalse(result['files'][0]['verified_content'])
        self.assertTrue(any('donor' in x for x in result['cautions']))


if __name__ == '__main__':
    unittest.main()
