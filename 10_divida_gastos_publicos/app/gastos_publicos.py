"""Coleta despesas pagas da União no catálogo oficial do Tesouro Transparente."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from tempfile import TemporaryDirectory

import openpyxl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / 'data/input/gastos_publicos'
OUTPUT = BASE / 'data/output/gastos_publicos'
DATASET = 'despesas-e-transferencias-totais'
SOURCE = f'https://www.tesourotransparente.gov.br/ckan/dataset/{DATASET}'
API = 'https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show'
PARSER_VERSION = 2
DIMENSIONS = {
    'funcao_codigo': 'ID_FUNCAO_PT', 'funcao': 'NO_FUNCAO_PT',
    'subfuncao_codigo': 'ID_SUBFUNCAO_PT', 'subfuncao': 'NO_SUBFUNCAO_PT',
    'orgao_codigo': 'ORGAO_CODIGO', 'orgao': 'ORGAO_DESCRICAO',
    'grupo_codigo': 'ID_GRUPO_DESPESA_NADE', 'grupo': 'NO_GRUPO_DESPESA_NADE',
    'natureza': 'PRIMARIA_FINANCEIRA',
}
REQUIRED = {'ID_ANO', 'ID_MES', 'PAGAMENTOS_TOTAIS', *DIMENSIONS.values()}
NOTE = ('Pagamentos da União em R$ correntes, incluindo restos a pagar pagos, transferências e despesas '
        'financeiras da base. Não é o total consolidado de União, estados e municípios. '
        'Investimentos são os pagamentos classificados no grupo de natureza de despesa 4; '
        'gasto em saúde ou educação não é sinônimo de investimento. Meses não publicados não são zeros.')


def session() -> requests.Session:
    client = requests.Session()
    client.headers['User-Agent'] = 'tesouro-gastos-collector/1.0'
    client.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1,
                 status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET'])))
    return client


def discover_resources(payload: dict) -> dict[int, dict]:
    if payload.get('success') is not True:
        raise ValueError('O catálogo do Tesouro não retornou sucesso.')
    resources = {}
    for item in payload['result']['resources']:
        match = re.fullmatch(r'Despesas e Transferências da União\s*-\s*(\d{4})', item.get('name', ''))
        if match and item.get('format', '').upper() == 'XLSX':
            year = int(match[1])
            if year in resources:
                raise ValueError(f'Mais de uma planilha para {year}; revise o catálogo.')
            resources[year] = item
    if not resources:
        raise ValueError('Nenhuma planilha anual reconhecida no catálogo do Tesouro.')
    return resources


def get_catalog(client: requests.Session) -> dict:
    response = client.get(API, params={'id': DATASET}, timeout=(15, 90))
    response.raise_for_status()
    return response.json()


def money(value) -> Decimal | None:
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('Valor monetário booleano inválido.')
    text = str(value).strip()
    if ',' in text:
        text = text.replace('.', '').replace(',', '.')
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f'Valor monetário inválido: {value!r}') from exc
    if not result.is_finite():
        raise ValueError(f'Valor monetário não finito: {value!r}')
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class PaymentMismatch(ValueError):
    def __init__(self, total: Decimal, components: Decimal):
        super().__init__('Pagamentos totais divergem de despesas pagas + restos a pagar pagos.')
        self.total = total
        self.components = components


def payment(row: dict) -> Decimal | None:
    total = money(row.get('PAGAMENTOS_TOTAIS'))
    paid = money(row.get('DESPESAS_PAGAS'))
    arrears = money(row.get('RESTOS_A_PAGAR_PAGOS'))
    if paid is not None or arrears is not None:
        components = (paid or Decimal(0)) + (arrears or Decimal(0))
        if total is None:
            return components
        if abs(total - components) > Decimal('0.02'):
            raise PaymentMismatch(total, components)
    return total


def code(value) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def normalize_header(value) -> str:
    text = unicodedata.normalize('NFKD', str(value or '').strip())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'\s+', '_', text).upper()


def parse_workbook(path: Path, year: int, detail_path: Path) -> tuple[list[dict], dict]:
    totals = defaultdict(Decimal)
    monthly = defaultdict(Decimal)
    seen_months = set()
    mismatches = []
    counts = {'linhas_fonte': 0, 'linhas_sem_pagamento_informado': 0, 'linhas_com_pagamento': 0}
    with path.open('rb') as source:
        book = openpyxl.load_workbook(source, read_only=True, data_only=True)
        try:
            candidates = []
            for sheet in book:
                header = tuple(normalize_header(v) for v in next(sheet.iter_rows(max_row=1, values_only=True), ()))
                if REQUIRED <= set(header):
                    candidates.append((sheet, header))
            if len(candidates) != 1:
                raise ValueError('Esperada uma aba de dados com ID_ANO, ID_MES, PAGAMENTOS_TOTAIS e classificações. '
                                 'Formato não reconhecido; nenhuma saída foi substituída.')
            sheet, header = candidates[0]
            fields = ['periodo', *DIMENSIONS, 'programa_codigo', 'programa', 'acao_codigo', 'acao',
                      'categoria_rtn', 'valor_pago_brl']
            with detail_path.open('w', encoding='utf-8-sig', newline='') as target:
                writer = csv.DictWriter(target, fieldnames=fields)
                writer.writeheader()
                for index, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
                    if all(v is None for v in values):
                        continue
                    row = dict(zip(header, values))
                    try:
                        row_year = int(code(row['ID_ANO']))
                        month = int(code(row['ID_MES']))
                        if row_year != year or not 1 <= month <= 12:
                            raise ValueError('Competência fora do ano solicitado ou mês inválido.')
                        try:
                            value = payment(row)
                        except PaymentMismatch as exc:
                            # A coluna de total é o valor oficial publicado. Não substituí-la
                            # por um recálculo quando a própria fonte tem divergências.
                            value = exc.total
                            mismatches.append({'linha': index, 'periodo': f'{year}-{month:02d}',
                                               'total_publicado_brl': str(exc.total),
                                               'soma_componentes_brl': str(exc.components),
                                               'diferenca_brl': str(exc.total - exc.components)})
                    except (ValueError, TypeError) as exc:
                        raise ValueError(f'Aba {sheet.title}, linha {index}: {exc}') from exc
                    counts['linhas_fonte'] += 1
                    seen_months.add(month)
                    if value is None:
                        counts['linhas_sem_pagamento_informado'] += 1
                        continue
                    counts['linhas_com_pagamento'] += 1
                    period = f'{year}-{month:02d}'
                    dimensions = tuple(code(row.get(column)) for column in DIMENSIONS.values())
                    totals[(period, *dimensions)] += value
                    monthly[period] += value
                    record = dict(zip(['periodo', *DIMENSIONS], (period, *dimensions)))
                    record.update(programa_codigo=code(row.get('ID_PROGRAMA_PT')), programa=code(row.get('NO_PROGRAMA_PT')),
                                  acao_codigo=code(row.get('ACAO')), acao=code(row.get('NO_ACAO')),
                                  categoria_rtn=code(row.get('CATEGORIA_RTN')), valor_pago_brl=str(value))
                    writer.writerow(record)
            if not counts['linhas_com_pagamento']:
                raise ValueError('Nenhum pagamento informado na planilha.')
            records = []
            for key, value in sorted(totals.items()):
                records.append({**dict(zip(['periodo', *DIMENSIONS], key)), 'valor_pago_brl': str(value)})
            return records, {**counts, 'aba': sheet.title, 'meses_na_fonte': sorted(seen_months),
                             'divergencias_componentes': mismatches,
                             'totais_mensais_brl': {k: str(v) for k, v in sorted(monthly.items())}}
        finally:
            book.close()


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def process_file(path: Path, year: int, output: Path = OUTPUT, resource: dict | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='gastos_', dir=output) as temp:
        stage = Path(temp)
        detail = stage / f'gastos_{year}_detalhados.csv'
        records, validation = parse_workbook(path, year, detail)
        categories = stage / f'gastos_{year}_categorias.csv'
        with categories.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['periodo', *DIMENSIONS, 'valor_pago_brl'])
            writer.writeheader()
            writer.writerows(records)
        metadata = {'ano': year, 'coletado_em': datetime.now(UTC).isoformat(), 'fonte': SOURCE,
                    'versao_extrator': PARSER_VERSION,
                    'arquivo_origem': path.name, 'sha256': sha256(path), 'unidade': 'BRL corrente',
                    'metodologia': NOTE, 'recurso': resource, 'validacao': validation}
        summary = stage / f'gastos_{year}_resumo.json'
        summary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        # Só publica após ler e validar a planilha inteira.
        for file in (detail, categories, summary):
            file.replace(output / file.name)
    return metadata


def collect_year(year, resources, client, input_dir, output, refresh, log):
    resource = resources[year]
    path = input_dir / f'despesas_{year}.xlsx'
    provenance = path.with_suffix('.fonte.json')
    cached = json.loads(provenance.read_text()) if provenance.exists() else {}
    fingerprint = {k: resource.get(k) for k in ('id', 'url', 'last_modified', 'hash')}
    if refresh or not path.exists() or cached.get('recurso') != fingerprint or cached.get('sha256') != sha256(path):
        log(f'{year}: baixando planilha oficial...')
        with TemporaryDirectory(dir=input_dir) as temp:
            downloaded = Path(temp) / 'download.xlsx'
            with client.get(resource['url'], stream=True, timeout=(15, 120)) as response:
                response.raise_for_status()
                with downloaded.open('wb') as stream:
                    for chunk in response.iter_content(1024 * 1024):
                        stream.write(chunk)
            with downloaded.open('rb') as stream:
                signature = stream.read(4)
            if signature != b'PK\x03\x04':
                raise ValueError('O download não retornou uma planilha XLSX.')
            downloaded.replace(path)
        provenance.write_text(json.dumps({'recurso': fingerprint, 'sha256': sha256(path)}, indent=2), encoding='utf-8')
    previous = output / f'gastos_{year}_resumo.json'
    if not refresh and previous.exists():
        metadata = json.loads(previous.read_text(encoding='utf-8'))
        if (metadata.get('versao_extrator') == PARSER_VERSION
                and metadata.get('sha256') == sha256(path)
                and all((output / f'gastos_{year}_{suffix}.csv').exists() for suffix in ('categorias', 'detalhados'))):
            log(f'{year}: já processado; usando cache validado.')
            return metadata
    log(f'{year}: validando e agrupando pagamentos...')
    result = process_file(path, year, output, resource)
    log(f'{year}: concluído — {result["validacao"]["linhas_com_pagamento"]} registros com pagamento.')
    return result


def build_history(output: Path = OUTPUT) -> None:
    """Consolida meses e anos sem tratar anos incompletos como fechados."""
    monthly = defaultdict(lambda: [Decimal(0), Decimal(0), Decimal(0)])
    for path in sorted(output.glob('gastos_????_categorias.csv')):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                values = monthly[row['periodo']]
                value = Decimal(row['valor_pago_brl'])
                values[0] += value
                if row['grupo_codigo'] == '4':
                    values[1] += value
                if row['natureza'].casefold() == 'primária':
                    values[2] += value
    annual = defaultdict(lambda: [set(), Decimal(0), Decimal(0), Decimal(0)])
    rows = []
    for period, values in sorted(monthly.items()):
        rows.append([period, *map(str, values)])
        year = annual[period[:4]]
        year[0].add(int(period[-2:]))
        for i, value in enumerate(values, 1):
            year[i] += value
    fields = ['pagamentos_totais_brl', 'investimentos_pagos_brl', 'pagamentos_classificados_primarios_brl']
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as temp:
        for filename, headers, records in [
            ('serie_gastos_mensal.csv', ['periodo', *fields], rows),
            ('serie_gastos_anual.csv', ['ano', 'meses_disponiveis', 'ano_completo', *fields],
             [[year, len(values[0]), values[0] == set(range(1, 13)), *map(str, values[1:])]
              for year, values in sorted(annual.items())]),
        ]:
            path = Path(temp) / filename
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream); writer.writerow(headers); writer.writerows(records)
            path.replace(output / filename)


def _collect_year_worker(year, resource, input_dir, output, refresh):
    # Cada processo escreve exclusivamente os arquivos do seu ano.
    with session() as client:
        return collect_year(year, {year: resource}, client, input_dir, output, refresh, lambda _: None)


def collect(years: list[int] | None = None, input_dir: Path = INPUT, output: Path = OUTPUT,
            refresh: bool = False, log=print, all_years: bool = False, workers: int = 3) -> list[dict]:
    if not 1 <= workers <= 8:
        raise ValueError('Use entre 1 e 8 processos.')
    if years is not None and all_years:
        raise ValueError('Informe anos específicos ou todos os anos, não ambos.')
    input_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    results, report = [], []
    with session() as client:
        catalog = get_catalog(client)
        resources = discover_resources(catalog)
        selected = sorted(set(resources if all_years else years or [max(resources)]))
        missing = set(selected) - resources.keys()
        if missing:
            raise ValueError(f'Anos não disponíveis no catálogo: {sorted(missing)}')
        (input_dir / 'catalogo.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
        def record_result(year, result=None, error=None):
            if error is not None:
                report.append({'ano': year, 'status': 'falhou', 'erro': str(error)})
                log(f'{year}: falhou — {error}. Continuando os demais anos.')
            else:
                results.append(result)
                mismatch_count = len(result['validacao'].get('divergencias_componentes', []))
                report.append({'ano': year, 'status': 'concluido', 'meses': result['validacao']['meses_na_fonte'],
                               'divergencias_componentes': mismatch_count})
                if mismatch_count:
                    log(f'{year}: {mismatch_count} divergências na fonte; totais publicados preservados e registrados no resumo.')
                log(f'[{len(report)}/{len(selected)}] {year}: concluído.')
            (output / 'relatorio_coleta_historica.json').write_text(
                json.dumps(sorted(report, key=lambda r: r['ano']), ensure_ascii=False, indent=2), encoding='utf-8')

        if workers == 1 or len(selected) == 1:
            for year in selected:
                try:
                    result = collect_year(year, resources, client, input_dir, output, refresh, log)
                except Exception as exc:
                    record_result(year, error=exc)
                else:
                    record_result(year, result=result)
        else:
            log(f'Processando {len(selected)} anos com até {workers} processos; arquivos já validados serão reaproveitados.')
            # spawn evita herdar o estado do Tk quando a coleta parte do painel.
            with ProcessPoolExecutor(max_workers=workers, mp_context=get_context('spawn')) as pool:
                futures = {pool.submit(_collect_year_worker, year, resources[year], input_dir, output, refresh): year
                           for year in selected}
                for future in as_completed(futures):
                    year = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        record_result(year, error=exc)
                    else:
                        record_result(year, result=result)
    build_history(output)
    failed = [r['ano'] for r in report if r['status'] == 'falhou']
    if failed:
        raise ValueError(f'Falha nos anos {failed}. Os demais foram preservados. Consulte relatorio_coleta_historica.json.')
    return results


def main():
    parser = argparse.ArgumentParser(description='Coleta gastos pagos da União por categoria no Tesouro Transparente.')
    parser.add_argument('--anos', type=int, nargs='+', help='Anos desejados; padrão: último ano do catálogo.')
    parser.add_argument('--processos', type=int, default=3, help='Processos de coleta (1 a 8); padrão: 3.')
    parser.add_argument('--todos-anos', action='store_true', help='Coleta todos os anos oferecidos pelo Tesouro.')
    parser.add_argument('--inicio', type=int, help='Primeiro ano do intervalo; exige --fim.')
    parser.add_argument('--fim', type=int, help='Último ano do intervalo; exige --inicio.')
    parser.add_argument('--listar-anos', action='store_true')
    parser.add_argument('--atualizar', action='store_true', help='Baixa novamente mesmo com cache válido.')
    parser.add_argument('--entrada', type=Path, default=INPUT)
    parser.add_argument('--saida', type=Path, default=OUTPUT)
    parser.add_argument('--arquivo', type=Path, help='Processa uma planilha local sem rede; exige um ano em --anos.')
    args = parser.parse_args()
    if (args.inicio is None) != (args.fim is None):
        parser.error('Informe --inicio e --fim juntos.')
    if args.inicio is not None:
        if args.anos or args.todos_anos or args.inicio > args.fim:
            parser.error('Intervalo inválido ou combinado com outra seleção de anos.')
        args.anos = list(range(args.inicio, args.fim + 1))
    if args.todos_anos and (args.anos or args.arquivo):
        parser.error('--todos-anos não pode ser combinado com --anos ou --arquivo.')
    if args.listar_anos:
        with session() as client:
            print('Anos disponíveis:', ', '.join(map(str, sorted(discover_resources(get_catalog(client))))))
    elif args.arquivo:
        if not args.anos or len(args.anos) != 1:
            parser.error('--arquivo exige exatamente um ano em --anos.')
        result = process_file(args.arquivo, args.anos[0], args.saida)
        build_history(args.saida)
        print(json.dumps(result['validacao'], ensure_ascii=False, indent=2))
    else:
        collect(args.anos, args.entrada, args.saida, args.atualizar, all_years=args.todos_anos, workers=args.processos)


if __name__ == '__main__':
    main()
