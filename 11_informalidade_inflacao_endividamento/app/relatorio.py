"""Apresentação portátil do relatório; não altera estimativas ou interpretações."""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path


TITULOS_GRAFICOS = {
    'autocorrelacao_modelos': 'Autocorrelação residual • 12 modelos',
    'sensibilidade_agregacao': 'Endividamento • média e fim de trimestre',
    'series': 'Evolução das séries • 2016–2025',
    'coeficientes': 'Coeficientes dos modelos em nível • IC 95% HAC',
    'ajuste_m4': 'Modelo M4 • ajuste e resíduos',
    'modelo_1_ipca': 'M1 • Informalidade e inflação',
    'modelo_2_endividamento': 'M2 • Informalidade e endividamento',
    'modelo_3_ipca_endividamento': 'M3 • Inflação e endividamento',
    'modelo_4_pandemia': 'M4 • Inflação, endividamento e pandemia',
}

CSS = '''
:root{--ink:#18333d;--muted:#536a73;--brand:#146c73;--line:#dbe5e6;--paper:#fff;--bg:#f2f6f5;--warn:#97600a}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 system-ui,-apple-system,sans-serif}
a{color:var(--brand);text-underline-offset:3px}a:hover{color:#0d454a}button,summary{font:inherit}
.layout{max-width:1540px;margin:auto;display:grid;grid-template-columns:250px minmax(0,1fr);gap:36px;padding:32px}
nav{position:sticky;top:24px;align-self:start;max-height:94vh;overflow:auto;padding:12px 0}
.brand{font-weight:800;letter-spacing:.08em;font-size:12px;color:var(--brand)}nav h2{font-size:20px;line-height:1.3;margin:12px 0 24px}
nav a{display:block;font-size:13px;padding:7px 12px;border-left:2px solid var(--line);text-decoration:none;color:var(--muted)}nav a:hover{border-color:var(--brand);background:#e5efed}
main{min-width:0}.hero{padding:44px;background:#123e49;color:#fff;border-radius:22px;margin-bottom:24px}.hero h1{font-family:Georgia,serif;font-weight:400;font-size:clamp(30px,4vw,46px);line-height:1.17;margin:12px 0 20px;max-width:850px}.hero p{color:#d1e4e6;max-width:70ch}.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase}.hero a{color:#d5f0e7}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.actions a,.actions button{border:1px solid #719397;border-radius:8px;padding:8px 14px;text-decoration:none;background:transparent;color:white;font-size:13px;cursor:pointer}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.card{padding:20px;background:white;border:1px solid var(--line);border-radius:12px}.card strong{display:block;font-size:28px;line-height:1.3}.card span{font-size:12px;color:var(--muted)}
section{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:32px;margin:22px 0;min-width:0}h2{font:500 29px/1.25 Georgia,serif;margin:0 0 24px}h3{font-size:19px;margin-top:28px}p{max-width:92ch}li{margin-bottom:8px}.section-number{display:block;color:var(--brand);font:700 11px/1.4 system-ui;letter-spacing:.12em;margin-bottom:10px}
.table{overflow-x:auto;margin:22px 0;border:1px solid var(--line);border-radius:10px}table{border-collapse:collapse;width:100%;font-size:12px;line-height:1.5;font-variant-numeric:tabular-nums}th{background:#edf4f2;color:#24505a;white-space:nowrap;text-align:left}th,td{padding:11px 13px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#f8faf9}tbody tr:hover{background:#edf5f3}td.num{text-align:right;white-space:nowrap}.badge{display:inline-block;border-radius:5px;padding:3px 7px;font-size:11px;font-weight:600;white-space:nowrap}.sig{background:#dcefea;color:#205a4a}.neutral{background:#edf1f3;color:#53656e}.warn{background:#fff0cf;color:#82500c}.critical{background:#fbe5e3;color:#963d33}
figure{margin:28px 0;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:white}figure img{display:block;width:100%;height:auto}figcaption{padding:14px 18px;background:#f5f8f7;font-size:13px;color:var(--muted)}figcaption strong{color:var(--ink)}figcaption a{float:right}.figure-help{font-size:12px;color:var(--muted)}
details{margin:14px 0;border:1px solid var(--line);border-radius:10px;overflow:hidden}summary{padding:16px 20px;background:#f1f6f4;cursor:pointer;font-size:14px;font-weight:600}summary:hover{background:#e6f0ed}.detail-body{padding:4px 18px 18px}details[open] summary{border-bottom:1px solid var(--line)}.subtle{color:var(--muted);font-size:13px}.callout{border-left:4px solid var(--brand);background:#edf6f2;padding:18px 22px;border-radius:0 10px 10px 0;margin:20px 0}.callout p{margin:0}.vif-row{display:grid;grid-template-columns:36px minmax(100px,1fr) 60px;align-items:center;gap:12px;font-size:12px;margin:10px 0}.track{background:#edf2f1;height:12px;border-radius:10px;position:relative;overflow:hidden}.track:after{content:'';position:absolute;left:50%;height:100%;border-left:1px dashed #8e691e}.bar{height:100%;background:#2a8585;border-radius:10px}.bar.attention{background:#c78a27}.bar.high{background:#b35046}.vif-row b{text-align:right}.mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px}.mini-grid h3{margin-top:0}.endnote{color:var(--muted);font-size:12px;padding:10px 4px 36px}
@media(max-width:1050px){.layout{grid-template-columns:190px minmax(0,1fr);gap:20px;padding:20px}.cards{grid-template-columns:repeat(2,1fr)}section{padding:24px}.hero{padding:30px}.mini-grid{grid-template-columns:1fr}}
@media(max-width:720px){.layout{display:block;padding:12px}nav{position:static;max-height:none;padding:12px}nav h2{margin:8px 0}nav .links{display:flex;overflow:auto;padding-bottom:8px}nav a{white-space:nowrap;border-left:0;border-bottom:2px solid var(--line)}section{padding:20px 16px}.hero{padding:26px 22px;border-radius:14px}h2{font-size:25px}.card{padding:16px}.cards{gap:8px}summary{padding:14px;font-size:13px}}
@media print{body{background:white;font-size:10pt}.layout{display:block;padding:0}nav,.actions,.figure-help{display:none}.hero{background:white;color:var(--ink);padding:0}.hero p{color:var(--muted)}section{border:0;padding:12px 0;margin:10px 0;break-before:auto}h2,h3,summary{break-after:avoid}figure,.card,tr{break-inside:avoid}figure{max-width:100%}.table{overflow:visible}table{font-size:8pt}th,td{padding:5px}.cards{grid-template-columns:repeat(4,1fr)}details{border:0}.detail-body{padding:0}.mini-grid{display:block}a{color:inherit}}
'''

LABELS = {
    'teste_ou_diagnostico': 'Teste / diagnóstico', 'objeto': 'Hipótese / objeto',
    'resultado_ou_leitura': 'Resultado / leitura', 'limite_da_conclusao': 'Limite da conclusão',
    'dimensao': 'Dimensão', 'situacao': 'Situação', 'evidencia_ou_limite': 'Evidência / limite',
    'variavel': 'Variável', 'observacoes': 'Observações', 'conferidas': 'Conferidas',
    'coincidentes': 'Coincidentes', 'divergentes': 'Divergentes', 'erro_maximo_pp': 'Diferença máxima (p.p.)',
    'status': 'Situação', 'coef_media': 'Coef. · média', 'coef_fim': 'Coef. · fim',
    'p_media': 'p · média', 'p_fim': 'p · fim', 'diferenca_coef': 'Diferença de coef.',
    'mudou_sinal': 'Mudou sinal?', 'mudou_decisao_5pct': 'Mudou decisão a 5%?',
    'bg_rejeita_5pct': 'BG rejeita a 5%?', 'bp_rejeita_5pct': 'BP rejeita a 5%?',
    'za_estatistica': 'Estatística ZA', 'za_p_aproximado': 'p · ZA (aprox.)',
    'critico_5pct': 'Crítico a 5%', 'trimestre_quebra_candidato': 'Quebra candidata',
    'rejeita_raiz_unitaria_5pct': 'Rejeita H0 a 5%?',
    'erro_max_coef': 'Erro máx. · coef.', 'erro_max_cov_hac': 'Erro máx. · cov. HAC',
    'erro_max_t': 'Erro máx. · t', 'erro_max_p': 'Erro máx. · p', 'erro_max_f': 'Erro máx. · F',
    'inicio': 'Início', 'fim': 'Fim', 'observacoes_perdidas': 'Perdas', 'gl_residuais': 'GL residuais',
    'modelo': 'Modelo', 'termo': 'Variável / coeficiente', 'coeficiente': 'Coeficiente',
    'ep_hac': 'Erro-padrão HAC', 't_hac': 't (HAC)', 'gl': 'GL', 'p_bilateral': 'p bilateral',
    'decisao_5pct': 'Decisão a 5%', 'tipo': 'Teste F', 'termos': 'Coeficientes testados',
    'f_hac': 'F (HAC)', 'gl_numerador': 'GL num.', 'gl_denominador': 'GL den.',
    'p_valor': 'p-valor', 'ic95_inferior': 'IC 95% · inferior', 'ic95_superior': 'IC 95% · superior',
    'vif': 'VIF', 'tolerancia': 'Tolerância', 'r2_auxiliar': 'R² auxiliar',
    'avaliacao_vif': 'Avaliação VIF', 'numero_condicao_padronizado': 'Nº de condição padronizado',
    'avaliacao_condicao': 'Avaliação da condição', 'dependencia_linear_exata': 'Dependência exata',
    'posto_matriz_com_intercepto': 'Posto da matriz', 'colunas_com_intercepto': 'Colunas da matriz',
    'numero_regressores': 'Regressores', 'vif_maximo': 'VIF máximo', 'r2': 'R²',
    'r2_ajustado': 'R² ajustado', 'n': 'N', 'p_f_hac_explicativas': 'p · F econômico',
}


def inline(text):
    escaped = html.escape(text)
    # Only local artifact names and HTTPS references are permitted.
    return re.sub(r'\[([^\]]+)\]\((https://[^\s)]+|[\w.\-/]+)\)',
                  r'<a href="\2">\1</a>', escaped)


def figure_html(path):
    title = TITULOS_GRAFICOS.get(path.stem, path.stem)
    data = base64.b64encode(path.read_bytes()).decode()
    pdf = path.with_suffix('.pdf')
    download = f'<a href="{html.escape(pdf.name)}">Baixar PDF</a>' if pdf.exists() else ''
    return (f'<figure id="fig-{path.stem}"><img alt="{html.escape(title)}" '
            f'src="data:image/png;base64,{data}"><figcaption><strong>{html.escape(title)}</strong>'
            f'{download}</figcaption></figure>')


def table_html(block):
    lines = block.splitlines()
    headers = [c.strip() for c in lines[0].strip('|').split('|')]
    out = ['<div class="table" tabindex="0" role="region" aria-label="Tabela de resultados"><table><thead><tr>']
    out.extend(f'<th scope="col">{html.escape(LABELS.get(h, h))}</th>' for h in headers)
    out.append('</tr></thead><tbody>')
    for line in lines[2:]:
        out.append('<tr>')
        for cell in line.strip('|').split('|'):
            value = cell.strip()
            safe = html.escape(value)
            if value == 'Rejeitar H0':
                safe = f'<span class="badge sig">{safe}</span>'
            elif value == 'Não rejeitar H0':
                safe = f'<span class="badge neutral">{safe}</span>'
            elif value.startswith('Atenção'):
                safe = f'<span class="badge warn">{safe}</span>'
            elif value.startswith('Elevada'):
                safe = f'<span class="badge critical">{safe}</span>'
            elif value.startswith('Baixa'):
                safe = f'<span class="badge neutral">{safe}</span>'
            elif value in ('False', 'True'):
                safe = 'Sim' if value == 'True' else 'Não'
            numeric = bool(re.fullmatch(r'[-+]?\d+(\.\d+)?', value))
            out.append(f'<td class="{"num" if numeric else "text"}">{safe}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def render_blocks(content, saida, collapsible=False):
    out, detail = [], False
    for block in content.strip().split('\n\n'):
        block = block.strip()
        if not block:
            continue
        if block.startswith('### '):
            if detail:
                out.append('</div></details>')
                detail = False
            title = block[4:]
            if collapsible:
                out.append(f'<details><summary>{inline(title)}</summary><div class="detail-body">')
                detail = True
            else:
                out.append(f'<h3>{inline(title)}</h3>')
        elif block.startswith('| '):
            out.append(table_html(block))
        elif block.startswith('!['):
            for filename in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', block):
                out.append(figure_html(saida / filename))
        elif block.startswith('- '):
            out.append('<ul>' + ''.join(f'<li>{inline(line[2:])}</li>' for line in block.splitlines()) + '</ul>')
        elif re.match(r'^\d+\. ', block):
            out.append('<ol>' + ''.join(f'<li>{inline(re.sub(r"^\d+\. ", "", line))}</li>' for line in block.splitlines()) + '</ol>')
        else:
            out.append('<p>' + inline(block).replace('\n', '<br>') + '</p>')
    if detail:
        out.append('</div></details>')
    return ''.join(out)


def escrever_html(texto, saida, testes_t, testes_f, multi_modelos, leitura_multi):
    parts = re.split(r'^## (.+)\n', texto, flags=re.M)
    sections = list(zip(parts[1::2], parts[2::2]))
    globals_ = testes_f[testes_f.tipo.eq('global')]
    cards = [(str(int(multi_modelos.n.max())), 'trimestres • 2016T1–2025T4'), (str(len(globals_)), 'modelos estimados'),
             (str(len(testes_t)), 'testes t bilaterais'), (str(len(testes_f)), 'testes F individuais e conjuntos')]
    hero = '''<header class="hero"><div class="eyebrow">Atividade 11 · Análise econométrica</div>
<h1>Inflação, endividamento<br>e informalidade no Brasil</h1>
<p>Uma leitura das associações entre preços, dívida das famílias e trabalho informal, com modelos em nível, diferenças e verificações de robustez.</p>
<div class="actions"><a href="#graficos">Explorar os gráficos</a><a href="resultados.xlsx">Baixar resultados · Excel</a><button onclick="imprimir()">Imprimir / salvar PDF</button></div></header>'''
    overview = '<div class="cards">' + ''.join(f'<div class="card"><strong>{v}</strong><span>{label}</span></div>' for v, label in cards) + '</div>'
    conclusao = next(content for title, content in sections if title == 'Conclusão para o trabalho').strip().split('\n\n')[0]
    overview += ('<section id="visao-geral"><span class="section-number">LEITURA RÁPIDA</span><h2>O que os resultados mostram</h2>'
                 f'<div class="callout"><p>{inline(conclusao)}</p></div>'
                 '<div class="mini-grid"><div><h3>Alcance da evidência</h3>'
                 '<p>M4 organiza a apresentação por reunir as duas variáveis econômicas e a janela da pandemia. Seu papel é descritivo; a inferência temporal permanece limitada pelos diagnósticos.</p>'
                 '<p>Testes individuais, testes conjuntos e diagnósticos têm objetos distintos. Rejeição global com controles não confirma, por si só, a hipótese sobre inflação e endividamento.</p>'
                 '<p class="subtle">Leia coeficientes, intervalos e hipóteses em conjunto. Não rejeitar H0 não demonstra equivalência a zero; os complementares são exploratórios.</p></div>'
                 '<div><h3>Multicolinearidade por modelo</h3><p class="subtle">Maior VIF entre as explicativas. Linha tracejada: VIF = 5; escala de 0 a 10.</p>')
    for r in multi_modelos.itertuples():
        cls = 'high' if r.vif_maximo >= 10 else 'attention' if r.vif_maximo >= 5 else ''
        overview += (f'<div class="vif-row"><span>{r.modelo}</span><div class="track"><div class="bar {cls}" '
                     f'style="width:{min(100, r.vif_maximo * 10):.2f}%"></div></div><b>{r.vif_maximo:.2f}</b></div>')
    overview += f'</div></div><p>{inline(leitura_multi)}</p><p class="subtle">VIF e número de condição são diagnósticos com limites heurísticos; não têm p-valor.</p></section>'
    navigation = ['<a href="#visao-geral">Visão geral</a>']
    rendered = []
    for index, (title, content) in enumerate(sections, 1):
        ident = 'graficos' if title.startswith('Gráficos individuais') else f'sec-{index}'
        navigation.append(f'<a href="#{ident}">{inline(title)}</a>')
        collapse = title.startswith(('Testes t e F', 'Multicolinearidade'))
        controls = ('<p class="subtle">Selecione um modelo para consultar todas as linhas. '
                    '<button type="button" onclick="alternar(this)">Expandir tabelas desta seção</button></p>') if collapse else ''
        rendered.append(f'<section id="{ident}"><span class="section-number">{index:02d} · ANÁLISE</span>'
                        f'<h2>{inline(title)}</h2>{controls}{render_blocks(content, saida, collapse)}</section>')
    script = '''<script>
function alternar(button){const section=button.closest('section');const items=section.querySelectorAll('details');const open=Array.from(items).some(d=>!d.open);items.forEach(d=>d.open=open);button.textContent=open?'Recolher tabelas desta seção':'Expandir tabelas desta seção'}
let printState=[];window.addEventListener('beforeprint',()=>{printState=Array.from(document.querySelectorAll('details')).map(d=>[d,d.open]);printState.forEach(([d])=>d.open=true)});window.addEventListener('afterprint',()=>printState.forEach(([d,open])=>d.open=open));
function imprimir(){window.print()}
</script>'''
    document = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Atividade 11 · Inflação, endividamento e informalidade</title><style>' + CSS + '</style></head><body>'
                '<div class="layout"><nav aria-label="Seções do relatório"><div class="brand">ECONOMETRIA / 11</div><h2>Brasil<br>2016 — 2025</h2><div class="links">'
                + ''.join(navigation) + '</div></nav><main>' + hero + overview + ''.join(rendered)
                + '<footer class="endnote">Relatório reproduzível · Gráficos incorporados ao HTML · Consulte a seção de metodologia e limitações antes de interpretar os resultados.</footer></main></div>' + script + '</body></html>')
    (saida / 'relatorio.html').write_text(document, encoding='utf-8')
