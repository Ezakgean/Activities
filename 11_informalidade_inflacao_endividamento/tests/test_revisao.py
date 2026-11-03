"""Auditoria oficial offline, reprodução independente e sensibilidades."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from app.analise import ARQUIVO, ler_base, estimar, preparar, testes_significancia
from app.fontes import PASTA, auditar_fontes
from app.robustez import aprofundar_estacionariedade, sensibilidade_agregacao
from app.verificacao import reproduzir, matriz_independente


class Revisao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, _ = ler_base(ARQUIVO)
        cls.ajustes, cls.coefs, _, cls.diag, _ = estimar(cls.d)
        _, cls.tf = testes_significancia(cls.ajustes, cls.coefs)

    def test_fontes_40_trimestres_e_120_meses_por_serie(self):
        tri, meses, resumo, oficial, manifest = auditar_fontes(self.d, ARQUIVO)
        self.assertEqual(len(tri), 120)
        self.assertTrue(tri.confere.all())
        self.assertEqual(len(meses), 240)
        self.assertTrue(meses.confere.all())
        self.assertEqual(resumo.coincidentes.sum(), 120)
        self.assertTrue(all(r['consulta'] for r in manifest))
        np.testing.assert_allclose(oficial.informalidade, self.d.informalidade)

    def test_snapshot_adulterado_nao_e_certificado(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp)
            for path in PASTA.glob('*.json'):
                shutil.copy(path, pasta/path.name)
            caminho = pasta/'informalidade_trimestral.json'
            raw = json.loads(caminho.read_text())
            raw[1]['V'] = '1.0'
            caminho.write_text(json.dumps(raw))
            tri, _, resumo, _, _ = auditar_fontes(self.d, ARQUIVO, pasta)
            inf = tri[tri.variavel.eq('informalidade')]
            self.assertFalse(inf.confere.any())
            self.assertTrue(inf.oficial.isna().all())
            self.assertTrue(inf.erro.str.contains('Hash').all())
            # Se a resposta for validamente registrada mas houver valor diferente,
            # a comparação deve relatar divergência em vez de rejeitar só o hash.
            manifesto = json.loads((pasta/'manifesto.json').read_text())
            for r in manifesto:
                if r['fonte'] == 'informalidade_trimestral':
                    r['sha256'] = hashlib.sha256(caminho.read_bytes()).hexdigest()
            (pasta/'manifesto.json').write_text(json.dumps(manifesto))
            tri, _, resumo, _, _ = auditar_fontes(self.d, ARQUIVO, pasta)
            self.assertEqual(resumo.set_index('variavel').loc['informalidade','divergentes'], 1)
            self.assertEqual((tri.status == 'Diverge da versão consultada').sum(), 1)

    def test_reproducao_completa_e_deteccao_de_matriz_incorreta(self):
        resumo, coefs, covs = reproduzir(self.d, self.ajustes, self.tf, diagnosticos=self.diag)
        self.assertEqual(len(resumo),12)
        self.assertEqual(len(coefs),46)
        self.assertLess(resumo.erro_max_cov_hac.max(), 1e-8)
        self.assertLess(covs.erro_absoluto.max(), 1e-8)
        x,y,nomes,periodos = matriz_independente(self.d,'R1')
        self.assertEqual(len(y),38)
        self.assertEqual(periodos[0],'2016T3')
        d = self.d.copy()
        d.loc[3,'ipca'] += 1
        with self.assertRaises(AssertionError):
            reproduzir(d,self.ajustes,self.tf)

    def test_agregacao_recalcula_diferencas_e_preserva_m1(self):
        comp, modelos, base_fim, alt, coefs_alt, *_ = sensibilidade_agregacao(
            self.d,ARQUIVO,self.ajustes,estimar,preparar)
        np.testing.assert_allclose(alt['M1'].params,self.ajustes['M1'].params)
        np.testing.assert_allclose(alt['D1'].params,self.ajustes['D1'].params)
        self.assertEqual(len(comp),46)
        self.assertTrue((modelos.n_media==modelos.n_fim).all())
        np.testing.assert_allclose(base_fim.d_endividamento.iloc[1:],np.diff(base_fim.endividamento))
        self.assertFalse(np.allclose(base_fim.d_endividamento.iloc[1:],self.d.d_endividamento.iloc[1:]))
        _, tf = testes_significancia(alt, coefs_alt)
        reproduzir(base_fim,alt,tf)

    def test_sensibilidades_temporais_e_datas_de_quebra(self):
        est, quebra = aprofundar_estacionariedade(self.d)
        self.assertEqual(len(est),54)
        self.assertEqual(len(quebra),6)
        self.assertEqual(set(est.ordem_diferenca),{0,1,2})
        self.assertEqual(set(est.limite_lags),{1,2,4})
        self.assertTrue((est.adf_lags<=est.limite_lags).all())
        self.assertTrue(quebra.trimestre_quebra_candidato.isin(self.d.trimestre).all())
        for ordem,n in [(0,40),(1,39),(2,38)]:
            self.assertTrue((est[est.ordem_diferenca.eq(ordem)].n==n).all())


if __name__ == '__main__':
    unittest.main()
