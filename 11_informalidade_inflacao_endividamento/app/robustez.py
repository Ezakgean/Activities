"""Verificações adicionais motivadas pelo parecer técnico."""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews


def aprofundar_estacionariedade(d):
    linhas, quebras = [], []
    for variavel in ['informalidade','ipca','endividamento']:
        for ordem in [0,1,2]:
            serie = d[variavel].copy()
            for _ in range(ordem):
                serie = serie.diff()
            serie = serie.dropna()
            for deterministico in ['c','ct']:
                for limite in [1,2,4]:
                    adf = adfuller(serie, maxlag=limite, regression=deterministico, autolag='AIC')
                    with warnings.catch_warnings(record=True) as avisos:
                        warnings.simplefilter('always')
                        kp = kpss(serie, regression=deterministico, nlags=limite)
                    linhas.append({'variavel': variavel, 'ordem_diferenca': ordem,
                                   'deterministico': deterministico, 'limite_lags': limite,
                                   'n': len(serie), 'adf_estatistica': adf[0], 'adf_p': adf[1],
                                   'adf_lags': adf[2], 'kpss_estatistica': kp[0], 'kpss_p_tabelado': kp[1],
                                   'adf_rejeita_5pct': adf[1] < .05, 'kpss_rejeita_5pct': kp[1] < .05,
                                   'kpss_aviso': ' | '.join(str(a.message) for a in avisos)})
        for deterministico in ['c','ct']:
            za = zivot_andrews(d[variavel], trim=.15, maxlag=4, regression=deterministico, autolag='AIC')
            quebras.append({'variavel': variavel, 'deterministico': deterministico,
                            'za_estatistica': za[0], 'za_p_aproximado': za[1], 'critico_5pct': za[2]['5%'],
                            'lags': za[3], 'trimestre_quebra_candidato': d.trimestre.iloc[za[4]],
                            'rejeita_raiz_unitaria_5pct': za[0] < za[2]['5%']})
    return pd.DataFrame(linhas), pd.DataFrame(quebras)


def sensibilidade_agregacao(d, arquivo, ajustes, estimar, preparar, lags=4):
    mensal = pd.read_excel(arquivo, sheet_name='Dados mensais')
    mensal.columns = ['trimestre','p1','p2','p3','e1','e2','e3']
    alternativa = d[['trimestre','informalidade','ipca','endividamento']].copy()
    alternativa['endividamento'] = alternativa.trimestre.map(mensal.set_index('trimestre').e3)
    alternativa = preparar(alternativa)
    r_alt, coefs_alt, resumo_alt, diag_alt, _ = estimar(alternativa, lags)
    coefs, modelos = [], []
    for nome, r in ajustes.items():
        alt = r_alt[nome]
        for i, termo in enumerate(r.model.exog_names):
            coefs.append({'modelo': nome, 'termo': termo,
                          'coef_media': r.params[i], 'coef_fim': alt.params[i],
                          'diferenca_coef': alt.params[i]-r.params[i],
                          'ep_media': r.bse[i], 'ep_fim': alt.bse[i],
                          'p_media': r.pvalues[i], 'p_fim': alt.pvalues[i],
                          'ic95_fim_inferior': alt.conf_int()[i,0], 'ic95_fim_superior': alt.conf_int()[i,1],
                          'mudou_sinal': bool(np.sign(r.params[i]) != np.sign(alt.params[i])),
                          'mudou_decisao_5pct': bool((r.pvalues[i] < .05) != (alt.pvalues[i] < .05))})
        indices = [i for i,n in enumerate(r.model.exog_names) if n != 'Intercept']
        restricao = np.eye(len(r.params))[indices]
        original_f, alt_f = r.f_test(restricao), alt.f_test(restricao)
        diagnostico = diag_alt[diag_alt.modelo.eq(nome)].iloc[0]
        modelos.append({'modelo': nome, 'n_media': int(r.nobs), 'n_fim': int(alt.nobs),
                        'r2_media': r.rsquared, 'r2_fim': alt.rsquared,
                        'p_f_global_media': float(original_f.pvalue), 'p_f_global_fim': float(alt_f.pvalue),
                        'bg_p_fim': diagnostico.bg_lm_p_4, 'bp_p_fim': diagnostico.bp_lm_p})
    return pd.DataFrame(coefs), pd.DataFrame(modelos), alternativa, r_alt, coefs_alt, resumo_alt, diag_alt


def sensibilidade_f_hac(ajustes, lags):
    linhas = []
    economicas = {'ipca','endividamento','d_ipca','d_endividamento','ipca_lag1','d_endividamento_lag1'}
    for modelo, r in ajustes.items():
        for lag in sorted({1,2,4,lags}):
            alt = r.get_robustcov_results(cov_type='HAC',maxlags=lag,use_correction=True,use_t=True)
            for tipo in ['global','economicas']:
                indices = [i for i,n in enumerate(r.model.exog_names)
                           if (n != 'Intercept' if tipo == 'global' else n in economicas)]
                teste = alt.f_test(np.eye(len(r.params))[indices])
                linhas.append({'modelo': modelo, 'hac_lags': lag, 'tipo': tipo,
                               'f_hac': float(np.asarray(teste.fvalue).item()), 'p_valor': float(teste.pvalue)})
    return pd.DataFrame(linhas)
