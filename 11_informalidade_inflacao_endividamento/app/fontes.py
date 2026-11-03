"""Extração opcional e auditoria das séries oficiais, sem alterar o Excel original."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

PASTA = Path(__file__).resolve().parents[1] / 'data/input/fontes_oficiais'
URLS = {
    'informalidade_trimestral': 'https://apisidra.ibge.gov.br/values/t/8529/n1/1/v/12466/p/201601-202504',
    'ipca_mensal': 'https://apisidra.ibge.gov.br/values/t/1737/n1/1/v/63/p/201601-202512',
    'endividamento_mensal': 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.29037/dados?formato=json&dataInicial=01/01/2016&dataFinal=31/12/2025',
    'ibge_8529_metadados': 'https://servicodados.ibge.gov.br/api/v3/agregados/8529/metadados',
    'ibge_1737_metadados': 'https://servicodados.ibge.gov.br/api/v3/agregados/1737/metadados',
}

def coletar(pasta=PASTA):
    pasta.mkdir(parents=True, exist_ok=True)
    def baixar(item):
        nome, url = item
        consulta = datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Atividade11-auditoria/1.0'})
            with urllib.request.urlopen(request, timeout=30) as resposta:
                data = resposta.read()
                if data.startswith(b'\x1f\x8b'):
                    data = gzip.decompress(data)
                json.loads(data)
                (pasta / f'{nome}.json').write_bytes(data)
                return {'fonte': nome, 'url': url, 'consulta': consulta,
                        'sha256': hashlib.sha256(data).hexdigest(), 'status': 'Obtida'}
        except Exception as exc:
            return {'fonte': nome, 'url': url, 'consulta': consulta,
                    'status': 'Falha de consulta', 'erro': str(exc)}
    with ThreadPoolExecutor(max_workers=5) as executor:
        manifest = list(executor.map(baixar, URLS.items()))
    (pasta / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest

def ler_sidra(pasta, nome, variavel):
    dados = json.loads((pasta / f'{nome}.json').read_text())
    linhas = dados[1:]
    if not linhas or any(r['D1C'] != '1' or r['D2C'] != variavel or r['MN'] != '%' for r in linhas):
        raise ValueError(f'Metadados SIDRA incompatíveis: {nome}')
    valores = {r['D3C']: float(r['V']) for r in linhas}
    if len(valores) != len(linhas):
        raise ValueError(f'Períodos duplicados: {nome}')
    return valores

def auditar_fontes(d, arquivo, pasta=PASTA):
    manifest = json.loads((pasta / 'manifesto.json').read_text()) if (pasta / 'manifesto.json').exists() else []
    fontes = {r['fonte']: r for r in manifest}
    def verificar_snapshot(nome):
        registro = fontes.get(nome, {})
        path = pasta / f'{nome}.json'
        if registro.get('status') != 'Obtida' or not path.exists():
            raise ValueError('Snapshot oficial não disponível nesta consulta.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != registro['sha256']:
            raise ValueError('Hash do snapshot oficial incompatível com o manifesto.')
    oficiais, problemas = {}, {}
    for nome, variavel, chave in [('informalidade_trimestral', '12466', 'informalidade'),
                                  ('ipca_mensal', '63', 'ipca')]:
        try:
            verificar_snapshot(nome)
            oficiais[chave] = ler_sidra(pasta, nome, variavel)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            problemas[chave] = str(exc)
    try:
        verificar_snapshot('endividamento_mensal')
        raw = json.loads((pasta / 'endividamento_mensal.json').read_text())
        oficiais['endividamento'] = {datetime.strptime(r['data'], '%d/%m/%Y').strftime('%Y%m'): float(r['valor']) for r in raw}
        if len(oficiais['endividamento']) != len(raw):
            raise ValueError('Meses duplicados no SGS.')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problemas['endividamento'] = str(exc)
    mensal = pd.read_excel(arquivo, sheet_name='Dados mensais')
    mensal.columns = ['trimestre','p1','p2','p3','e1','e2','e3']
    mensal = mensal.set_index('trimestre')
    comparacoes, meses, base_oficial = [], [], []
    for row in d.itertuples():
        periodo = row.periodo
        cod = f'{periodo.year}{periodo.quarter:02}'
        registros = {'trimestre': row.trimestre}
        for variavel in ['informalidade', 'ipca', 'endividamento']:
            original = float(getattr(row, variavel))
            erro = problemas.get(variavel, '')
            try:
                if erro:
                    raise ValueError(erro)
                if variavel == 'informalidade':
                    oficial = oficiais[variavel][cod]
                else:
                    valores = []
                    for j, mes in enumerate(pd.period_range(periodo.start_time, periods=3, freq='M'), 1):
                        valor = oficiais[variavel][mes.strftime('%Y%m')]
                        fornecido = float(mensal.loc[row.trimestre, ('p' if variavel == 'ipca' else 'e') + str(j)])
                        meses.append({'trimestre': row.trimestre, 'mes': str(mes), 'variavel': variavel,
                                      'planilha': fornecido, 'oficial': valor, 'diferenca_pp': fornecido-valor,
                                      'confere': bool(np.isclose(fornecido, valor, rtol=0, atol=1e-8))})
                        valores.append(valor)
                    oficial = (np.prod(1 + np.array(valores)/100)-1)*100 if variavel == 'ipca' else np.mean(valores)
                    if variavel == 'endividamento':
                        registros['endividamento_fim'] = valores[-1]
                confere = bool(np.isclose(original, oficial, rtol=0, atol=1e-8))
                status = 'Confere' if confere else 'Diverge da versão consultada'
                registros[variavel] = oficial
            except (KeyError, ValueError) as exc:
                oficial = np.nan
                confere = False
                status = 'Não conferido'
                erro = str(exc)
            comparacoes.append({'trimestre': row.trimestre, 'variavel': variavel, 'planilha': original,
                                'oficial': oficial, 'diferenca_pp': original-oficial, 'confere': confere,
                                'status': status, 'erro': erro})
        base_oficial.append(registros)
    comparacoes = pd.DataFrame(comparacoes)
    resumo = comparacoes.groupby('variavel', sort=False).agg(
        observacoes=('trimestre','size'), conferidas=('oficial','count'),
        coincidentes=('confere','sum'), erro_maximo_pp=('diferenca_pp', lambda s: s.abs().max())).reset_index()
    resumo['divergentes'] = resumo.conferidas - resumo.coincidentes
    resumo['status'] = np.where(resumo.conferidas < resumo.observacoes, 'Auditoria incompleta',
                                np.where(resumo.divergentes > 0, 'Divergências encontradas', 'Conferida com a versão consultada'))
    return comparacoes, pd.DataFrame(meses), resumo, pd.DataFrame(base_oficial), manifest

if __name__ == '__main__':
    for resultado in coletar():
        print(resultado['fonte'], resultado['status'], resultado.get('erro', ''))
