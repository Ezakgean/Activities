"""Verifica a preservação de conteúdo e imagens na apresentação HTML."""
import base64
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from app.relatorio import escrever_html, render_blocks, table_html


class Documento(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.anchors = []
        self.images = []
        self.tables = 0
        self.details = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href', '').startswith('#'):
            self.anchors.append(attrs['href'][1:])
        if tag == 'img':
            self.images.append(attrs['src'])
        self.tables += tag == 'table'
        self.details += tag == 'details'


class Relatorio(unittest.TestCase):
    def test_conteudo_graficos_links_e_tabelas_preservados(self):
        # O renderer recebe o texto inteiro, incluindo os detalhes por modelo.
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        with tempfile.TemporaryDirectory() as temp:
            saida = Path(temp)
            (saida / 'series.png').write_bytes(png)
            texto = '''# Relatório

## Base, medidas e conferência

Informação anterior sobre a base.

![Séries](series.png)

## Gráficos individuais dos quatro modelos

Interpretação anterior dos gráficos.

## Testes t e F completos

Hipóteses preservadas.

### M1 — modelo

| termo | p_bilateral | decisao_5pct |
| --- | --- | --- |
| ipca | 0.3362 | Não rejeitar H0 |

## Multicolinearidade — todos os modelos

### Multicolinearidade em M1

VIF e limites heurísticos.

## Conclusão para o trabalho

Conclusão anterior preservada.

## Referências

- [Fonte](https://example.org/fonte).
'''
            tt = pd.DataFrame({'modelo': ['M1']})
            tf = pd.DataFrame({'modelo': ['M1'], 'tipo': ['global'], 'p_valor': [.3362]})
            multi = pd.DataFrame({'modelo': ['M1'], 'vif_maximo': [1.], 'n': [40]})
            escrever_html(texto, saida, tt, tf, multi, 'Sem alerta de colinearidade.')
            document = (saida / 'relatorio.html').read_text()
            parser = Documento()
            parser.feed(document)
            for sentence in ['Informação anterior sobre a base.', 'Interpretação anterior dos gráficos.',
                             'Hipóteses preservadas.', 'VIF e limites heurísticos.',
                             'Conclusão anterior preservada.']:
                self.assertIn(sentence, document)
            self.assertEqual(parser.tables, 1)
            self.assertEqual(parser.details, 2)
            self.assertEqual(len(parser.images), 1)
            self.assertEqual(base64.b64decode(parser.images[0].split(',')[1]), png)
            self.assertTrue(set(parser.anchors).issubset(parser.ids))
            self.assertLess(document.index('fig-series'), document.index('<section id="graficos"'))
            self.assertIn('beforeprint', document)
            self.assertNotIn('<script src=', document)

    def test_formatacao_segura_e_preservacao_das_decisoes(self):
        block = '| termo | decisao_5pct |\n| --- | --- |\n| <variável> | Rejeitar H0 |\n| outra | Não rejeitar H0 |'
        rendered = table_html(block)
        self.assertIn('&lt;variável&gt;', rendered)
        self.assertIn('badge sig', rendered)
        self.assertIn('badge neutral', rendered)
        self.assertIn('Não rejeitar H0', rendered)
        rendered = render_blocks('- [Planilha](resultados.xlsx).', Path('.'))
        self.assertIn('href="resultados.xlsx"', rendered)


if __name__ == '__main__':
    unittest.main()
