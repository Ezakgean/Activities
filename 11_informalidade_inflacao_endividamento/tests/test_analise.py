"""Verificações de integridade, calendário e hipóteses do pipeline."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy import stats

from app.analise import ARQUIVO, ler_base, preparar, estimar, testes_significancia, MODELOS, diagnosticar_multicolinearidade, multicolinearidade


class Integridade(unittest.TestCase):
    def test_base_e_agregacao_original(self):
        d, audit = ler_base(ARQUIVO)
        self.assertEqual(len(d), 40)
        self.assertEqual(d.pandemia.sum(), 8)
        self.assertEqual(d.pandemia_nucleo.sum(), 7)
        self.assertEqual(d.pandemia_ampla.sum(), 14)
        self.assertEqual(d.d_informalidade.notna().sum(), 39)
        self.assertEqual(d.d_informalidade_lag1.notna().sum(), 38)
        self.assertEqual(d.loc[d.trimestre.eq('2020T1'), 'pandemia'].item(), 1)
        self.assertEqual(d.loc[d.trimestre.eq('2022T1'), 'pandemia'].item(), 0)
        self.assertLess(audit['erro_maximo_agregacao']['ipca'], 1e-8)

    def test_nao_diferencia_nem_defasa_atraves_de_lacuna(self):
        dados = pd.DataFrame({'trimestre': ['2019T4', '2020T1', '2020T3', '2020T4'],
                             'informalidade': [40, 39, 38, 39], 'ipca': [1, 2, 3, 4],
                             'endividamento': [40, 41, 42, 43]})
        d = preparar(dados)
        self.assertTrue(np.isnan(d.loc[2, 'd_informalidade']))
        self.assertTrue(np.isnan(d.loc[2, 'ipca_lag1']))
        self.assertTrue(np.isnan(d.loc[3, 'd_informalidade_lag1']))
        self.assertEqual(d.loc[3, 'd_informalidade'], 1)
        with self.assertRaisesRegex(ValueError, 'duplicados'):
            preparar(pd.concat([dados, dados.iloc[[0]]]))

    def test_detecta_agregacao_incorreta_e_mes_ausente(self):
        with tempfile.TemporaryDirectory() as temp:
            arquivo = Path(temp) / 'alterada.xlsx'
            # Materializa os valores: salvar fórmulas com openpyxl apaga seu cache.
            wb = openpyxl.load_workbook(ARQUIVO, data_only=True)
            wb['Dados mensais']['B2'] = 10
            wb.save(arquivo)
            with self.assertRaisesRegex(ValueError, 'inconsistente'):
                ler_base(arquivo)
            wb['Dados mensais']['B2'] = None
            wb.save(arquivo)
            with self.assertRaisesRegex(ValueError, 'ausentes'):
                ler_base(arquivo)

    def test_estimacao_e_cauda_da_hipotese_positiva(self):
        d, _ = ler_base(ARQUIVO)
        ajustes, coefs, resumo, _, _ = estimar(d)
        esperado = np.linalg.lstsq(np.column_stack([np.ones(40), d.ipca]), d.informalidade, rcond=None)[0]
        np.testing.assert_allclose(ajustes['M1'].params, esperado, atol=1e-10)
        self.assertEqual(resumo.set_index('modelo').loc['R1', 'n'], 38)
        r = coefs[coefs.modelo.eq('M2') & coefs.termo.eq('endividamento')].iloc[0]
        self.assertLess(r.coeficiente, 0)
        self.assertGreater(r.p_unilateral_positivo, .5)
        self.assertAlmostEqual(r.p_unilateral_positivo, stats.t.sf(r.t_hac, 38))
        d4 = ajustes['D4'].model.data.frame.dropna(subset=['d_informalidade','d_ipca','d_endividamento','d_pandemia'])
        self.assertEqual(d4.loc[d4.trimestre.eq('2020T1'), 'd_pandemia'].item(), 1)
        self.assertEqual(d4.loc[d4.trimestre.eq('2022T1'), 'd_pandemia'].item(), -1)

    def test_testes_t_f_cobrem_todos_os_coeficientes_e_modelos(self):
        d, _ = ler_base(ARQUIVO)
        ajustes, coefs, _, _, _ = estimar(d)
        tt, tf = testes_significancia(ajustes, coefs)
        self.assertEqual(set(tt.modelo), set(MODELOS))
        self.assertEqual(len(tt), sum(len(r.params) for r in ajustes.values()))
        individuais = tf[tf.tipo.eq('individual')].rename(columns={'termos': 'termo'})
        comparacao = tt.merge(individuais, on=['modelo', 'termo'], validate='one_to_one')
        self.assertEqual(len(comparacao), len(tt))
        np.testing.assert_allclose(comparacao.f_hac, comparacao.t_hac ** 2, rtol=1e-10)
        np.testing.assert_allclose(comparacao.p_valor, comparacao.p_bilateral, atol=1e-12)
        for modelo, r in ajustes.items():
            global_ = tf[tf.modelo.eq(modelo) & tf.tipo.eq('global')].iloc[0]
            self.assertEqual(global_.gl_numerador, len(r.params) - 1)
            self.assertEqual(global_.gl_denominador, r.df_resid)
            nomes = r.model.exog_names
            indices = [j for j, n in enumerate(nomes) if n != 'Intercept']
            beta = r.params[indices]
            cov = r.cov_params()[np.ix_(indices, indices)]
            esperado = beta @ np.linalg.solve(cov, beta) / len(indices)
            self.assertAlmostEqual(global_.f_hac, esperado, places=7)
            self.assertAlmostEqual(global_.p_valor, stats.f.sf(esperado, len(indices), r.df_resid))
        self.assertEqual(set(tf[tf.tipo.eq('sazonalidade')].modelo), {'R1', 'R2'})

    def test_multicolinearidade_independencia_e_dependencia_exata(self):
        x = np.array([-1., -1., 1., 1.])
        y = np.array([-1., 1., -1., 1.])
        linhas, resumo = diagnosticar_multicolinearidade(
            np.column_stack([np.ones(4), x, y]), ['Intercept', 'x', 'y'])
        np.testing.assert_allclose([l['vif'] for l in linhas], [1, 1])
        self.assertAlmostEqual(resumo['numero_condicao_padronizado'], 1)
        self.assertFalse(resumo['dependencia_linear_exata'])
        linhas, resumo = diagnosticar_multicolinearidade(
            np.column_stack([np.ones(4), x, 2*x]), ['Intercept', 'x', 'duplicada'])
        self.assertTrue(resumo['dependencia_linear_exata'])
        self.assertTrue(np.isinf(resumo['numero_condicao_padronizado']))
        self.assertTrue(all(np.isinf(l['vif']) for l in linhas))
        self.assertTrue(all(l['tolerancia'] == 0 for l in linhas))

    def test_multicolinearidade_base_real_e_invariancia_de_escala(self):
        d, _ = ler_base(ARQUIVO)
        ajustes, _, _, diag, _ = estimar(d)
        variaveis, modelos = multicolinearidade(ajustes)
        self.assertEqual(set(modelos.modelo), set(MODELOS))
        self.assertEqual(len(variaveis), sum(len(r.params)-1 for r in ajustes.values()))
        comparacao = variaveis.merge(diag, on=['modelo', 'termo'], validate='one_to_one')
        np.testing.assert_allclose(comparacao.vif_x, comparacao.vif_y)
        np.testing.assert_allclose(variaveis.tolerancia * variaveis.vif, 1)
        self.assertFalse(modelos.dependencia_linear_exata.any())
        r = ajustes['R2']
        x = r.model.exog.copy()
        _, original = diagnosticar_multicolinearidade(x, r.model.exog_names)
        x[:, 1] = x[:, 1] * 1000 + 500
        _, escalado = diagnosticar_multicolinearidade(x, r.model.exog_names)
        self.assertAlmostEqual(original['numero_condicao_padronizado'],
                               escalado['numero_condicao_padronizado'])


if __name__ == '__main__':
    unittest.main()
