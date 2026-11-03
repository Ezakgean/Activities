"""Análise reprodutível da base trimestral fornecida, sem coleta ou imputação."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import warnings

os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import acorr_breusch_godfrey, het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.stattools import adfuller, kpss

ROOT = Path(__file__).resolve().parents[1]
ARQUIVO = ROOT / 'data/input/base_regressao_informalidade_ipca_endividamento_2016_2025.xlsx'
VARIAVEIS = ['informalidade', 'ipca', 'endividamento']
MODELOS = {
    'M1': 'informalidade ~ ipca',
    'M2': 'informalidade ~ endividamento',
    'M3': 'informalidade ~ ipca + endividamento',
    'M4': 'informalidade ~ ipca + endividamento + pandemia',
    'D1': 'd_informalidade ~ d_ipca',
    'D2': 'd_informalidade ~ d_endividamento',
    'D3': 'd_informalidade ~ d_ipca + d_endividamento',
    'D4': 'd_informalidade ~ d_ipca + d_endividamento + d_pandemia',
    'R1': 'd_informalidade ~ d_informalidade_lag1 + ipca_lag1 + d_endividamento_lag1 + pandemia + C(trimestre_num)',
    'R2': 'informalidade ~ ipca + endividamento + pandemia + tendencia + C(trimestre_num)',
    'R3': 'informalidade ~ ipca + endividamento + pandemia_nucleo',
    'R4': 'informalidade ~ ipca + endividamento + pandemia_ampla',
}


def preparar(d: pd.DataFrame) -> pd.DataFrame:
    """Valida trimestres e mantém mudanças/defasagens apenas em períodos consecutivos."""
    d = d.copy()
    if not d.trimestre.astype(str).str.fullmatch(r'\d{4}T[1-4]').all():
        raise ValueError('Identificador trimestral inválido; use AAAAT1 a AAAAT4.')
    d['periodo'] = pd.PeriodIndex(d.trimestre.str.replace('T', 'Q'), freq='Q')
    if d.periodo.duplicated().any():
        raise ValueError('Trimestres duplicados.')
    d = d.sort_values('periodo').reset_index(drop=True)
    for v in VARIAVEIS:
        d[v] = pd.to_numeric(d[v], errors='raise')
    if not np.isfinite(d[VARIAVEIS].to_numpy()).all():
        raise ValueError('Valores ausentes ou não finitos nas séries.')
    for v in ['informalidade', 'endividamento']:
        if not d[v].between(0, 100).all():
            raise ValueError(f'{v} deve estar em %, entre 0 e 100.')
    if (d.ipca <= -100).any():
        raise ValueError('Inflação incompatível com o cálculo do índice de preços.')
    ordinais = d.periodo.map(lambda p: p.ordinal)
    consecutivo = ordinais.diff().eq(1)
    d['pandemia'] = d.periodo.between(pd.Period('2020Q1'), pd.Period('2021Q4')).astype(int)
    d['pandemia_nucleo'] = d.periodo.between(pd.Period('2020Q2'), pd.Period('2021Q4')).astype(int)
    d['pandemia_ampla'] = d.periodo.between(pd.Period('2020Q1'), pd.Period('2023Q2')).astype(int)
    d['trimestre_num'] = d.periodo.dt.quarter
    d['tendencia'] = ordinais - ordinais.min()
    for v in VARIAVEIS + ['pandemia']:
        d[f'd_{v}'] = d[v].diff().where(consecutivo)
    for v in ['ipca', 'd_endividamento', 'd_informalidade']:
        d[f'{v}_lag1'] = d[v].shift().where(consecutivo)
    return d


def ler_base(arquivo: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_excel(arquivo, sheet_name='Base para regressao', header=None)
    linhas = raw[0].astype(str).str.fullmatch(r'\d{4}T[1-4]')
    d = raw.loc[linhas, :3].copy()
    d.columns = ['trimestre'] + VARIAVEIS
    d = preparar(d)
    esperado = pd.period_range('2016Q1', '2025Q4', freq='Q')
    if list(d.periodo) != list(esperado):
        raise ValueError('A atividade requer os 40 trimestres consecutivos de 2016T1 a 2025T4.')
    mensal = pd.read_excel(arquivo, sheet_name='Dados mensais')
    if mensal.shape[1] != 7:
        raise ValueError('A aba Dados mensais deve ter trimestre e seis valores mensais.')
    mensal.columns = ['trimestre', 'p1', 'p2', 'p3', 'e1', 'e2', 'e3']
    if mensal.trimestre.duplicated().any() or set(mensal.trimestre) != set(d.trimestre):
        raise ValueError('Trimestres mensais duplicados ou incompatíveis com a base.')
    valores = mensal.iloc[:, 1:].apply(pd.to_numeric, errors='raise')
    if not np.isfinite(valores.to_numpy()).all():
        raise ValueError('Dados mensais ausentes ou não finitos.')
    mensal['ipca_recalculado'] = ((1 + valores[['p1', 'p2', 'p3']] / 100).prod(axis=1) - 1) * 100
    mensal['endividamento_recalculado'] = valores[['e1', 'e2', 'e3']].mean(axis=1)
    conferir = d.merge(mensal, on='trimestre', validate='one_to_one')
    erros = {}
    for v in ['ipca', 'endividamento']:
        erros[v] = float((conferir[v] - conferir[f'{v}_recalculado']).abs().max())
        if erros[v] > 1e-8:
            raise ValueError(f'Agregação mensal inconsistente: {v}.')
    fontes = pd.read_excel(arquivo, sheet_name='Metodologia e fontes').to_dict('records')
    return d, {'sha256': hashlib.sha256(arquivo.read_bytes()).hexdigest(), 'observacoes': len(d),
               'inicio': d.trimestre.iloc[0], 'fim': d.trimestre.iloc[-1],
               'erro_maximo_agregacao': erros, 'metadados_planilha': fontes,
               'validacao': 'Estrutura e agregações internas conferidas; séries não auditadas contra as fontes externas.'}


def estacionariedade(d: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for v in VARIAVEIS + [f'd_{v}' for v in VARIAVEIS]:
        s = d[v].dropna()
        for deterministico in ['c', 'ct']:
            adf = adfuller(s, maxlag=4, regression=deterministico, autolag='AIC')
            with warnings.catch_warnings(record=True) as avisos:
                warnings.simplefilter('always')
                kp = kpss(s, regression=deterministico, nlags=4)
            linhas.append({'variavel': v, 'deterministico': deterministico, 'n': len(s),
                           'adf_estatistica': adf[0], 'adf_p': adf[1], 'adf_lags': adf[2],
                           'kpss_estatistica': kp[0], 'kpss_p_tabelado': kp[1],
                           'kpss_lags': kp[2], 'kpss_aviso': ' | '.join(str(a.message) for a in avisos)})
    return pd.DataFrame(linhas)


def estimar(d: pd.DataFrame, lags: int = 4):
    ajustes, coefs, resumo, diagnosticos, sensibilidade = {}, [], [], [], []
    for nome, formula in MODELOS.items():
        ols = smf.ols(formula, data=d, missing='drop').fit()
        r = ols.get_robustcov_results(cov_type='HAC', maxlags=lags, use_correction=True, use_t=True)
        ajustes[nome] = r
        nomes = ols.model.exog_names
        for j, termo in enumerate(nomes):
            # Pré-especificado H1: coeficiente > 0; p unilateral não substitui o bilateral.
            coefs.append({'modelo': nome, 'termo': termo, 'coeficiente': r.params[j],
                          'ep_hac': r.bse[j], 't_hac': r.tvalues[j], 'p_bilateral': r.pvalues[j],
                          'p_unilateral_positivo': stats.t.sf(r.tvalues[j], r.df_resid),
                          'ic95_inferior': r.conf_int()[j, 0], 'ic95_superior': r.conf_int()[j, 1]})
        alvos = [i for i, n in enumerate(nomes) if n in ['ipca', 'endividamento', 'd_ipca', 'd_endividamento', 'ipca_lag1', 'd_endividamento_lag1']]
        restricao = np.eye(len(nomes))[alvos]
        conjunto = r.f_test(restricao)
        resumo.append({'modelo': nome, 'formula': formula, 'n': int(r.nobs), 'r2': r.rsquared,
                       'r2_ajustado': r.rsquared_adj, 'aic': r.aic, 'bic': r.bic,
                       'f_hac_explicativas': float(np.asarray(conjunto.fvalue).item()),
                       'p_f_hac_explicativas': float(conjunto.pvalue), 'gl_residuais': r.df_resid})
        bg = acorr_breusch_godfrey(ols, nlags=4)
        bp = het_breuschpagan(ols.resid, ols.model.exog)
        for j, termo in enumerate(nomes):
            if termo != 'Intercept':
                diagnosticos.append({'modelo': nome, 'termo': termo,
                                     'vif': variance_inflation_factor(ols.model.exog, j),
                                     'bg_lm_p_4': bg[1], 'bp_lm_p': bp[1]})
        for lag in sorted({1, 4, lags}):
            alt = ols.get_robustcov_results(cov_type='HAC', maxlags=lag, use_correction=True, use_t=True)
            for j in alvos:
                sensibilidade.append({'modelo': nome, 'termo': nomes[j], 'hac_lags': lag,
                                      'coeficiente': alt.params[j], 'ep_hac': alt.bse[j], 'p_bilateral': alt.pvalues[j]})
    return (ajustes, pd.DataFrame(coefs), pd.DataFrame(resumo),
            pd.DataFrame(diagnosticos), pd.DataFrame(sensibilidade))


def tabela_md(df: pd.DataFrame) -> str:
    def fmt(x):
        return f'{x:.4f}' if isinstance(x, (float, np.floating)) else str(x).replace('|', '/')
    return '\n'.join(['| ' + ' | '.join(map(str, df.columns)) + ' |',
                      '| ' + ' | '.join(['---'] * len(df.columns)) + ' |'] +
                     ['| ' + ' | '.join(fmt(x) for x in linha) + ' |' for linha in df.itertuples(index=False, name=None)])


def graficos(d, coefs, ajustes, saida):
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    x = d.periodo.dt.to_timestamp()
    fig, axs = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for ax, v, cor in zip(axs, VARIAVEIS, ['#176b87', '#b05c13', '#7952a0']):
        ax.plot(x, d[v], color=cor, marker='.', label=v)
        ax.axvspan(pd.Timestamp('2020-01-01'), pd.Timestamp('2021-12-31'), color='gray', alpha=.15)
        ax.set_ylabel('%'); ax.set_title(v.capitalize(), loc='left'); ax.grid(alpha=.2)
    fig.suptitle('Brasil, 2016–2025 | faixa cinza: dummy 2020T1–2021T4')
    fig.tight_layout(); fig.savefig(saida / 'series.png', dpi=150); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for ax, v in zip(axs, ['ipca', 'endividamento']):
        sub = coefs[(coefs.modelo.isin(['M1','M2','M3','M4'])) & coefs.termo.eq(v)]
        ax.errorbar(sub.coeficiente, sub.modelo, xerr=[sub.coeficiente-sub.ic95_inferior, sub.ic95_superior-sub.coeficiente], fmt='o', capsize=4)
        ax.axvline(0, color='gray', linestyle='--'); ax.set_title(v.capitalize())
        ax.set_xlabel('p.p. de informalidade por +1 p.p.; IC 95% HAC')
    fig.tight_layout(); fig.savefig(saida / 'coeficientes.png', dpi=150); plt.close(fig)
    fig, axs = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    axs[0].plot(x, d.informalidade, label='Observada')
    axs[0].plot(x, ajustes['M4'].fittedvalues, label='Ajustada M4')
    axs[0].set_ylabel('Informalidade (%)'); axs[0].legend()
    axs[1].plot(x, ajustes['M4'].resid, color='#b05c13')
    axs[1].axhline(0, color='gray'); axs[1].set_ylabel('Resíduos M4 (p.p.)')
    fig.tight_layout(); fig.savefig(saida / 'ajuste_m4.png', dpi=150); plt.close(fig)
    graficos_quatro_modelos(d, ajustes, saida)


def graficos_quatro_modelos(d, ajustes, saida):
    """Gráficos individuais: ajuste, relações condicionais e contrastes HAC."""
    cores = ['#176b87', '#bf621a']
    titulos = {
        'M1': 'Modelo 1 — Informalidade e inflação (IPCA)',
        'M2': 'Modelo 2 — Informalidade e endividamento das famílias',
        'M3': 'Modelo 3 — Inflação e endividamento no mesmo modelo',
        'M4': 'Modelo 4 — Inflação, endividamento e dummy da pandemia',
    }
    arquivos = {'M1': 'modelo_1_ipca', 'M2': 'modelo_2_endividamento',
                'M3': 'modelo_3_ipca_endividamento', 'M4': 'modelo_4_pandemia'}
    rotulos = {'ipca': 'IPCA acumulado no trimestre (%)',
               'endividamento': 'Endividamento / renda acumulada em 12 meses (%)'}
    for nome, titulo in titulos.items():
        r = ajustes[nome]
        nomes = r.model.exog_names
        beta = np.asarray(r.params)
        cov = np.asarray(r.cov_params())
        critico = stats.t.ppf(.975, r.df_resid)
        multiplo = nome in ['M3', 'M4']
        fig, axs = plt.subplots(2 if multiplo else 1, 2, figsize=(14, 10 if multiplo else 5.8))
        axes = np.asarray(axs).ravel()

        def predicao(v, grade, dummy=0):
            design = np.ones((len(grade), len(nomes)))
            for j, termo in enumerate(nomes):
                if termo == v:
                    design[:, j] = grade
                elif termo == 'pandemia':
                    design[:, j] = dummy
                elif termo != 'Intercept':
                    design[:, j] = d[termo].mean()
            y = design @ beta
            ep = np.sqrt(np.maximum(0, np.einsum('ij,jk,ik->i', design, cov, design)))
            return y, critico * ep

        variaveis = ['ipca', 'endividamento'] if multiplo else ['ipca' if nome == 'M1' else 'endividamento']
        for ax, v in zip(axes, variaveis):
            j = nomes.index(v)
            grade = np.linspace(d[v].min(), d[v].max(), 120)
            observado = d.informalidade.copy()
            # Ajusta os pontos para o mesmo valor médio da outra explicativa.
            for outra in ['ipca', 'endividamento']:
                if outra != v and outra in nomes:
                    observado -= beta[nomes.index(outra)] * (d[outra] - d[outra].mean())
            grupos = [0, 1] if nome == 'M4' else [0]
            for grupo in grupos:
                mascara = d.pandemia.eq(grupo) if nome == 'M4' else np.ones(len(d), dtype=bool)
                legenda = ('D=1: 2020T1–2021T4' if grupo else 'D=0: demais trimestres') if nome == 'M4' else 'Trimestres observados'
                ax.scatter(d.loc[mascara, v], observado[mascara], color=cores[grupo], alpha=.7, s=27, label=legenda)
                y, margem = predicao(v, grade, grupo)
                ax.plot(grade, y, color=cores[grupo], linewidth=2)
                ax.fill_between(grade, y-margem, y+margem, color=cores[grupo], alpha=.13)
            ax.set_xlabel(rotulos[v])
            ax.set_ylabel('Informalidade ajustada à média da outra variável (%)' if multiplo else 'Taxa de informalidade (%)')
            ax.set_title(f"β = {beta[j]:+.3f} p.p. por +1 p.p. | p bilateral = {r.pvalues[j]:.3f}", fontsize=11)
            ax.legend(fontsize=8, loc='best'); ax.grid(alpha=.2)

        ax_tempo = axes[3] if multiplo else axes[1]
        datas = d.periodo.dt.to_timestamp()
        ax_tempo.plot(datas, d.informalidade, color='#24333d', label='Observada', marker='.', linewidth=1.5)
        ax_tempo.plot(datas, r.fittedvalues, color=cores[0], label=f'Ajustada por {nome}', linewidth=2)
        if nome == 'M4':
            ax_tempo.axvspan(pd.Timestamp('2020-01-01'), pd.Timestamp('2021-12-31'), color=cores[1], alpha=.12, label='D=1')
        ax_tempo.set_title(f'Ajuste no tempo | N={int(r.nobs)} | R²={r.rsquared:.3f}')
        ax_tempo.set_ylabel('Taxa de informalidade (%)'); ax_tempo.set_xlabel('Ano')
        ax_tempo.legend(fontsize=8); ax_tempo.grid(alpha=.2)

        if multiplo:
            ax = axes[2]
            contrastes = []
            for termos in [['ipca'], ['endividamento'], ['ipca', 'endividamento']]:
                c = np.array([1. if n in termos else 0. for n in nomes])
                contrastes.append((float(c @ beta), float(critico * np.sqrt(c @ cov @ c))))
            labels = ['IPCA +1 p.p.; dívida fixa', 'Dívida +1 p.p.; IPCA fixo', 'IPCA e dívida +1 p.p. cada']
            if nome == 'M4':
                c = np.array([1. if n == 'pandemia' else 0. for n in nomes])
                contrastes.append((float(c @ beta), float(critico * np.sqrt(c @ cov @ c))))
                labels.append('Dummy: D=1 versus D=0')
            for k, (efeito, margem) in enumerate(contrastes):
                ax.errorbar(efeito, k, xerr=margem, fmt='o', capsize=5, color=cores[1] if k==3 else cores[0])
            ax.set_yticks(range(len(labels)), labels, fontsize=9)
            ax.invert_yaxis(); ax.axvline(0, color='gray', linestyle='--')
            ax.set_xlabel('Diferença estimada na informalidade (p.p.)')
            ax.set_title('Associações individuais e conjuntas | IC 95% HAC', fontsize=11)
            ax.grid(axis='x', alpha=.2)
        nota = 'Faixas: IC 95% HAC da média estimada; não são intervalos para observações individuais. Associação não implica causalidade.'
        if multiplo:
            nota += '\nPainéis superiores: outra variável econômica fixada na média; pontos ajustados pelo coeficiente dessa variável.'
        if nome == 'M4':
            nota += '\nA dummy desloca o intercepto; as inclinações são iguais nos dois grupos. Demais variáveis fixas nos contrastes.'
        if nome in ['M1', 'M3', 'M4']:
            nota += '\nIPCA mede inflação; a base não contém renda real para medir diretamente a perda de poder de compra.'
        fig.suptitle(titulo, fontsize=16, fontweight='bold')
        fig.text(.02, .015, nota, fontsize=9, va='bottom')
        fig.tight_layout(rect=(0, .13 if multiplo else .15, 1, .94), h_pad=2, w_pad=3)
        for extensao in ['png', 'pdf']:
            fig.savefig(saida / f'{arquivos[nome]}.{extensao}', dpi=170)
        plt.close(fig)


def escrever_relatorio(d, auditoria, coefs, resumo, diag, est, saida, lags):
    principais = coefs[coefs.modelo.isin(['M1','M2','M3','M4']) & coefs.termo.ne('Intercept')]
    def leitura(modelo, termo):
        r = coefs[coefs.modelo.eq(modelo) & coefs.termo.eq(termo)].iloc[0]
        if r.coeficiente > 0 and r.p_bilateral < .05:
            decisao = 'associação positiva com significância bilateral a 5%, condicionada à especificação'
        elif r.coeficiente < 0 and r.p_bilateral < .05:
            decisao = 'associação negativa com significância bilateral a 5%, contrária ao sinal proposto'
        else:
            decisao = 'evidência insuficiente de associação diferente de zero a 5% no teste bilateral'
        return f"{modelo}, {termo}: coeficiente {r.coeficiente:.4f}; p bilateral {r.p_bilateral:.4f}; IC95% [{r.ic95_inferior:.4f}; {r.ic95_superior:.4f}]. Há {decisao}."
    texto = f'''# Atividade 11 — Inflação, endividamento e informalidade no Brasil

## Objetivo e problema de pesquisa
Investigar se o aumento da inflação e do endividamento das famílias está associado ao aumento da taxa de informalidade no Brasil, entre 2016T1 e 2025T4. A hipótese econômica é que a pressão sobre os orçamentos familiares pode estimular ocupações informais. A direção e a intensidade são questões empíricas; este desenho não identifica causalidade.

## Base, medidas e conferência
Amostra: {len(d)} trimestres civis consecutivos. Sem interpolação, imputação ou coleta adicional. O arquivo original foi preservado em data/input. A consistência interna foi conferida por trimestre, recompondo o IPCA mensal e a média do endividamento. Erros máximos: IPCA {auditoria['erro_maximo_agregacao']['ipca']:.2e} e endividamento {auditoria['erro_maximo_agregacao']['endividamento']:.2e}. Isso não certifica a exatidão das séries frente às fontes oficiais; a origem e a versão da série de informalidade ainda precisam ser auditadas para publicação.

- I: informalidade em % dos ocupados, conforme a planilha; não é quantidade de trabalhadores informais.
- π: IPCA acumulado no trimestre em %, calculado por 100 × [∏(1 + IPCA_m/100) − 1].
- E: endividamento em %, média dos três meses. Segundo os metadados, é dívida com o SFN em relação à renda acumulada em 12 meses (SGS 29037); não é percentual de famílias endividadas nem inadimplência.
- D: 1 de 2020T1 a 2021T4 e 0 nos demais trimestres. São 8 observações com D=1. É uma janela analítica adotada, não uma afirmação de encerramento sanitário ou legal da pandemia.

O IPCA mede a variação dos preços. Sem renda nominal ou real, não se observa diretamente a perda de poder de compra. Para renda nominal fixa, a perda percentual no trimestre seria 100 × [1 − 1/(1 + π/100)], uma transformação da inflação, que não acrescenta informação independente. Não incluir essa transformação junto com o IPCA como se fossem dois canais distintos. Para testar o mecanismo de renda, obter rendimento real e justificar seu papel como variável explicativa ou mediadora.

## Os quatro modelos solicitados
Estimação por mínimos quadrados ordinários com intercepto:

1. M1: I_t = α + βπ π_t + u_t.
2. M2: I_t = α + βE E_t + u_t.
3. M3: I_t = α + βπ π_t + βE E_t + u_t.
4. M4: I_t = α + βπ π_t + βE E_t + δ D_t + u_t.

Espera-se βπ > 0 e βE > 0 segundo a hipótese proposta. Os modelos simples estimam associações brutas; M3 e M4 estimam associações parciais. Em M4, δ é um deslocamento médio do intercepto na janela definida, mantendo IPCA e endividamento constantes. A dummy não estima mudança de inclinação nem isola o efeito causal da pandemia.

Todas as variáveis originais estão em escala percentual (38,3 significa 38,3%, não 0,383). Cada β expressa a diferença em pontos percentuais da informalidade associada a +1 ponto percentual na explicativa. Esse coeficiente não é elasticidade. Os erros u_t capturam fatores omitidos.

## Inferência e hipóteses
Erros-padrão HAC de Newey–West, kernel Bartlett, {lags} defasagens, correção de amostra finita e referência t com graus de liberdade residuais. A janela principal de quatro defasagens cobre até um ano; sensibilidade com uma defasagem está em sensibilidade_hac.csv. HAC modifica a inferência, não os coeficientes, e não corrige regressão espúria, endogeneidade ou a equação da média.

A tabela principal usa H0: β=0 contra H1: β≠0, IC95% e significância de 5%. O arquivo de coeficientes também apresenta o teste direcional pré-especificado H0: β≤0 contra H1: β>0; para coeficiente negativo, o p unilateral positivo é grande. Não escolher a cauda após observar os resultados. O teste F robusto de M3/M4 avalia H0: βπ=βE=0; rejeitá-lo não implica que ambos sejam positivos ou individualmente significativos. A dummy fica fora dessa restrição conjunta. A amostra pequena exige cautela mesmo com HAC.

## Resultados dos quatro modelos em nível
{tabela_md(principais[['modelo','termo','coeficiente','ep_hac','p_bilateral','ic95_inferior','ic95_superior']])}

{tabela_md(resumo[resumo.modelo.str.startswith('M')][['modelo','n','r2','r2_ajustado','p_f_hac_explicativas']])}

{chr(10).join(leitura(m,t) for m,t in [('M1','ipca'),('M2','endividamento'),('M3','ipca'),('M3','endividamento'),('M4','ipca'),('M4','endividamento'),('M4','pandemia')])}

A interpretação adequada é condicional aos modelos e à qualidade das séries. Ausência de significância não demonstra ausência de associação. Um sinal negativo não significativo tampouco permite afirmar que a dívida reduz a informalidade.

## Gráficos individuais dos quatro modelos

Cada modelo tem um arquivo PNG e um PDF. Os painéis exibem relações estimadas e o ajuste da informalidade ao longo do tempo. M3 e M4 apresentam também contrastes para aumentos individuais e simultâneos de 1 p.p. no IPCA e no endividamento, com intervalos calculados usando a covariância HAC completa. Nos painéis condicionais, a outra explicativa econômica fica na média e os pontos observados são ajustados para esse mesmo valor. Em M4, as curvas distinguem D=0 e D=1; o contraste da dummy compara os grupos com IPCA e endividamento fixos. São associações estimadas, não efeitos causais. As faixas representam a incerteza da média estimada, não a dispersão dos dados individuais.

- [Modelo 1 — IPCA](modelo_1_ipca.png).
- [Modelo 2 — Endividamento](modelo_2_endividamento.png).
- [Modelo 3 — IPCA e endividamento](modelo_3_ipca_endividamento.png).
- [Modelo 4 — IPCA, endividamento e pandemia](modelo_4_pandemia.png).

## Séries temporais e verificações de robustez
Os quatro modelos em nível são referências descritivas. A pergunta sobre aumentos requer examinar também mudanças no tempo:

- D1–D4 usam ΔI como dependente e Δπ e/ou ΔE como explicativas. Em D4, a dummy é ΔD, pois se diferencia a equação M4: representa entrada e saída da janela. Δπ é aceleração/desaceleração da inflação trimestral, não o IPCA trimestral em si; ΔE é a mudança do indicador de dívida, não o crescimento percentual do estoque de dívida.
- R1: ΔI_t = α + ρΔI_(t−1) + θπ π_(t−1) + θE ΔE_(t−1) + δD_t + sazonalidade + u_t. Examina se inflação anterior e aumento anterior do indicador de dívida se associam à mudança atual da informalidade. A dummy em nível neste modelo permite uma mudança média na variação da informalidade durante a janela. É uma especificação diferente de D4. As duas primeiras observações são perdidas (N=38). Defasagens não eliminam endogeneidade.
- R2 acrescenta tendência linear e dummies sazonais a M4 (T1 como referência).
- R3 usa janela 2020T2–2021T4; R4 usa 2020T1–2023T2. As janelas são sensibilidades analíticas, não datas oficiais de uma mesma definição de pandemia.

{tabela_md(coefs[coefs.modelo.isin(['D4','R1','R2','R3','R4']) & coefs.termo.isin(['d_ipca','d_endividamento','ipca','endividamento','ipca_lag1','d_endividamento_lag1'])][['modelo','termo','coeficiente','p_bilateral','ic95_inferior','ic95_superior']])}

{leitura('D4', 'd_ipca')} {leitura('D4', 'd_endividamento')}

{leitura('R1', 'ipca_lag1')} {leitura('R1', 'd_endividamento_lag1')}

Não selecionar a especificação pelo menor p-valor. As especificações respondem a perguntas distintas. O R² de modelos com dependentes diferentes não deve ser comparado; AIC/BIC só devem orientar comparações com a mesma dependente e a mesma amostra.

## Diagnósticos
ADF: H0 de raiz unitária; KPSS: H0 de estacionariedade em torno de constante (c) ou tendência (ct). ADF seleciona até quatro defasagens por AIC; KPSS usa quatro. Os p-valores KPSS são tabelados e os avisos de limites estão preservados em estacionariedade.csv. Com 40 observações, quebras e pandemia reduzem o poder desses testes. Não rejeitar ADF não prova raiz unitária; resultados conflitantes não justificam conclusões automáticas. Os testes c e ct são sensibilidades à parte determinística.

{tabela_md(est[est.deterministico.eq('c')][['variavel','adf_p','adf_lags','kpss_p_tabelado']])}

Na configuração com constante, o ADF não rejeita raiz unitária nas três séries em nível a 5%. O KPSS rejeita estacionariedade do endividamento; para as outras duas séries, os testes não são conclusivos em conjunto. Nas primeiras diferenças, o ADF com constante rejeita raiz unitária nas três séries e o KPSS não rejeita estacionariedade. A sensibilidade com tendência, especialmente para a mudança do endividamento, recomenda cautela. Esses resultados favorecem examinar variações, sem certificar automaticamente uma especificação.

Breusch–Godfrey (quatro defasagens) testa H0 de ausência de autocorrelação residual; Breusch–Pagan testa H0 de homocedasticidade. Seus p-valores usuais são diagnósticos aproximados nesta amostra; BP é particularmente sensível à dependência temporal. VIF avalia colinearidade entre os regressores; o intercepto não é reportado.

{tabela_md(diag[diag.modelo.str.startswith('M')].drop_duplicates('modelo')[['modelo','bg_lm_p_4','bp_lm_p']])}

Nos quatro modelos em nível, Breusch–Godfrey rejeita ausência de autocorrelação a 5%; há dependência temporal residual relevante. Os VIFs das explicativas de M4 são próximos de 1, de modo que colinearidade não parece ser o principal problema nesta especificação. O uso de HAC deve ser acompanhado da discussão sobre a dinâmica e a estacionariedade, e não apenas da tabela de significância.

Se há persistência/tendência não resolvida, os resultados em nível não devem fundamentar a conclusão principal. Em etapas posteriores, considerar ARDL/ECM e cointegração apenas após justificar a ordem de integração e excluir séries I(2); erros HAC por si só não tornam uma regressão em nível válida. As variações e defasagens aqui são verificações exploratórias, não prova de que todos os problemas foram resolvidos.

## Conclusão para o trabalho
Nos quatro modelos em nível desta base, a inflação apresenta coeficiente positivo e o endividamento coeficiente negativo, mas nenhum desses coeficientes é significativo a 5% no teste bilateral com a configuração HAC principal. Portanto, essas regressões não fornecem evidência estatística suficiente para sustentar a hipótese de que ambos estejam associados positivamente à informalidade no período. A inclusão da dummy não altera essa leitura. Os resultados em variações e com defasagens devem ser discutidos como sensibilidade, respeitando a mudança do significado dos coeficientes.

Este estudo não demonstra causalidade. Atividade econômica, desemprego, rendimento, composição setorial, transferências, juros e mudanças de medição podem afetar as séries simultaneamente. A taxa de informalidade também pode cair pela saída de informais da ocupação; ela não mede isoladamente criação de postos formais. Com apenas 40 observações, priorizar modelos parcimoniosos e evitar muitos controles e defasagens. A conclusão sobre perda efetiva de poder de compra depende de ampliar a base.

## Reprodutibilidade e referências
Base fornecida pelo usuário; metadados e SHA-256 em auditoria.json. A aba de metodologia informa SIDRA 8529 (informalidade), SIDRA 1737 (IPCA) e SGS 29037 (endividamento). Não foram substituídos dados da planilha por dados externos. As páginas SIDRA e BCB não puderam ser lidas na consulta desta execução; a atribuição das séries acima deriva dos metadados, não de uma auditoria externa concluída.

- [Informalidade — SIDRA 8529](https://sidra.ibge.gov.br/tabela/8529).
- [IPCA — SIDRA 1737](https://sidra.ibge.gov.br/tabela/1737).
- [BCB — SGS 29037](https://dadosabertos.bcb.gov.br/dataset/29037-endividamento-das-familias-com-o-sistema-financeiro-nacional-em-relacao-a-renda-acumulada-dos).
- [statsmodels — covariâncias robustas e HAC](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html).
- [statsmodels — teste ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html).
'''
    # A conclusão textual depende da configuração; nunca persistir uma conclusão padrão incorreta.
    if not (principais[principais.termo.isin(['ipca','endividamento'])].p_bilateral >= .05).all():
        texto = texto.replace('Nos quatro modelos em nível desta base, a inflação apresenta coeficiente positivo e o endividamento coeficiente negativo, mas nenhum desses coeficientes é significativo a 5% no teste bilateral com a configuração HAC principal. Portanto, essas regressões não fornecem evidência estatística suficiente para sustentar a hipótese de que ambos estejam associados positivamente à informalidade no período. A inclusão da dummy não altera essa leitura.', 'Há coeficientes significativos nesta configuração; avaliar os sinais, intervalos e leituras individuais acima antes de concluir sobre a hipótese positiva.')
    texto = re.sub(r'(?m)^(#{1,6} [^\n]+)\n(?!\n)', r'\1\n\n', texto)
    (saida / 'relatorio.md').write_text(texto, encoding='utf-8')
    # HTML portátil, sem dependência de CDN ou servidor.
    blocos = []
    for bloco in texto.split('\n\n'):
        if bloco.startswith('#'):
            nivel = len(bloco) - len(bloco.lstrip('#'))
            blocos.append(f'<h{nivel}>{html.escape(bloco.lstrip("# "))}</h{nivel}>')
        elif bloco.startswith('| '):
            linhas = bloco.splitlines()
            cells = lambda s, tag: ''.join(f'<{tag}>{html.escape(c.strip())}</{tag}>' for c in s.strip('|').split('|'))
            blocos.append('<div class="table"><table><thead><tr>' + cells(linhas[0], 'th') + '</tr></thead><tbody>' + ''.join('<tr>' + cells(l, 'td') + '</tr>' for l in linhas[2:]) + '</tbody></table></div>')
        else:
            escaped = html.escape(bloco)
            escaped = re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)', r'<a href="\2">\1</a>', escaped)
            blocos.append('<p>' + escaped.replace('\n', '<br>') + '</p>')
    titulos_graficos = {
        'modelo_1_ipca': 'Modelo 1 — Informalidade e IPCA',
        'modelo_2_endividamento': 'Modelo 2 — Informalidade e endividamento',
        'modelo_3_ipca_endividamento': 'Modelo 3 — IPCA e endividamento',
        'modelo_4_pandemia': 'Modelo 4 — IPCA, endividamento e pandemia',
    }
    arquivos_graficos = sorted(saida.glob('modelo_*.png')) + sorted(p for p in saida.glob('*.png') if not p.name.startswith('modelo_'))
    imgs = ''.join(f'<h3>{html.escape(titulos_graficos.get(p.stem, p.stem))}</h3><img alt="{p.stem}" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}">' for p in arquivos_graficos)
    documento = '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atividade 11 — Análise econométrica</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#20303c}h1,h2{color:#176b87}p{max-width:100ch}.table{overflow:auto}table{border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}img{width:100%;height:auto}a{color:#176b87}@media print{body{margin:0}img,table{break-inside:avoid}}</style>' + ''.join(blocos) + '<h2>Gráficos</h2>' + imgs + '</html>'
    (saida / 'relatorio.html').write_text(documento, encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arquivo', type=Path, default=ARQUIVO)
    parser.add_argument('--saida', type=Path, default=ROOT / 'data/output')
    parser.add_argument('--hac-lags', type=int, choices=range(1, 5), default=4)
    args = parser.parse_args(argv)
    d, auditoria = ler_base(args.arquivo)
    ajustes, coefs, resumo, diag, sens = estimar(d, args.hac_lags)
    est = estacionariedade(d)
    args.saida.mkdir(parents=True, exist_ok=True)
    exportar = d.drop(columns='periodo')
    descritivas = d[VARIAVEIS].describe().rename_axis('estatistica').reset_index()
    correlacoes = d[VARIAVEIS].corr().rename_axis('variavel').reset_index()
    tabelas = {'base_trimestral': exportar, 'coeficientes': coefs, 'modelos': resumo,
               'diagnosticos': diag, 'sensibilidade_hac': sens, 'estacionariedade': est,
               'descritivas': descritivas, 'correlacoes': correlacoes}
    for nome, tabela in tabelas.items():
        tabela.to_csv(args.saida / f'{nome}.csv', index=False, encoding='utf-8-sig')
    with pd.ExcelWriter(args.saida / 'resultados.xlsx', engine='openpyxl') as writer:
        for nome, tabela in tabelas.items():
            tabela.to_excel(writer, sheet_name=nome, index=False)
            ws = writer.sheets[nome]; ws.freeze_panes = 'B2'; ws.auto_filter.ref = ws.dimensions
            for coluna in ws.columns:
                ws.column_dimensions[coluna[0].column_letter].width = min(65, max(15, max(len(str(c.value or '')) for c in coluna) + 2))
    auditoria.update({'python': platform.python_version(), 'pacotes': {p: importlib.metadata.version(p) for p in ['pandas','numpy','statsmodels','scipy','matplotlib','openpyxl']},
                     'configuracao': {'hac_lags': args.hac_lags, 'kernel': 'bartlett', 'use_correction': True, 'use_t': True, 'modelos': MODELOS}})
    (args.saida / 'auditoria.json').write_text(json.dumps(auditoria, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.saida / 'sumarios_modelos.txt').write_text('\n\n'.join(f'{nome}\n{r.summary()}' for nome, r in ajustes.items()), encoding='utf-8')
    graficos(d, coefs, ajustes, args.saida)
    escrever_relatorio(d, auditoria, coefs, resumo, diag, est, args.saida, args.hac_lags)
    print(resumo[resumo.modelo.str.startswith('M')].to_string(index=False))
    print(f'\nRelatório: {args.saida / "relatorio.html"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
