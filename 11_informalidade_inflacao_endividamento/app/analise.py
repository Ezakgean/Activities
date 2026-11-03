"""Análise trimestral com auditoria oficial opcional, sem imputação."""
from __future__ import annotations

import argparse
import hashlib
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

from .relatorio import escrever_html
from .fontes import auditar_fontes, coletar
from .verificacao import reproduzir
from .robustez import aprofundar_estacionariedade, sensibilidade_agregacao, sensibilidade_f_hac

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
        for lag in sorted({1, 2, 4, lags}):
            alt = ols.get_robustcov_results(cov_type='HAC', maxlags=lag, use_correction=True, use_t=True)
            for j in range(len(nomes)):
                sensibilidade.append({'modelo': nome, 'termo': nomes[j], 'hac_lags': lag,
                                      'coeficiente': alt.params[j], 'ep_hac': alt.bse[j], 'p_bilateral': alt.pvalues[j]})
    return (ajustes, pd.DataFrame(coefs), pd.DataFrame(resumo),
            pd.DataFrame(diagnosticos), pd.DataFrame(sensibilidade))


def diagnosticar_multicolinearidade(exog, nomes):
    """VIF com intercepto e condição dos regressores centrados/padronizados."""
    x = np.asarray(exog, dtype=float)
    indices = [j for j, nome in enumerate(nomes) if nome != 'Intercept']
    regressores = x[:, indices]
    desvios = regressores.std(axis=0)
    if np.any(desvios == 0):
        condicao = np.inf
    else:
        padronizados = (regressores - regressores.mean(axis=0)) / desvios
        condicao = float(np.linalg.cond(padronizados))
    posto = int(np.linalg.matrix_rank(x))
    if posto < x.shape[1]:
        condicao = np.inf
    linhas = []
    for j in indices:
        if np.linalg.matrix_rank(np.delete(x, j, axis=1)) == posto:
            vif = np.inf
        else:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                vif = float(variance_inflation_factor(x, j))
        tolerancia = 0. if np.isinf(vif) else 1 / vif
        alerta = ('Elevada (VIF >= 10)' if vif >= 10 else
                  'Atenção (5 <= VIF < 10)' if vif >= 5 else 'Baixa (VIF < 5)')
        linhas.append({'termo': nomes[j], 'vif': vif, 'tolerancia': tolerancia,
                       'r2_auxiliar': 1 - tolerancia, 'avaliacao_vif': alerta})
    resumo = {'n': x.shape[0], 'numero_regressores': len(indices),
              'posto_matriz_com_intercepto': posto, 'colunas_com_intercepto': x.shape[1],
              'dependencia_linear_exata': posto < x.shape[1],
              'numero_condicao_padronizado': condicao,
              'avaliacao_condicao': ('Elevada (>= 30)' if condicao >= 30 else
                                     'Atenção (10 a 30)' if condicao >= 10 else 'Baixa (< 10)'),
              'vif_maximo': max(l['vif'] for l in linhas)}
    return linhas, resumo


def multicolinearidade(ajustes):
    variaveis, modelos = [], []
    for modelo, r in ajustes.items():
        linhas, resumo = diagnosticar_multicolinearidade(r.model.exog, r.model.exog_names)
        variaveis.extend({'modelo': modelo, **linha} for linha in linhas)
        modelos.append({'modelo': modelo, **resumo})
    return pd.DataFrame(variaveis), pd.DataFrame(modelos)


def testes_significancia(ajustes, coefs, alfa=.05):
    """Testes t bilaterais e F de Wald com a mesma covariância HAC."""
    testes_t = coefs[['modelo', 'termo', 'coeficiente', 'ep_hac', 't_hac',
                      'p_bilateral', 'ic95_inferior', 'ic95_superior']].copy()
    testes_t['gl'] = testes_t.modelo.map({m: r.df_resid for m, r in ajustes.items()})
    testes_t['t_critico_5pct'] = stats.t.ppf(1 - alfa / 2, testes_t.gl)
    testes_t['h0'] = testes_t.termo + ' = 0'
    testes_t['decisao_5pct'] = np.where(testes_t.p_bilateral < alfa, 'Rejeitar H0', 'Não rejeitar H0')
    linhas = []
    economicas = {'ipca', 'endividamento', 'd_ipca', 'd_endividamento',
                  'ipca_lag1', 'd_endividamento_lag1'}
    for modelo, r in ajustes.items():
        nomes = r.model.exog_names
        grupos = [('individual', [termo]) for termo in nomes]
        grupos += [('global', [t for t in nomes if t != 'Intercept']),
                   ('economicas', [t for t in nomes if t in economicas])]
        sazonais = [t for t in nomes if t.startswith('C(trimestre_num)')]
        if sazonais:
            grupos.append(('sazonalidade', sazonais))
        for tipo, termos in grupos:
            restricao = np.eye(len(nomes))[[nomes.index(t) for t in termos]]
            teste = r.f_test(restricao)
            pvalor = float(teste.pvalue)
            linhas.append({'modelo': modelo, 'tipo': tipo, 'termos': ' + '.join(termos),
                           'h0': '; '.join(t + ' = 0' for t in termos),
                           'f_hac': float(np.asarray(teste.fvalue).item()),
                           'gl_numerador': float(teste.df_num),
                           'gl_denominador': float(teste.df_denom),
                           'f_critico_5pct': stats.f.ppf(1 - alfa, teste.df_num, teste.df_denom),
                           'p_valor': pvalor,
                           'decisao_5pct': 'Rejeitar H0' if pvalor < alfa else 'Não rejeitar H0'})
    return testes_t, pd.DataFrame(linhas)


def tabela_md(df: pd.DataFrame) -> str:
    def fmt(x):
        if isinstance(x, (float, np.floating)):
            return f'{x:.3e}' if 0 < abs(x) < 1e-4 else f'{x:.4f}'
        return str(x).replace('|', '/')
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


def graficos_revisao(ajustes, comparacao, saida):
    from statsmodels.graphics.tsaplots import plot_acf
    fig, axs = plt.subplots(3, 4, figsize=(15, 9))
    for ax, (nome, r) in zip(axs.ravel(), ajustes.items()):
        plot_acf(r.resid, ax=ax, lags=8, zero=False, alpha=.05, title=f'{nome} | N={int(r.nobs)}')
        ax.set_xlabel('Defasagem (trimestres)'); ax.set_ylim(-1,1)
    fig.suptitle('Persistência dos resíduos | todos os modelos', fontsize=16)
    fig.text(.02,.01,'Faixas de referência aproximadas a 95%. Correlogramas descritivos; consultar BG(4).',fontsize=10)
    fig.tight_layout(rect=(0,.04,1,.95))
    for ext in ['png','pdf']:
        fig.savefig(saida/f'autocorrelacao_modelos.{ext}',dpi=160)
    plt.close(fig)
    sub = comparacao[comparacao.modelo.isin(['M2','M3','M4']) & comparacao.termo.eq('endividamento')]
    fig, ax = plt.subplots(figsize=(10,4.5))
    for j, row in enumerate(sub.itertuples()):
        for deslocamento, coef, ep, cor, rotulo in [(-.12,row.coef_media,row.ep_media,'#176b87','Média trimestral'),
                                                   (.12,row.coef_fim,row.ep_fim,'#b05c13','Fim de trimestre')]:
            critico=stats.t.ppf(.975,ajustes[row.modelo].df_resid)
            ax.errorbar(coef,j+deslocamento,xerr=critico*ep,fmt='o',capsize=5,color=cor,
                        label=rotulo if j==0 else None)
    ax.set_yticks(range(len(sub)),sub.modelo); ax.invert_yaxis();ax.axvline(0,color='gray',linestyle='--')
    ax.set_title('Endividamento | sensibilidade da agregação e IC 95% HAC')
    ax.set_xlabel('Associação em p.p. de informalidade por +1 p.p. de endividamento')
    ax.legend();ax.grid(axis='x',alpha=.2)
    fig.text(.02,.01,'Mesma base mensal, amostras, dummies e HAC. Não é um teste de igualdade dos coeficientes.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1))
    for ext in ['png','pdf']:
        fig.savefig(saida/f'sensibilidade_agregacao.{ext}',dpi=160)
    plt.close(fig)


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


def escrever_relatorio(d, auditoria, coefs, resumo, diag, est, saida, lags, testes_t, testes_f, multi_variaveis, multi_modelos, revisao):
    principais = coefs[coefs.modelo.isin(['M1','M2','M3','M4']) & coefs.termo.ne('Intercept')]
    alertas_multi = multi_variaveis[multi_variaveis.vif >= 5]
    leitura_multi = ('Nenhum modelo apresenta VIF ≥ 5 nas explicativas.' if alertas_multi.empty else
                     'Variáveis com VIF ≥ 5: ' + '; '.join(
                         f'{r.modelo}, {r.termo}: VIF={r.vif:.4f}, tolerância={r.tolerancia:.4f}'
                         for r in alertas_multi.itertuples()) + '.')
    leitura_multi += (' Há dependência linear exata em pelo menos um modelo.'
                      if multi_modelos.dependencia_linear_exata.any() else
                      ' Não foi detectada dependência linear exata em nenhum modelo.')
    def leitura(modelo, termo):
        r = coefs[coefs.modelo.eq(modelo) & coefs.termo.eq(termo)].iloc[0]
        if r.coeficiente > 0 and r.p_bilateral < .05:
            decisao = 'associação positiva com significância bilateral a 5%, condicionada à especificação'
        elif r.coeficiente < 0 and r.p_bilateral < .05:
            decisao = 'associação negativa com significância bilateral a 5%, contrária ao sinal proposto'
        else:
            decisao = 'evidência insuficiente de associação diferente de zero a 5% no teste bilateral'
        return f"{modelo}, {termo}: coeficiente {r.coeficiente:.4f}; p bilateral {r.p_bilateral:.4f}; IC95% [{r.ic95_inferior:.4f}; {r.ic95_superior:.4f}]. Há {decisao}."
    fontes_res = revisao['fontes_resumo']
    verificacao = revisao['reproducao_modelos']
    diag_todos = diag.drop_duplicates('modelo')[['modelo','bg_lm_p_4','bp_lm_p']].copy()
    diag_todos['bg_rejeita_5pct'] = diag_todos.bg_lm_p_4 < .05
    diag_todos['bp_rejeita_5pct'] = diag_todos.bp_lm_p < .05
    comparacao_fim = revisao['agregacao_coeficientes']
    econ_fim = comparacao_fim[comparacao_fim.modelo.isin(['M1','M2','M3','M4']) & comparacao_fim.termo.isin(['ipca','endividamento'])]
    leitura_fim = ('A substituição da média pelo último mês preserva os sinais e as decisões bilaterais a 5% dos coeficientes econômicos de M1–M4.'
                   if not (econ_fim.mudou_sinal | econ_fim.mudou_decisao_5pct).any() else
                   'Há mudança de sinal ou decisão em coeficientes econômicos de M1–M4; consulte as linhas abaixo.')
    mudancas_fim = comparacao_fim[comparacao_fim.mudou_decisao_5pct | comparacao_fim.mudou_sinal]
    resumo_integracao = revisao['estacionariedade_sens'].groupby(['variavel','ordem_diferenca'], sort=False).agg(
        adf_p_min=('adf_p','min'), adf_p_max=('adf_p','max'),
        kpss_p_min=('kpss_p_tabelado','min'), kpss_p_max=('kpss_p_tabelado','max')).reset_index()
    status_fontes = ('As 120 observações trimestrais (40 de cada variável) coincidem com a versão oficial consultada, à tolerância absoluta de 1e−8 p.p.'
                     if fontes_res.coincidentes.sum() == 120 else
                     'A conferência oficial tem divergências ou observações não conferidas; consulte a tabela antes de interpretar as regressões.')
    consultas = auditoria.get('fontes_oficiais', [])
    data_consulta = ', '.join(sorted({r['consulta'][:10] for r in consultas})) or 'não disponível'
    status_revisao = pd.DataFrame([
        ('Dados', 'Comparação oficial executada', status_fontes),
        ('Cálculos', '12 modelos reproduzidos', 'Matrizes, amostras, MQO, HAC, t, F, IC95%, BG, BP e VIF conferidos por cálculo separado.'),
        ('Agregação', 'Sensibilidade executada', leitura_fim),
        ('Séries temporais', 'Diagnóstico ampliado; validação limitada', 'ADF/KPSS sensíveis à especificação; quebras não resolvem a incerteza sobre a integração.'),
        ('Especificação', 'Limitação reconhecida', 'Os modelos dinâmicos são exploratórios; não há identificação causal nem controles econômicos adicionais nesta base.'),
    ], columns=['dimensao','situacao','evidencia_ou_limite'])
    f_economico = testes_f[testes_f.tipo.eq('economicas')].set_index('modelo')
    f_global = testes_f[testes_f.tipo.eq('global')].set_index('modelo')
    alcance_testes = pd.DataFrame([
        ('t bilateral e IC95% de M4', 'Associação parcial de cada regressor, condicionada aos demais',
         'IPCA e endividamento: incerteza compatível com coeficientes nulos nesta configuração.',
         'Não demonstram inexistência de relação, causalidade ou irrelevância econômica.'),
        ('F econômico de M4', 'IPCA e endividamento conjuntamente iguais a zero',
         f"F={f_economico.loc['M4','f_hac']:.4f}; p={f_economico.loc['M4','p_valor']:.4f}.",
         'Não testa se ambos os coeficientes são positivos nem a validade temporal da equação.'),
        ('F global de R1', 'Todos os regressores, incluindo dinâmica, pandemia e sazonalidade',
         f"F={f_global.loc['R1','f_hac']:.4f}; p={f_global.loc['R1','p_valor']:.4f}.",
         'Sua rejeição não identifica qual bloco explica o resultado nem valida R1 como principal.'),
        ('F econômico de R1', 'Inflação defasada e variação do endividamento defasada conjuntamente nulas',
         f"F={f_economico.loc['R1','f_hac']:.4f}; p={f_economico.loc['R1','p_valor']:.4f}.",
         'A rejeição global de R1 não deve ser apresentada como confirmação da hipótese econômica.'),
        ('BG, ADF/KPSS e VIF', 'Dependência residual, propriedades temporais e colinearidade',
         'Diagnósticos com objetos distintos; nenhum equivale à validação integral da especificação.',
         'VIF baixo e não rejeição de BG não comprovam exogeneidade, estacionariedade ou causalidade.'),
    ], columns=['teste_ou_diagnostico','objeto','resultado_ou_leitura','limite_da_conclusao'])
    texto = f'''# Atividade 11 — Inflação, endividamento e informalidade no Brasil

## Revisão técnica e estado da validação

Esta versão incorpora o parecer técnico, mantendo M1–M4 e a dummy 2020T1–2021T4. As tabelas, os gráficos e as interpretações anteriores permanecem disponíveis. A análise distingue a correspondência com as fontes, a reprodução dos cálculos e a adequação econômica e temporal da especificação. A primeira e a segunda não demonstram a terceira.

{tabela_md(status_revisao)}

M4 é a referência descritiva principal da apresentação, justificada pela pergunta econômica e pela parcimônia. Os modelos em nível não constituem evidência temporal já validada. Os testes de significância são apresentados como resultados condicionais às especificações; a persistência e a autocorrelação impedem transformar sua correção aritmética em conclusão definitiva. A análise em diferenças e R1 permanece exploratória, com hipóteses econômicas distintas. Não foi escolhido um modelo pelo menor p-valor.

## Objetivo e problema de pesquisa
Investigar se o aumento da inflação e do endividamento das famílias está associado ao aumento da taxa de informalidade no Brasil, entre 2016T1 e 2025T4. A hipótese econômica é que a pressão sobre os orçamentos familiares pode estimular ocupações informais. A direção e a intensidade são questões empíricas; este desenho não identifica causalidade.

## Base, medidas e conferência
Amostra: {len(d)} trimestres civis consecutivos. Sem interpolação ou imputação. A comparação externa usa snapshots oficiais separados, sem substituir a base fornecida. O arquivo original foi preservado em data/input. A consistência interna foi conferida por trimestre, recompondo o IPCA mensal e a média do endividamento. Erros máximos: IPCA {auditoria['erro_maximo_agregacao']['ipca']:.2e} e endividamento {auditoria['erro_maximo_agregacao']['endividamento']:.2e}. A auditoria externa desta revisão está documentada a seguir. A data de extração da planilha original não é conhecida; a coincidência com a versão consultada não reconstitui seu histórico de revisões.

- I: informalidade em % dos ocupados, conforme a planilha; não é quantidade de trabalhadores informais.
- π: IPCA acumulado no trimestre em %, calculado por 100 × [∏(1 + IPCA_m/100) − 1].
- E: Endividamento das famílias com o Sistema Financeiro Nacional em relação à renda acumulada em 12 meses (SGS 29037), em %, média dos três meses. Após esta definição, usa-se a abreviação endividamento das famílias. Não é percentual de famílias endividadas nem inadimplência.
- D: 1 de 2020T1 a 2021T4 e 0 nos demais trimestres. São 8 observações com D=1. É uma janela analítica adotada, não uma afirmação de encerramento sanitário ou legal da pandemia.

O IPCA mede a variação dos preços. Sem renda nominal ou real, não se observa diretamente a perda de poder de compra. Para renda nominal fixa, a perda percentual no trimestre seria 100 × [1 − 1/(1 + π/100)], uma transformação da inflação, que não acrescenta informação independente. Não incluir essa transformação junto com o IPCA como se fossem dois canais distintos. Para testar o mecanismo de renda, obter rendimento real e justificar seu papel como variável explicativa ou mediadora.

![Evolução das séries](series.png)

## Auditoria das fontes oficiais

Consulta em {data_consulta}, com datas e horários no fuso America/Sao_Paulo registrados no manifesto. {status_fontes} Além da conferência trimestral, cada um dos 120 meses de IPCA e dos 120 meses de endividamento foi comparado individualmente aos valores da planilha. O arquivo original permanece intacto. As diferenças indicadas são planilha menos fonte oficial, em pontos percentuais; números muito pequenos podem refletir precisão de ponto flutuante.

{tabela_md(fontes_res)}

Informalidade: SIDRA 8529, variável 12466, Brasil (nível territorial N1, código 1), unidade percentual e PNAD Contínua trimestral. Os códigos AAAA01 a AAAA04 representam trimestres civis; não foram utilizadas observações de trimestres móveis sobrepostos. IPCA: SIDRA 1737, variável 63 (variação mensal), Brasil, percentual; meses janeiro–março, abril–junho, julho–setembro e outubro–dezembro compostos dentro do trimestre. Endividamento: SGS 29037, mensal, percentual, agregado pela média dos mesmos três meses.

Conforme a [definição divulgada pelo IBGE](https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/44244-pnad-continua-trimestral-desocupacao-cai-em-18-das-27-ufs-no-segundo-trimestre-de-2025), a proxy de informalidade inclui empregados privados e domésticos sem carteira, empregadores e trabalhadores por conta própria sem CNPJ e trabalhadores familiares auxiliares no trabalho principal. A definição corrente é comum à série consultada. Isso não certifica ausência de mudanças de coleta ou ponderação ao longo do tempo. O IBGE documenta reponderações históricas nas [notas metodológicas da PNAD Contínua](https://www.ibge.gov.br/estatisticas/sociais/trabalho/9173-informalidade.html), incluindo a atualização de pesos em 2025. Usar uma única extração evita combinar versões atuais distintas, mas não permite reconstruir valores de publicações antigas sem os arquivos da época.

As respostas oficiais, URLs, carimbos de extração e SHA-256 estão em [manifesto de fontes](../input/fontes_oficiais/manifesto.json). A conferência individual está em [auditoria trimestral](fontes_trimestres.csv) e [auditoria mensal](fontes_meses.csv), também em abas da planilha. A execução padrão reutiliza esses snapshots; a atualização online é uma ação explícita com --atualizar-fontes.

## Os quatro modelos solicitados
Estimação por mínimos quadrados ordinários com intercepto:

1. M1: I_t = α + βπ π_t + u_t.
2. M2: I_t = α + βE E_t + u_t.
3. M3: I_t = α + βπ π_t + βE E_t + u_t.
4. M4: I_t = α + βπ π_t + βE E_t + δ D_t + u_t.

A hipótese motivadora propõe βπ > 0 e βE > 0, sem impor esses sinais às estimativas. Esses sinais não são necessários em termos teóricos: mudanças na atividade, no crédito e na composição da ocupação podem produzir associações distintas. Os modelos simples estimam associações brutas; M3 e M4 estimam associações parciais. Em M4, δ é um deslocamento médio do intercepto na janela definida, mantendo IPCA e endividamento constantes. A dummy procura captar diferenças na informalidade durante 2020 e 2021 que não são explicadas pelo IPCA e pelo endividamento incluídos. Não estima mudança de inclinação nem isola o efeito causal da pandemia; outros acontecimentos da janela também podem influenciar seu coeficiente.

Todas as variáveis originais estão em escala percentual (38,3 significa 38,3%, não 0,383). Cada β expressa a diferença em pontos percentuais da informalidade associada a +1 ponto percentual na explicativa. Esse coeficiente não é elasticidade. Os erros u_t capturam fatores omitidos.

## Fundamentação da especificação principal

M4 é adotado como referência descritiva principal da apresentação: I_t = α + βπ π_t + βE E_t + δD_t + u_t. A pergunta operacional é se, no mesmo trimestre, a inflação e o nível do endividamento das famílias apresentam associação parcial com a taxa de informalidade, considerada a janela de 2020 e 2021. A escolha organiza os resultados da análise original; não decorre do menor p-valor, do maior R² ou da significância de outro modelo. Ela não transforma a regressão em nível em um modelo temporal validado.

A presença conjunta de π_t e E_t distingue as duas associações: βπ compara observações com o mesmo endividamento e D, enquanto βE compara observações com a mesma inflação e D. São interpretações condicionais da equação estimada, e não comparações experimentais. A variável dependente é uma proporção dos ocupados; por isso, esses parâmetros não medem criação de trabalho informal nem a passagem individual de uma pessoa da formalidade à informalidade.

A inflação pode pressionar o orçamento quando a renda nominal não acompanha os preços, e o indicador dívida/renda pode refletir pressão financeira. Esses mecanismos motivam a pergunta, mas não são identificados pelas variáveis disponíveis. O IPCA não observa renda real, e o endividamento também pode acompanhar expansão de crédito e atividade. Assim, a fundamentação admite sinais ambíguos e não trata o sinal proposto como uma restrição do modelo.

D_t permite um deslocamento médio do intercepto durante os oito trimestres de 2020T1–2021T4, uma janela analítica de perturbação comum ao mercado de trabalho e às variáveis econômicas. Ela mantém inclinações comuns entre períodos e não controla automaticamente todas as mudanças ocorridas nessa janela. A equação permanece parcimoniosa, com intercepto e três regressores em 40 observações; essa parcimônia é uma escolha de escopo e não garante ausência de viés por variáveis omitidas.

M1 e M2 mostram associações brutas; M3 permite examinar as duas variáveis econômicas conjuntamente; M4 acrescenta a janela da pandemia. Essa sequência explica o papel das especificações sem tratar a estabilidade entre elas como teste de robustez causal. D1–D4 descrevem mudanças, com ΔIPCA medindo aceleração inflacionária. R1 descreve associações com defasagens e controles sazonais. R2–R4 exploram tendência e janelas alternativas. São perguntas e sensibilidades complementares; nenhum desses modelos substitui M4 apenas porque tem um teste significativo.

Para fundamentar inferência temporal principal seria necessário justificar melhor a dinâmica e as propriedades das séries e discutir a plausibilidade de exogeneidade em relação aos fatores omitidos. HAC não fornece essas justificativas. Com a evidência atual, a escolha de M4 como referência de apresentação é defensável pela pergunta e pela transparência, enquanto sua interpretação permanece descritiva e condicional. Não há um modelo de longo prazo ou causal estabelecido neste estudo.

## Inferência e hipóteses
Erros-padrão HAC de Newey–West, kernel Bartlett, {lags} defasagens, correção de amostra finita e referência t com graus de liberdade residuais. A janela principal de quatro defasagens cobre até um ano; sensibilidades com uma, duas e quatro defasagens para todos os coeficientes estão em sensibilidade_hac.csv, e para os testes F globais e econômicos em sensibilidade_f_hac.csv. HAC modifica a inferência, não os coeficientes, e não corrige regressão espúria, endogeneidade ou a equação da média.

A tabela principal usa H0: β=0 contra H1: β≠0, IC95% e significância de 5%. O arquivo de coeficientes também apresenta o teste direcional pré-especificado H0: β≤0 contra H1: β>0; para coeficiente negativo, o p unilateral positivo é grande. Não escolher a cauda após observar os resultados. O teste F robusto de M3/M4 avalia H0: βπ=βE=0; rejeitá-lo não implica que ambos sejam positivos ou individualmente significativos. A dummy fica fora dessa restrição conjunta. A amostra pequena exige cautela mesmo com HAC.

## Resultados dos quatro modelos em nível
{tabela_md(principais[['modelo','termo','coeficiente','ep_hac','p_bilateral','ic95_inferior','ic95_superior']])}

{tabela_md(resumo[resumo.modelo.str.startswith('M')][['modelo','n','r2','r2_ajustado','p_f_hac_explicativas']])}

{chr(10).join(leitura(m,t) for m,t in [('M1','ipca'),('M2','endividamento'),('M3','ipca'),('M3','endividamento'),('M4','ipca'),('M4','endividamento'),('M4','pandemia')])}

A interpretação adequada é condicional aos modelos e à qualidade das séries. Ausência de significância não demonstra ausência de associação. Um sinal negativo não significativo tampouco permite afirmar que a dívida reduz a informalidade.

![Coeficientes e intervalos de confiança](coeficientes.png)

## O que os testes permitem concluir

A leitura começa pela magnitude estimada e pelo IC95%, e depois considera o p-valor em relação à hipótese específica. Para um aumento de 1 p.p. em uma explicativa, o coeficiente expressa a associação em p.p. da informalidade, mantidas as demais variáveis da equação. Um intervalo que contém zero representa incerteza sobre direção e magnitude nesta configuração; não demonstra equivalência prática a zero. Não foi definido um limiar de relevância econômica nem realizado teste de equivalência.

{tabela_md(alcance_testes)}

Todos os testes HAC usam referências aproximadas nesta amostra e são condicionais à especificação. Os valores-p apresentados não corrigem a possibilidade de regressão espúria ou de endogeneidade. Por isso, a leitura adequada dos coeficientes econômicos de M4 é de evidência insuficiente nesta configuração para distingui-los de zero, e não de ausência demonstrada de associação na população.

Em R1, o F global e o F econômico respondem a perguntas diferentes. O primeiro inclui controles e dinâmica; o segundo restringe apenas os dois regressores econômicos. O contraste entre seus resultados impede usar a rejeição global como confirmação de que inflação e endividamento estejam associados positivamente à informalidade. Os testes são apresentados integralmente, sem eleger R1 como modelo principal por esse resultado.

As rejeições encontradas em D2–D4 ao usar endividamento de fim de trimestre são sensibilidades exploratórias. A mudança de agregação altera o comportamento da variação do indicador e pode alterar inferência; não é uma confirmação independente, pois usa a mesma amostra mensal. Como há várias especificações e testes sem ajuste por multiplicidade, rejeições isoladas não sustentam uma narrativa confirmatória.

## Gráficos individuais dos quatro modelos

Cada modelo tem um arquivo PNG e um PDF. Os painéis exibem relações estimadas e o ajuste da informalidade ao longo do tempo. M3 e M4 apresentam também contrastes para aumentos individuais e simultâneos de 1 p.p. no IPCA e no endividamento, com intervalos calculados usando a covariância HAC completa. Nos painéis condicionais, a outra explicativa econômica fica na média e os pontos observados são ajustados para esse mesmo valor. Em M4, as curvas distinguem D=0 e D=1; o contraste da dummy compara os grupos com IPCA e endividamento fixos. São associações estimadas, não efeitos causais. As faixas representam a incerteza da média estimada, não a dispersão dos dados individuais.

### M1 — Informalidade e inflação

![Modelo 1 — IPCA](modelo_1_ipca.png)

### M2 — Informalidade e endividamento

![Modelo 2 — Endividamento](modelo_2_endividamento.png)

### M3 — Inflação e endividamento no mesmo modelo

![Modelo 3 — IPCA e endividamento](modelo_3_ipca_endividamento.png)

### M4 — Inflação, endividamento e pandemia

![Modelo 4 — IPCA, endividamento e pandemia](modelo_4_pandemia.png)

![Ajuste e resíduos de M4](ajuste_m4.png)

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

## Sensibilidade da agregação do endividamento

A média trimestral foi mantida porque representa o nível médio do endividamento durante o mesmo intervalo de três meses em que se observa o mercado de trabalho. O último mês representa a posição no encerramento, e não uma média do trimestre. Para separar essa escolha de uma mudança da fonte, esta sensibilidade usa exclusivamente os três valores mensais da planilha original; substitui-se a média por e3, e todas as diferenças e defasagens são reconstruídas.

Os 12 modelos foram reestimados com o endividamento de fim de trimestre, mantendo amostras, equações, dummies e a configuração HAC. {leitura_fim} Essa estabilidade da decisão a 5% em M1–M4 não demonstra equivalência dos parâmetros nem estabilidade nos modelos complementares. M1/D1 não usam endividamento e funcionam como referências invariantes.

{tabela_md(econ_fim[['modelo','termo','coef_media','coef_fim','diferenca_coef','p_media','p_fim','mudou_sinal','mudou_decisao_5pct']])}

![Endividamento médio e de fim de trimestre](sensibilidade_agregacao.png)

{tabela_md(revisao['agregacao_modelos'])}

Nos complementares, a mudança de agregação torna a variação do endividamento significativa em D2–D4 e a defasagem da variação da informalidade significativa em R1. As decisões que mudam estão abaixo. D2 também passa a rejeitar o F global a 5%. Essas alterações mostram sensibilidade material e impedem generalizar a estabilidade de M1–M4 para toda a análise. Não se escolhe o fim de trimestre por produzir significância.

{tabela_md(mudancas_fim[['modelo','termo','coef_media','coef_fim','p_media','p_fim','mudou_decisao_5pct']])}

Coeficientes, erros-padrão, intervalos e decisões de todas as variáveis estão em agregacao_coeficientes.csv. A planilha também contém testes t e F, diagnósticos e multicolinearidade da variante de fim de trimestre. Esta variante passou pela mesma reprodução matricial da especificação original.

## Multicolinearidade — todos os modelos

Os diagnósticos abaixo usam exatamente a matriz de regressores e a amostra efetivamente utilizada em cada modelo, incluindo dummies, tendência e defasagens. O intercepto participa das regressões auxiliares do VIF, mas não recebe classificação. A variável dependente não entra nesta avaliação.

VIF_j = 1/(1 − R²_j), em que R²_j vem da regressão da explicativa j nas demais explicativas e no intercepto. A tolerância é 1/VIF. Como referências descritivas, VIF < 5 indica baixa colinearidade, 5 ≤ VIF < 10 requer atenção e VIF ≥ 10 sinaliza colinearidade elevada (tolerância ≤ 0,10). Nos modelos com apenas uma explicativa, VIF = 1 por construção. As dummies sazonais são avaliadas por coluna, com T1 como referência.

O número de condição é a razão entre o maior e o menor valor singular da matriz das explicativas centradas e padronizadas, excluindo o intercepto; isso evita atribuir às unidades de medida uma colinearidade artificial. Valores de 10 a 30 requerem atenção e ≥ 30 indicam condição elevada. A verificação de posto inclui o intercepto e detecta dependência linear exata; nesse caso, o número de condição é infinito. Os limites são heurísticos, não testes de hipótese com p-valor, e não justificam excluir controles automaticamente. HAC não corrige multicolinearidade.

{leitura_multi}

{tabela_md(multi_modelos)}

{chr(10).join('### Multicolinearidade em ' + modelo + chr(10) + chr(10) + tabela_md(multi_variaveis[multi_variaveis.modelo.eq(modelo)].drop(columns='modelo')) + chr(10) for modelo in MODELOS)}

## Diagnósticos
ADF: H0 de raiz unitária; KPSS: H0 de estacionariedade em torno de constante (c) ou tendência (ct). ADF seleciona até quatro defasagens por AIC; KPSS usa quatro. Os p-valores KPSS são tabelados e os avisos de limites estão preservados em estacionariedade.csv. Com 40 observações, quebras e pandemia reduzem o poder desses testes. Não rejeitar ADF não prova raiz unitária; resultados conflitantes não justificam conclusões automáticas. Os testes c e ct são sensibilidades à parte determinística.

{tabela_md(est[est.deterministico.eq('c')][['variavel','adf_p','adf_lags','kpss_p_tabelado']])}

Na configuração com constante, o ADF não rejeita raiz unitária nas três séries em nível a 5%. O KPSS rejeita estacionariedade do endividamento; para as outras duas séries, os testes não são conclusivos em conjunto. Nas primeiras diferenças, o ADF com constante rejeita raiz unitária nas três séries e o KPSS não rejeita estacionariedade. A sensibilidade com tendência, especialmente para a mudança do endividamento, recomenda cautela. Esses resultados favorecem examinar variações, sem certificar automaticamente uma especificação.

Breusch–Godfrey (quatro defasagens) testa H0 de ausência de autocorrelação residual; Breusch–Pagan testa H0 de homocedasticidade. Seus p-valores usuais são diagnósticos aproximados nesta amostra; BP é particularmente sensível à dependência temporal. VIF avalia colinearidade entre os regressores; o intercepto não é reportado.

{tabela_md(diag[diag.modelo.str.startswith('M')].drop_duplicates('modelo')[['modelo','bg_lm_p_4','bp_lm_p']])}

Nos quatro modelos em nível, Breusch–Godfrey rejeita ausência de autocorrelação a 5%; há dependência temporal residual relevante. Os VIFs das explicativas de M4 são próximos de 1, de modo que colinearidade não parece ser o principal problema nesta especificação. O uso de HAC deve ser acompanhado da discussão sobre a dinâmica e a estacionariedade, e não apenas da tabela de significância.

Se há persistência/tendência não resolvida, os resultados em nível não devem fundamentar a conclusão principal. Em etapas posteriores, considerar ARDL/ECM e cointegração apenas após justificar a ordem de integração e excluir séries I(2); erros HAC por si só não tornam uma regressão em nível válida. As variações e defasagens aqui são verificações exploratórias, não prova de que todos os problemas foram resolvidos.

## Aprofundamento das propriedades temporais

Foram acrescentadas sensibilidades ADF com seleção AIC até 1, 2 e 4 defasagens e KPSS com 1, 2 e 4 defasagens, com constante (c) ou constante e tendência (ct), para níveis, primeiras e segundas diferenças. A segunda diferença é apenas um diagnóstico complementar; não é uma nova especificação principal, e a rejeição de raiz unitária nela não prova que a série original seja I(2). Os resultados completos e avisos de limites do KPSS estão em estacionariedade_sens.csv.

A tabela resume a faixa de p-valores entre as seis especificações de cada transformação; 0 indica nível, 1 primeira diferença e 2 segunda diferença. Mínimos e máximos descrevem sensibilidade e não constituem critérios de seleção pelo menor p-valor. Os p-valores KPSS são tabelados e podem estar nos limites publicados; os avisos completos foram preservados.

{tabela_md(resumo_integracao)}

O IPCA em nível rejeita raiz unitária em parte das especificações curtas do ADF, mas não na principal; portanto, não se impõe uma classificação automática como I(1). As primeiras diferenças de informalidade e IPCA apresentam rejeição ADF nas sensibilidades examinadas. A primeira diferença do endividamento tem decisões ADF e KPSS sensíveis às defasagens e à tendência. A ordem de integração do endividamento permanece incerta com esta amostra; os diagnósticos não demonstram automaticamente I(1) ou I(2).

Acrescentou-se Zivot–Andrews, com uma quebra endógena, corte de 15% em cada extremidade e seleção AIC até quatro defasagens, nos níveis, com c e ct. H0: raiz unitária sem quebra; alternativa: estacionariedade com uma quebra na parte determinística especificada. Os p-valores são aproximados. A data retornada é uma candidata escolhida pelo teste, não uma data confirmada de ruptura e nem o início causal da pandemia. A implementação usa a [aproximação documentada pelo statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.zivot_andrews.html). Não testar repetidamente até obter rejeição.

{tabela_md(revisao['quebras_za'])}

A evidência de quebra para endividamento depende da parte determinística; não resolve sozinha a classificação da série. Não se aplicou cointegração ou ARDL/ECM mecanicamente: a incerteza de integração, a possibilidade de quebras e a amostra curta impedem justificar esses procedimentos nesta revisão. Assim, relações de longo prazo permanecem não estabelecidas, e os níveis continuam descritivos. A inclusão de ΔIPCA em D1–D4 mede aceleração/desaceleração da inflação, não o mesmo mecanismo do IPCA em nível ou defasado de R1.

## Reprodução dos 12 modelos e diagnósticos complementares

Um módulo separado reconstrói as matrizes e as amostras diretamente das séries originais, usando especificações explícitas, sem o construtor de fórmulas. Os coeficientes são recalculados por mínimos quadrados com NumPy e a covariância HAC pela soma dos produtos dos escores, pesos Bartlett 1 − h/(L+1) e correção n/(n−k). Testes t, IC95% e todos os testes F individuais e conjuntos são reconstruídos com distribuições da SciPy. Foram verificadas as matrizes inteiras de covariância, e não apenas a diagonal. As diferenças numéricas máximas abaixo não são erros-padrão; medem a concordância entre dois caminhos de cálculo.

{tabela_md(verificacao[['modelo','n','inicio','fim','observacoes_perdidas','gl_residuais','erro_max_coef','erro_max_cov_hac','erro_max_t','erro_max_p','erro_max_f','status']])}

M1–M4, R2–R4 usam 40 observações; D1–D4 perdem o primeiro trimestre e usam 39; R1 perde os dois primeiros e usa 38. Em D4, ΔD registra +1 em 2020T1 e −1 em 2022T1; em R1, D permanece em nível. R3/R4 mantêm suas janelas alternativas apenas como sensibilidade. O trimestre T1 é a referência sazonal. As linhas utilizadas constam em reproducao_modelos.csv; os coeficientes e as covariâncias recalculados estão em reproducao_coeficientes.csv e reproducao_covariancias.csv. A reprodução não depende dos testes de estacionariedade e não os substitui.

Breusch–Godfrey, Breusch–Pagan (versão Koenker usada pelo pipeline) e VIF também foram reproduzidos por regressões auxiliares. BG testa ausência de autocorrelação até quatro defasagens. Em modelos com dependente defasada, continuam sendo diagnósticos aproximados. BP testa homocedasticidade e não é uma garantia contra outras formas de má especificação.

{tabela_md(diag_todos)}

![Autocorrelação residual dos 12 modelos](autocorrelacao_modelos.png)

Os correlogramas usam até oito defasagens; as faixas são referências aproximadas e não substituem BG ou uma modelagem dinâmica. D1–D4 e R1 não apresentam rejeição de BG a 5% nesta configuração, mas isso não comprova ausência de dependência. BP aponta heterocedasticidade em D2, D3 e R1. O padrão de rejeição de BG em R1 difere do encontrado nos níveis, mas as dependentes e as amostras também diferem. Essa comparação não isola o papel das defasagens nem demonstra melhoria causal ou superioridade de R1. O F global de R1 inclui controles e sazonalidade: sua rejeição não demonstra que inflação e endividamento sejam conjuntamente significativos. O modelo R2 exige cautela adicional pela colinearidade de endividamento e tendência.

## Limites de especificação e próximos passos

Os modelos atuais não incluem desemprego, atividade, rendimento real, composição setorial, juros ou transferências. A base fornecida não contém esses controles; eles não foram imputados. Sua omissão pode enviesar coeficientes quando se relacionam ao regressor e à informalidade. Por exemplo, uma expansão de atividade pode elevar crédito e emprego formal simultaneamente, produzindo associação negativa entre dívida e informalidade sem um efeito protetor da dívida.

O indicador de endividamento pode aumentar por expansão das dívidas, queda da renda no denominador ou ambos. Ele não mede inadimplência nem a proporção de famílias com dívida. O IPCA mede preços; para estudar poder de compra diretamente seria necessário rendimento real, com nova especificação e atenção à simultaneidade com a ocupação. Não se acrescentaram controles para procurar significância.

Uma ampliação posterior exige selecionar poucos controles com justificativa teórica, obter séries compatíveis e documentar suas versões. Relações de longo prazo e escolhas de defasagem devem depender das propriedades dessas séries e da pergunta econômica, preservando graus de liberdade. Esta revisão conclui a conferência da versão atual dos dados e a reprodução numérica; M4 permanece a referência descritiva de apresentação, enquanto sua fundamentação como modelo principal de inferência temporal continua limitada pela dinâmica, integração e identificação econômica.

## Conclusão para o trabalho

M4 reúne inflação, endividamento das famílias e a dummy 2020T1–2021T4 como referência descritiva principal da pergunta sobre associações no mesmo trimestre. Seus coeficientes econômicos e os de M1–M3 não são distinguíveis de zero a 5% pelos testes bilaterais HAC nesta configuração, e seus intervalos de confiança incluem zero. Essa evidência é inconclusiva quanto à direção e à magnitude das associações; não demonstra inexistência de relação nem confirma a hipótese de que ambas sejam positivas. A interpretação permanece condicional, porque os diagnósticos temporais não estabeleceram a adequação dos modelos em nível.

Os complementares não sustentam uma conclusão mais forte: o F global de R1 não equivale ao teste conjunto dos regressores econômicos, e as rejeições em diferenças dependem da agregação do endividamento. Nenhuma especificação foi promovida a principal com base em significância isolada. As observações coincidem com as fontes consultadas e os cálculos foram reproduzidos, mas essas conferências não validam uma relação causal ou de longo prazo.

O alcance deste estudo é descrever estimativas condicionais, sua incerteza e sua sensibilidade. Para sustentar inferência temporal mais forte seria necessário fundamentar a dinâmica, esclarecer as propriedades das séries e justificar controles econômicos e hipóteses de identificação. O IPCA não mede diretamente poder de compra, e o indicador de endividamento não mede inadimplência. Portanto, os resultados atuais não fundamentam recomendações de elevar ou reduzir inflação ou dívida como forma de alterar a informalidade.

## Testes t e F completos — todos os modelos e coeficientes

Os testes usam a mesma covariância HAC descrita acima. Cada teste t é bilateral: H0: coeficiente = 0 versus H1: coeficiente ≠ 0. Incluem-se intercepto, variáveis econômicas, dummies, tendência, defasagens e cada contraste sazonal (T2, T3 e T4 em relação a T1). A variável dependente não recebe teste t como regressor. Rejeita-se H0 quando p < 0,05; não rejeitar não prova que o coeficiente seja zero. Os valores críticos e graus de liberdade estão nos CSVs e na planilha.

O F individual testa a mesma hipótese do t bilateral, com uma restrição: F = t² e os p-valores coincidem. O F global testa todos os coeficientes exceto o intercepto conjuntamente, incluindo os controles. O F econômico mantém a restrição anterior apenas sobre inflação e/ou endividamento. Para R1 e R2, há também F do bloco de sazonalidade. Rejeitar um teste conjunto indica que ao menos um dos coeficientes testados difere de zero, sem determinar qual ou seu sinal. Os p-valores são por teste, sem ajuste por comparações múltiplas; a referência F com HAC é aproximada em amostras finitas.

{chr(10).join('### ' + modelo + ' — ' + MODELOS[modelo] + chr(10) + chr(10) + tabela_md(testes_t[testes_t.modelo.eq(modelo)][['termo','coeficiente','ep_hac','t_hac','gl','p_bilateral','decisao_5pct']]) + chr(10) + chr(10) + tabela_md(testes_f[testes_f.modelo.eq(modelo)][['tipo','termos','f_hac','gl_numerador','gl_denominador','p_valor','decisao_5pct']]) + chr(10) for modelo in MODELOS)}

## Reprodutibilidade e referências
Base fornecida pelo usuário; metadados e SHA-256 em auditoria.json. A aba de metodologia informa SIDRA 8529 (informalidade), SIDRA 1737 (IPCA) e SGS 29037 (endividamento). Não foram substituídos dados da planilha por dados externos. As APIs SIDRA e BCB foram consultadas nesta revisão; resultados e rastreabilidade estão na seção de auditoria oficial. A planilha de entrada não foi alterada. A concordância com a extração atual não certifica todas as publicações históricas nem a adequação econométrica.

- [Informalidade — SIDRA 8529](https://sidra.ibge.gov.br/tabela/8529).
- [IPCA — SIDRA 1737](https://sidra.ibge.gov.br/tabela/1737).
- [BCB — SGS 29037](https://dadosabertos.bcb.gov.br/dataset/29037-endividamento-das-familias-com-o-sistema-financeiro-nacional-em-relacao-a-renda-acumulada-dos).
- [statsmodels — covariâncias robustas e HAC](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html).
- [statsmodels — teste ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html).
- [statsmodels — Zivot–Andrews e aproximação da implementação](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.zivot_andrews.html).
- [IBGE — divulgação trimestral e notas metodológicas](https://www.ibge.gov.br/estatisticas/sociais/trabalho/9173-informalidade.html).
- [IBGE — definição da informalidade e divulgação trimestral de 2025](https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/44244-pnad-continua-trimestral-desocupacao-cai-em-18-das-27-ufs-no-segundo-trimestre-de-2025).

'''
    # Mantém a conclusão descritiva compatível com os resultados recebidos.
    if not (principais[principais.termo.isin(['ipca','endividamento'])].p_bilateral >= .05).all():
        texto = texto.replace('Seus coeficientes econômicos e os de M1–M3 não são distinguíveis de zero a 5% pelos testes bilaterais HAC nesta configuração, e seus intervalos de confiança incluem zero. Essa evidência é inconclusiva quanto à direção e à magnitude das associações; não demonstra inexistência de relação nem confirma a hipótese de que ambas sejam positivas.',
                              'Há coeficientes econômicos significativos nesta configuração. A leitura deve distinguir os sinais, os intervalos e os modelos indicados nas tabelas; significância isolada não estabelece que ambas as associações sejam positivas nem valida a especificação temporal.')
    texto = re.sub(r'(?m)^(#{1,6} [^\n]+)\n(?!\n)', r'\1\n\n', texto).rstrip() + '\n'
    (saida / 'relatorio.md').write_text(texto, encoding='utf-8')
    escrever_html(texto, saida, testes_t, testes_f, multi_modelos, leitura_multi)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arquivo', type=Path, default=ARQUIVO)
    parser.add_argument('--saida', type=Path, default=ROOT / 'data/output')
    parser.add_argument('--hac-lags', type=int, choices=range(1, 5), default=4)
    parser.add_argument('--atualizar-fontes', action='store_true', help='Consulta as APIs oficiais e atualiza os snapshots de auditoria.')
    args = parser.parse_args(argv)
    if args.atualizar_fontes:
        coletar()
    d, auditoria = ler_base(args.arquivo)
    ajustes, coefs, resumo, diag, sens = estimar(d, args.hac_lags)
    testes_t, testes_f = testes_significancia(ajustes, coefs)
    multi_variaveis, multi_modelos = multicolinearidade(ajustes)
    est = estacionariedade(d)
    fontes_tri, fontes_mes, fontes_res, base_oficial, manifesto = auditar_fontes(d, args.arquivo)
    verificacao, verificacao_coefs, verificacao_cov = reproduzir(d, ajustes, testes_f, args.hac_lags, diag)
    est_sens, quebras = aprofundar_estacionariedade(d)
    agreg_coefs, agreg_modelos, base_fim, ajustes_fim, coefs_fim, modelos_fim, diag_fim = sensibilidade_agregacao(
        d, args.arquivo, ajustes, estimar, preparar, args.hac_lags)
    tt_fim, tf_fim = testes_significancia(ajustes_fim, coefs_fim)
    multi_fim, multi_modelos_fim = multicolinearidade(ajustes_fim)
    reproduzir(base_fim, ajustes_fim, tf_fim, args.hac_lags, diag_fim)
    revisao = {'fontes_resumo': fontes_res, 'fontes_trimestres': fontes_tri, 'fontes_meses': fontes_mes,
               'base_oficial_conferida': base_oficial, 'reproducao_modelos': verificacao,
               'reproducao_coeficientes': verificacao_coefs, 'reproducao_covariancias': verificacao_cov,
               'estacionariedade_sens': est_sens, 'quebras_za': quebras,
               'agregacao_coeficientes': agreg_coefs, 'agregacao_modelos': agreg_modelos,
               'base_fim_trimestre': base_fim.drop(columns='periodo'), 'coeficientes_fim': coefs_fim,
               'modelos_fim': modelos_fim, 'diagnosticos_fim': diag_fim, 'testes_t_fim': tt_fim,
               'testes_f_fim': tf_fim, 'multicolinearidade_fim': multi_fim,
               'colinearidade_modelos_fim': multi_modelos_fim, 'sensibilidade_f_hac': sensibilidade_f_hac(ajustes, args.hac_lags)}
    auditoria['fontes_oficiais'] = manifesto
    auditoria['resultado_conferencia_oficial'] = fontes_res.to_dict('records')
    auditoria['validacao'] = ('Comparação com a versão oficial consultada: ver resultado_conferencia_oficial; '
                            'a reprodução numérica dos 12 modelos passou. Adequação temporal e identificação causal não certificadas.')

    args.saida.mkdir(parents=True, exist_ok=True)
    exportar = d.drop(columns='periodo')
    descritivas = d[VARIAVEIS].describe().rename_axis('estatistica').reset_index()
    correlacoes = d[VARIAVEIS].corr().rename_axis('variavel').reset_index()
    tabelas = {'multicolinearidade': multi_variaveis, 'colinearidade_modelos': multi_modelos, 'testes_t': testes_t, 'testes_f': testes_f, 'base_trimestral': exportar, 'coeficientes': coefs, 'modelos': resumo,
               'diagnosticos': diag, 'sensibilidade_hac': sens, 'estacionariedade': est,
               'descritivas': descritivas, 'correlacoes': correlacoes, **revisao}
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
    graficos_revisao(ajustes, agreg_coefs, args.saida)
    escrever_relatorio(d, auditoria, coefs, resumo, diag, est, args.saida, args.hac_lags, testes_t, testes_f, multi_variaveis, multi_modelos, revisao)
    print(resumo[resumo.modelo.str.startswith('M')].to_string(index=False))
    print(f'\nRelatório: {args.saida / "relatorio.html"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
