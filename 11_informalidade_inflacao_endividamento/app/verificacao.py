"""Reprodução matricial dos 12 modelos, sem o estimador ou a covariância do statsmodels."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

ESPECIFICACOES = {
 'M1': ('informalidade', ['ipca']), 'M2': ('informalidade', ['endividamento']),
 'M3': ('informalidade', ['ipca','endividamento']),
 'M4': ('informalidade', ['ipca','endividamento','pandemia']),
 'D1': ('d_informalidade', ['d_ipca']), 'D2': ('d_informalidade', ['d_endividamento']),
 'D3': ('d_informalidade', ['d_ipca','d_endividamento']),
 'D4': ('d_informalidade', ['d_ipca','d_endividamento','d_pandemia']),
 'R1': ('d_informalidade', ['C(trimestre_num)[T.2]','C(trimestre_num)[T.3]','C(trimestre_num)[T.4]',
                          'd_informalidade_lag1','ipca_lag1','d_endividamento_lag1','pandemia']),
 'R2': ('informalidade', ['C(trimestre_num)[T.2]','C(trimestre_num)[T.3]','C(trimestre_num)[T.4]',
                        'ipca','endividamento','pandemia','tendencia']),
 'R3': ('informalidade', ['ipca','endividamento','pandemia_nucleo']),
 'R4': ('informalidade', ['ipca','endividamento','pandemia_ampla']),
}


def matriz_independente(d, modelo):
    periodos = pd.PeriodIndex(d.trimestre.str.replace('T','Q'), freq='Q')
    consecutivo = np.r_[False, np.diff(periodos.asi8) == 1]
    def diferenca(x):
        return np.where(consecutivo, np.r_[np.nan, np.diff(x)], np.nan)
    def defasagem(x):
        return np.where(consecutivo, np.r_[np.nan, x[:-1]], np.nan)
    colunas = {v: d[v].to_numpy(float) for v in ['informalidade','ipca','endividamento']}
    for nome, inicio, fim in [('pandemia','2020Q1','2021Q4'),
                              ('pandemia_nucleo','2020Q2','2021Q4'), ('pandemia_ampla','2020Q1','2023Q2')]:
        colunas[nome] = np.array((periodos >= pd.Period(inicio)) & (periodos <= pd.Period(fim)), dtype=float)
    for v in ['informalidade','ipca','endividamento','pandemia']:
        colunas['d_'+v] = diferenca(colunas[v])
    for v in ['ipca','d_informalidade','d_endividamento']:
        colunas[v+'_lag1'] = defasagem(colunas[v])
    colunas['tendencia'] = periodos.asi8 - periodos.asi8.min()
    for q in [2,3,4]:
        colunas[f'C(trimestre_num)[T.{q}]'] = (periodos.quarter == q).astype(float)
    dependente, regressores = ESPECIFICACOES[modelo]
    nomes = ['Intercept'] + regressores
    x = np.column_stack([np.ones(len(d))] + [colunas[n] for n in regressores])
    y = colunas[dependente]
    manter = np.isfinite(x).all(axis=1) & np.isfinite(y)
    return x[manter], y[manter], nomes, d.trimestre.to_numpy()[manter]


def ajuste_matricial(x, y, lags):
    n, k = x.shape
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ beta
    bread = np.linalg.inv(x.T @ x)
    scores = x * resid[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags+1):
        gamma = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag/(lags+1)) * (gamma + gamma.T)
    cov = bread @ meat @ bread * n/(n-k)
    ep = np.sqrt(np.diag(cov))
    t = beta/ep
    p = 2 * stats.t.sf(np.abs(t), n-k)
    margem = stats.t.ppf(.975, n-k)*ep
    return beta, cov, t, p, np.column_stack([beta-margem,beta+margem]), resid


def r2_auxiliar(x, y):
    erro = y - x @ np.linalg.lstsq(x, y, rcond=None)[0]
    return 1 - (erro @ erro)/np.sum((y-y.mean())**2)


def reproduzir(d, ajustes, testes_f, lags=4, diagnosticos=None):
    resumos, detalhes, covs = [], [], []
    for nome, r in ajustes.items():
        x, y, nomes, periodos = matriz_independente(d, nome)
        beta, cov, t, p, ic, resid = ajuste_matricial(x, y, lags)
        n, k = x.shape
        # Checagens das matrizes impedem que um erro de transformação seja mascarado pelo reestimador.
        np.testing.assert_allclose(x, r.model.exog, atol=1e-12, rtol=0)
        np.testing.assert_allclose(y, r.model.endog, atol=1e-12, rtol=0)
        assert nomes == r.model.exog_names
        assert n == r.nobs and n-k == r.df_resid
        np.testing.assert_allclose(beta, r.params, atol=1e-9, rtol=1e-8)
        np.testing.assert_allclose(cov, r.cov_params(), atol=1e-8, rtol=1e-7)
        np.testing.assert_allclose(t, r.tvalues, atol=1e-7, rtol=1e-7)
        np.testing.assert_allclose(p, r.pvalues, atol=1e-8, rtol=1e-7)
        np.testing.assert_allclose(ic, r.conf_int(), atol=1e-7, rtol=1e-7)
        for i, termo in enumerate(nomes):
            detalhes.append({'modelo': nome, 'termo': termo, 'coeficiente_recalculado': beta[i],
                             'ep_hac_recalculado': np.sqrt(cov[i,i]), 't_recalculado': t[i],
                             'p_recalculado': p[i], 'ic95_inferior': ic[i,0], 'ic95_superior': ic[i,1]})
            for j, outro in enumerate(nomes):
                covs.append({'modelo': nome, 'termo_linha': termo, 'termo_coluna': outro,
                             'cov_hac': r.cov_params()[i,j], 'cov_recalculada': cov[i,j],
                             'erro_absoluto': abs(cov[i,j]-r.cov_params()[i,j])})
        erros_f = []
        for row in testes_f[testes_f.modelo.eq(nome)].itertuples():
            termos = row.termos.split(' + ')
            indices = [nomes.index(t) for t in termos]
            estatistica = beta[indices] @ np.linalg.solve(cov[np.ix_(indices,indices)], beta[indices]) / len(indices)
            pvalor = stats.f.sf(estatistica,len(indices),n-k)
            np.testing.assert_allclose([estatistica,pvalor], [row.f_hac,row.p_valor],atol=1e-7,rtol=1e-7)
            erros_f.append(abs(estatistica-row.f_hac))
        # LM de BG com quatro lags preenchidos por zero no início, como no pipeline principal.
        lagged = np.column_stack([np.r_[np.zeros(lag), resid[:-lag]] for lag in range(1,5)])
        bg_r2 = r2_auxiliar(np.column_stack([x,lagged]),resid)
        bg_p = stats.chi2.sf(n*bg_r2,4)
        bp_p = stats.chi2.sf(n*r2_auxiliar(x,resid**2),k-1)
        vif = [1/(1-r2_auxiliar(np.delete(x,j,axis=1),x[:,j])) for j in range(1,k)]
        if diagnosticos is not None:
            conferidos = diagnosticos[diagnosticos.modelo.eq(nome)]
            np.testing.assert_allclose(conferidos.bg_lm_p_4, bg_p, atol=1e-8, rtol=1e-7)
            np.testing.assert_allclose(conferidos.bp_lm_p, bp_p, atol=1e-8, rtol=1e-7)
            for i, termo in enumerate(nomes[1:]):
                np.testing.assert_allclose(conferidos[conferidos.termo.eq(termo)].vif,
                                           vif[i], atol=1e-8, rtol=1e-7)
        resumos.append({'modelo': nome, 'n': n, 'inicio': periodos[0], 'fim': periodos[-1],
                        'observacoes_perdidas': len(d)-n, 'gl_residuais': n-k, 'trimestres_utilizados': ', '.join(periodos),
                        'erro_max_coef': max(abs(beta-r.params)),
                        'erro_max_cov_hac': np.max(abs(cov-r.cov_params())),
                        'erro_max_t': max(abs(t-r.tvalues)), 'erro_max_p': max(abs(p-r.pvalues)),
                        'erro_max_f': max(erros_f), 'bg_lm_p_4_recalculado': bg_p,
                        'bp_lm_p_recalculado': bp_p, 'vif_max_recalculado': max(vif),
                        'status': 'Reproduzido numericamente'})
    return pd.DataFrame(resumos), pd.DataFrame(detalhes), pd.DataFrame(covs)
