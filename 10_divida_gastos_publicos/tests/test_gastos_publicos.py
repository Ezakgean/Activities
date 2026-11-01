import csv
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
from pathlib import Path

import openpyxl
import pandas as pd

from app.gastos_publicos import DIMENSIONS, build_history, collect, collect_year, discover_resources, money, payment, process_file, sha256
from app.painel_gastos import grouped_data


class SpendingTests(unittest.TestCase):
    def workbook(self, path, rows):
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = '2026'
        headers = ['ID_ANO', 'ID_MES', *DIMENSIONS.values(), 'PAGAMENTOS_TOTAIS',
                   'DESPESAS_PAGAS', 'RESTOS_A_PAGAR_PAGOS']
        sheet.append(headers)
        for changes in rows:
            row = dict(ID_ANO=2026, ID_MES=1, ID_FUNCAO_PT=10, NO_FUNCAO_PT='SAUDE',
                       ID_SUBFUNCAO_PT='301', NO_SUBFUNCAO_PT='ATENCAO BASICA',
                       ORGAO_CODIGO='36000', ORGAO_DESCRICAO='MINISTERIO DA SAUDE',
                       ID_GRUPO_DESPESA_NADE='4', NO_GRUPO_DESPESA_NADE='INVESTIMENTOS',
                       PRIMARIA_FINANCEIRA='Primária', PAGAMENTOS_TOTAIS=120,
                       DESPESAS_PAGAS=100, RESTOS_A_PAGAR_PAGOS=20)
            row.update(changes)
            sheet.append([row.get(h) for h in headers])
        # Não importar subtotais como despesas adicionais.
        summary = book.create_sheet('Resumo')
        summary.append(['Total', 999999])
        book.save(path)
        book.close()

    def test_paid_amount_includes_arrears_only_once_and_keeps_adjustments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'base.xlsx'
            self.workbook(source, [{}, {'DESPESAS_PAGAS': -10, 'RESTOS_A_PAGAR_PAGOS': None, 'PAGAMENTOS_TOTAIS': -10},
                                   {'ID_MES': 2, 'DESPESAS_PAGAS': None, 'RESTOS_A_PAGAR_PAGOS': None, 'PAGAMENTOS_TOTAIS': None}])
            meta = process_file(source, 2026, root / 'out')
            self.assertEqual(meta['validacao']['totais_mensais_brl'], {'2026-01': '110.00'})
            self.assertEqual(meta['validacao']['linhas_sem_pagamento_informado'], 1)
            with (root / 'out/gastos_2026_categorias.csv').open(encoding='utf-8-sig') as f:
                records = list(csv.DictReader(f))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['valor_pago_brl'], '110.00')
            self.assertEqual(records[0]['subfuncao_codigo'], '301')
            # Segunda execução substitui o ano, sem duplicar registros.
            process_file(source, 2026, root / 'out')
            self.assertEqual(json.loads((root / 'out/gastos_2026_resumo.json').read_text())['validacao']['linhas_fonte'], 3)

    def test_invalid_file_preserves_previous_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'base.xlsx'
            self.workbook(source, [{}])
            process_file(source, 2026, root)
            before = (root / 'gastos_2026_categorias.csv').read_bytes()
            self.workbook(source, [{'ID_MES': 13}])
            with self.assertRaisesRegex(ValueError, 'mês inválido'):
                process_file(source, 2026, root)
            self.assertEqual((root / 'gastos_2026_categorias.csv').read_bytes(), before)

    def test_reconciliation_and_numbers(self):
        self.assertEqual(money('1.234,56'), Decimal('1234.56'))
        self.assertEqual(payment({'DESPESAS_PAGAS': 0}), Decimal(0))
        self.assertIsNone(payment({}))
        with self.assertRaises(ValueError):
            payment({'PAGAMENTOS_TOTAIS': 150, 'DESPESAS_PAGAS': 100, 'RESTOS_A_PAGAR_PAGOS': 20})
        with self.assertRaises(ValueError):
            money('NaN')

    def test_published_total_is_preserved_with_source_discrepancy_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'base.xlsx'
            self.workbook(source, [{'PAGAMENTOS_TOTAIS': 150}])
            result = process_file(source, 2026, root)
            self.assertEqual(result['validacao']['totais_mensais_brl']['2026-01'], '150.00')
            issues = result['validacao']['divergencias_componentes']
            self.assertEqual(issues[0]['soma_componentes_brl'], '120.00')
            self.assertEqual(issues[0]['diferenca_brl'], '30.00')

    def test_discovery_ignores_technical_notes(self):
        payload = {'success': True, 'result': {'resources': [
            {'name': 'Nota Técnica 2026', 'format': 'PDF'},
            {'name': 'Despesas e Transferências da União - 2026', 'format': 'XLSX', 'url': 'fonte'},
        ]}}
        self.assertEqual(list(discover_resources(payload)), [2026])

    def test_historical_headers_and_monthly_annual_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'base.xlsx'
            self.workbook(source, [{'ID_MES': m} for m in range(1, 13)])
            book = openpyxl.load_workbook(source)
            for cell in book.active[1]:
                if cell.value == 'PRIMARIA_FINANCEIRA':
                    cell.value = 'Primaria_Financeira'
            book.save(source); book.close()
            process_file(source, 2026, root)
            self.workbook(source, [{'ID_ANO': 2025, 'ID_MES': 7}])
            process_file(source, 2025, root)
            build_history(root)
            with (root / 'serie_gastos_anual.csv').open(encoding='utf-8-sig') as f:
                annual = list(csv.DictReader(f))
            self.assertEqual(annual[0]['ano_completo'], 'False')
            self.assertEqual(annual[0]['meses_disponiveis'], '1')
            self.assertEqual(annual[1]['ano_completo'], 'True')
            self.assertEqual(annual[1]['pagamentos_totais_brl'], '1440.00')
            self.assertEqual(annual[1]['investimentos_pagos_brl'], '1440.00')
            with (root / 'serie_gastos_mensal.csv').open(encoding='utf-8-sig') as f:
                self.assertEqual(len(list(csv.DictReader(f))), 13)

    def test_all_years_continues_after_failure_and_reports_it(self):
        payload = {'success': True, 'result': {'resources': [
            {'name': f'Despesas e Transferências da União - {year}', 'format': 'XLSX'} for year in [2025, 2026]
        ]}}
        with tempfile.TemporaryDirectory() as temp, patch('app.gastos_publicos.get_catalog', return_value=payload), \
                patch('app.gastos_publicos.collect_year', side_effect=[ValueError('Falha simulada'),
                      {'validacao': {'meses_na_fonte': [1, 2]}}]) as collector:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, '2025'):
                collect(input_dir=root, output=root, all_years=True, log=lambda _: None, workers=1)
            self.assertEqual([call.args[0] for call in collector.call_args_list], [2025, 2026])
            report = json.loads((root / 'relatorio_coleta_historica.json').read_text())
            self.assertEqual([r['status'] for r in report], ['falhou', 'concluido'])

    def test_unchanged_year_reuses_processed_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'despesas_2026.xlsx'
            self.workbook(source, [{}])
            resource = {'id': 'id', 'url': 'url', 'last_modified': 'data', 'hash': ''}
            source.with_suffix('.fonte.json').write_text(json.dumps({'recurso': resource, 'sha256': sha256(source)}))
            process_file(source, 2026, root, resource)
            client = Mock()
            with patch('app.gastos_publicos.process_file') as process:
                result = collect_year(2026, {2026: resource}, client, root, root, False, lambda _: None)
            client.get.assert_not_called()
            process.assert_not_called()
            self.assertEqual(result['ano'], 2026)

    def test_investment_filter_does_not_include_personnel_or_other_months(self):
        data = pd.DataFrame([
            {'ano': '2026', 'periodo': '2026-01', 'grupo_codigo': '4', 'funcao_codigo': '10', 'funcao': 'Saúde', 'valor_pago_brl': 100},
            {'ano': '2026', 'periodo': '2026-01', 'grupo_codigo': '1', 'funcao_codigo': '10', 'funcao': 'Saúde', 'valor_pago_brl': 900},
            {'ano': '2026', 'periodo': '2026-02', 'grupo_codigo': '4', 'funcao_codigo': '10', 'funcao': 'Saúde', 'valor_pago_brl': 300},
        ])
        self.assertEqual(grouped_data(data, '2026', '2026-01', 'funcao', True).valor_pago_brl.sum(), 100)
        self.assertEqual(grouped_data(data, '2026', 'Acumulado disponível', 'funcao', False).valor_pago_brl.sum(), 1300)


if __name__ == '__main__':
    unittest.main()
