import base64
import html
import json
import sqlite3
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests

BASE = Path(__file__).resolve().parent
BANCO = BASE / 'saida' / 'goias_bi.db'
VERDE = '#16713C'
AMARELO = '#F3C543'
AZUL = '#19549B'

st.set_page_config(page_title='Goiás BI | Inteligência Fiscal', page_icon='🇧🇷', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#F8FBF9;color:#18342A}
[data-testid="stSidebar"] {background:#FFFFFF;border-right:1px solid #DFEAE2}
[data-testid="stSidebar"] * {color:#18342A}
.block-container {padding-top:1.5rem; max-width:1500px}
h1,h2,h3 {color:#145D35!important;letter-spacing:-.025em}
[data-testid="stMetric"] {background:#FFF;border:1px solid #DDEBE0;border-left:5px solid #16713C;border-radius:14px;padding:16px 18px;box-shadow:0 2px 9px #123c1c0c}
[data-testid="stMetricLabel"] {color:#446457}
[data-testid="stMetricValue"] {color:#154A32}
.stTabs [data-baseweb="tab-list"] {gap:10px;border-bottom:1px solid #DDEBE0}
.stTabs [data-baseweb="tab"] {background:#EDF6EF;border-radius:10px 10px 0 0;color:#145D35;padding:12px 20px}
.stTabs [aria-selected="true"] {background:#D9EDE0!important;border-bottom:3px solid #E9BB31}
.stButton button, .stDownloadButton button {background:#16713C;color:white;border:0;border-radius:9px}
.stButton button:hover, .stDownloadButton button:hover {background:#19549B;color:white}
[data-testid="stAlert"] {border-radius:12px}
.go-hero {background:linear-gradient(115deg,#fff 0%,#eef7f0 75%,#fff9de 100%);border:1px solid #dbe9dc;border-top:6px solid #16713C;border-radius:18px;padding:24px 26px;margin-bottom:22px}
.go-eyebrow {font-size:12px;font-weight:800;letter-spacing:.13em;color:#19549B;text-transform:uppercase}
.go-title {font-size:clamp(28px,3vw,42px);font-weight:850;color:#145D35;line-height:1.1;margin:8px 0}
.go-sub {color:#526d5c;font-size:15px}
.go-accent {height:5px;max-width:180px;border-radius:8px;background:linear-gradient(to right,#16713C 0 45%,#F3C543 45% 75%,#19549B 75%)}
.go-motion {width:112px;height:112px;object-fit:contain;filter:drop-shadow(0 5px 12px #16713c20)}
</style>''', unsafe_allow_html=True)

bandeira, cabecalho, animacao = st.columns([1, 7, 1.15], vertical_alignment='center')
with bandeira:
    st.image('https://commons.wikimedia.org/wiki/Special:FilePath/Flag_of_Goi%C3%A1s.svg', width=112)
with cabecalho:
    st.markdown('''<div class="go-hero"><div class="go-eyebrow">Estado de Goiás · Business Intelligence</div><div class="go-title">Goiás BI | Inteligência Fiscal</div><div class="go-sub">Painel de repasses municipais de ICMS e IPVA · Exercício 2025</div><div class="go-accent" style="margin-top:14px"></div></div>''', unsafe_allow_html=True)
with animacao:
    gif = base64.b64encode((BASE / 'assets' / 'goias_bi_animado.gif').read_bytes()).decode('ascii')
    st.markdown(f'<img class="go-motion" src="data:image/gif;base64,{gif}" alt="Mapa de Goiás com animação de dados em movimento">', unsafe_allow_html=True)

st.info('Análise exploratória: ICMS e IPVA vêm de abas da mesma planilha. Para cumprir integralmente a atividade, ainda é necessária uma segunda base pública independente.')
if not BANCO.exists():
    st.error('Banco de dados não encontrado. Execute `python etl.py --arquivo dados/Conciliacao_das_Distribuicoes-2025.xlsx` na pasta do projeto.')
    st.stop()
with sqlite3.connect(BANCO) as con:
    df = pd.read_sql_query('SELECT * FROM repasses_municipais ORDER BY municipio', con)
if df.empty:
    st.error('Banco vazio. Execute o ETL para importar os municípios.')
    st.stop()

st.sidebar.markdown('### 🟢 Goiás BI')
st.sidebar.caption('Filtros de análise · 2025')
municipios = st.sidebar.multiselect('Municípios', options=df['municipio'].tolist(), default=df['municipio'].tolist(), help='Selecione os municípios para atualizar todo o painel.')
filtrado = df[df['municipio'].isin(municipios)].copy()
st.sidebar.markdown('---')
st.sidebar.caption('Fonte: Conciliação das Distribuições 2025 · Governo de Goiás')
if filtrado.empty:
    st.warning('Selecione ao menos um município na barra lateral.')
    st.stop()

def reais(valor):
    return 'R$ ' + f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def grafico_claro(fig):
    fig.update_layout(template='plotly_white', paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', font=dict(color='#244936'), margin=dict(l=12,r=14,t=20,b=12), legend=dict(bgcolor='rgba(0,0,0,0)'))
    fig.update_xaxes(gridcolor='#E5EEE8', zerolinecolor='#E5EEE8')
    fig.update_yaxes(gridcolor='#E5EEE8', zerolinecolor='#E5EEE8')
    return fig

visao, analise, mapa, dados = st.tabs(['📊 Visão geral', '📈 Correlação e regressão', '🗺️ Mapa de Goiás', '🗂️ Dados e metodologia'])
with visao:
    m1,m2,m3=st.columns(3)
    m1.metric('Municípios selecionados', f'{len(filtrado)} de {len(df)}')
    m2.metric('ICMS repassado', reais(filtrado['icms_repassado'].sum()))
    m3.metric('IPVA repassado', reais(filtrado['ipva_repassado'].sum()))
    st.subheader('Os 20 maiores repasses de ICMS')
    ranking=filtrado.nlargest(20,'icms_repassado').sort_values('icms_repassado')
    fig=px.bar(ranking,x='icms_repassado',y='municipio',orientation='h',color_discrete_sequence=[VERDE],labels={'icms_repassado':'ICMS repassado (R$)','municipio':'Município'})
    fig.update_layout(xaxis_tickprefix='R$ ',xaxis_tickformat=',.0f',yaxis_title=None,height=620)
    st.plotly_chart(grafico_claro(fig),use_container_width=True)
    st.caption('Valores anuais por município, em reais.')

with analise:
    st.subheader('Relação entre IPVA e ICMS')
    st.caption('Variável X: IPVA repassado (R$) | Variável Y: ICMS repassado (R$). Cada ponto é um município.')
    valores=filtrado[['ipva_repassado','icms_repassado']].to_numpy(dtype=float)
    validos=np.isfinite(valores).all(axis=1)
    amostra=filtrado.loc[validos].copy()
    x=amostra['ipva_repassado'].to_numpy(dtype=float)
    y=amostra['icms_repassado'].to_numpy(dtype=float)
    if len(amostra)<3 or np.unique(x).size<2 or np.std(y)==0:
        st.warning('Selecione pelo menos três municípios válidos e com valores diferentes para calcular a regressão.')
    else:
        a,b=np.polyfit(x,y,1)
        r=float(np.corrcoef(x,y)[0,1])
        c1,c2,c3=st.columns(3)
        c1.metric('Municípios analisados',len(amostra))
        c2.metric('Correlação de Pearson (r)',f'{r:.4f}')
        c3.metric('Coeficiente R²',f'{r*r:.4f}')
        fig=px.scatter(amostra,x='ipva_repassado',y='icms_repassado',hover_name='municipio',hover_data=['codigo_municipio'],color_discrete_sequence=[AZUL],labels={'ipva_repassado':'IPVA repassado (R$)','icms_repassado':'ICMS repassado (R$)'})
        grade=np.linspace(x.min(),x.max(),100)
        fig.add_trace(go.Scatter(x=grade,y=b+a*grade,mode='lines',name='Reta de regressão',line=dict(color=VERDE,width=4)))
        fig.update_layout(xaxis_tickprefix='R$ ',xaxis_tickformat=',.0f',yaxis_tickprefix='R$ ',yaxis_tickformat=',.0f',height=490)
        st.plotly_chart(grafico_claro(fig),use_container_width=True)
        st.markdown(f'**Equação ajustada:** ICMS estimado = {reais(b)} + ({a:.6f} × IPVA)')
        st.caption('Correlação não significa causalidade. O R² é referente ao ajuste linear da amostra selecionada.')
        st.subheader('Simulador de repasse')
        valor=st.number_input('Valor de IPVA repassado (R$)',min_value=0.0,value=float(np.median(x)),step=10000.0,format='%.2f')
        st.metric('ICMS estimado pelo modelo',reais(b+a*valor))
        st.caption('Estimativa descritiva, não previsão oficial. Evite extrapolar para valores fora dos observados.')


# A planilha fiscal usa códigos próprios, diferentes dos códigos IBGE.
# O vínculo geográfico é realizado pelo nome normalizado do município.
FONTE_GEOJSON = 'https://cdn.jsdelivr.net/gh/henriquemalvar/br-geojson@main/dist/municipios/GO.geojson'
ARQUIVO_GEOJSON = BASE / 'dados' / 'goias_municipios.geojson'


def normalizar_municipio(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.casefold().strip().split())


def criar_mapa_svg(geometria, associados, indicador):
    features_por_codigo = {
        str(feature.get('properties', {}).get('cd_geocmu') or feature.get('properties', {}).get('CD_MUN')): feature
        for feature in geometria['features']
    }
    selecionados = associados.set_index('ibge_id').to_dict('index')
    valores = associados[indicador].dropna().astype(float)
    cores = ['#E6F4E9', '#BDE2C5', '#82C996', '#3FA867', '#116B3A']
    limites = np.unique(valores.quantile(np.linspace(0, 1, len(cores) + 1)).to_numpy())
    classes = {
        codigo: (
            0 if len(limites) == 1
            else int(np.searchsorted(limites[1:-1], float(municipio[indicador]), side='left'))
        )
        for codigo, municipio in selecionados.items()
        if pd.notna(municipio[indicador])
    }

    def rings_for(feature):
        if feature['geometry']['type'] == 'Polygon':
            return feature['geometry']['coordinates']
        return [ring for poligono in feature['geometry']['coordinates'] for ring in poligono]

    pontos_originais = [
        ponto
        for feature in geometria['features']
        for ring in rings_for(feature)
        for ponto in ring
    ]
    latitude_media = np.mean([ponto[1] for ponto in pontos_originais])
    fator_longitude = np.cos(np.radians(latitude_media))
    pontos = [
        (ponto[0] * fator_longitude, ponto[1])
        for ponto in pontos_originais
    ]
    min_x = min(ponto[0] for ponto in pontos)
    max_x = max(ponto[0] for ponto in pontos)
    min_y = min(ponto[1] for ponto in pontos)
    max_y = max(ponto[1] for ponto in pontos)
    largura, altura_mapa, margem = 900, 690, 24
    altura_legenda = 170
    altura = altura_mapa + altura_legenda
    escala = min((largura - margem * 2) / (max_x - min_x), (altura_mapa - margem * 2) / (max_y - min_y))
    deslocamento_x = (largura - (max_x - min_x) * escala) / 2
    deslocamento_y = (altura_mapa - (max_y - min_y) * escala) / 2

    def projetar(ponto):
        x = deslocamento_x + (ponto[0] * fator_longitude - min_x) * escala
        y = altura_mapa - deslocamento_y - (ponto[1] - min_y) * escala
        return x, y

    caminhos = []
    for codigo, feature in features_por_codigo.items():
        municipio = selecionados.get(codigo)
        valor = float(municipio[indicador]) if municipio and pd.notna(municipio[indicador]) else None
        faixa = classes.get(codigo) if valor is not None else None
        cor = cores[faixa] if faixa is not None else '#E8ECE9'
        segmentos = []
        for ring in rings_for(feature):
            projetados = [projetar(ponto) for ponto in ring]
            segmentos.append(
                'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in projetados) + 'Z'
            )
        nome = municipio['municipio'] if municipio else feature.get('properties', {}).get('nome', 'Município')
        descricao = f'{nome} — {reais(valor)}' if valor is not None else f'{nome} — fora do filtro'
        caminhos.append(
            f'<path class="municipio" d="{"".join(segmentos)}" fill="{cor}" '
            f'title="{html.escape(descricao, quote=True)}"><title>{html.escape(descricao)}</title></path>'
        )

    def formatar_limite(valor):
        absoluto = abs(valor)
        divisor, sufixo = (1_000_000, ' mi') if absoluto >= 1_000_000 else (
            (1_000, ' mil') if absoluto >= 1_000 else (1, '')
        )
        numero = f'{valor / divisor:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f'{numero}{sufixo}'

    itens_legenda = []
    quantidade_faixas = max(1, len(limites) - 1)
    for indice in range(quantidade_faixas):
        cor = cores[indice]
        if len(limites) == 1:
            intervalo = f'{formatar_limite(limites[0])} (todos iguais)'
        elif indice == 0:
            intervalo = f'Até {formatar_limite(limites[1])}'
        else:
            intervalo = f'Acima de {formatar_limite(limites[indice])} até {formatar_limite(limites[indice + 1])}'
        x = 24 + (indice % 3) * 292
        y = altura_mapa + 78 + (indice // 3) * 42
        itens_legenda.append(
            f'<rect x="{x}" y="{y - 13}" width="17" height="17" rx="4" fill="{cor}"/>'
            f'<text x="{x + 25}" y="{y}" class="legenda-titulo">Faixa {indice + 1}</text>'
            f'<text x="{x + 25}" y="{y + 16}" class="legenda-valor">{html.escape(intervalo)}</text>'
        )
    x_fora = 24 + (quantidade_faixas % 3) * 292
    y_fora = altura_mapa + 78 + (quantidade_faixas // 3) * 42
    itens_legenda.append(
        f'<rect x="{x_fora}" y="{y_fora - 13}" width="17" height="17" rx="4" fill="#E8ECE9"/>'
        f'<text x="{x_fora + 25}" y="{y_fora}" class="legenda-titulo">Fora do filtro</text>'
        f'<text x="{x_fora + 25}" y="{y_fora + 16}" class="legenda-valor">Municípios não selecionados</text>'
    )
    titulo_indicador = 'ICMS repassado' if indicador == 'icms_repassado' else 'IPVA repassado'
    legenda = (
        f'<rect x="0" y="{altura_mapa}" width="{largura}" height="{altura_legenda}" fill="#F8FBF9"/>'
        f'<path d="M24 {altura_mapa + 15}H{largura - 24}" stroke="#DDEAE0"/>'
        f'<text x="24" y="{altura_mapa + 43}" class="legenda-cabecalho">'
        f'Legenda — {titulo_indicador} (R$)</text>'
        f'<text x="24" y="{altura_mapa + 62}" class="legenda-nota">'
        'Faixas por quintis dos municípios selecionados · valores resumidos em mil ou milhões</text>'
        f'{"".join(itens_legenda)}'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'role="img" aria-label="Mapa de Goiás dividido em municípios, colorido por {html.escape(indicador)}" '
        'style="display:block;width:100%;height:auto">'
        '<style>.municipio{stroke:#fff;stroke-width:1.05;stroke-linejoin:round;vector-effect:non-scaling-stroke;'
        'transition:fill .15s,stroke-width .15s}.municipio:hover{stroke:#123f29;stroke-width:2.6}'
        '.legenda-cabecalho{font:700 17px sans-serif;fill:#145D35}'
        '.legenda-nota{font:12px sans-serif;fill:#526d5c}'
        '.legenda-titulo{font:700 12px sans-serif;fill:#244936}'
        '.legenda-valor{font:11px sans-serif;fill:#526d5c}</style>'
        f'{"".join(caminhos)}{legenda}</svg>'
    )


@st.cache_data(show_spinner=False, ttl=86400)
def carregar_geojson():
    if ARQUIVO_GEOJSON.exists():
        with ARQUIVO_GEOJSON.open(encoding='utf-8') as arquivo:
            geo = json.load(arquivo)
    else:
        resposta = requests.get(FONTE_GEOJSON, timeout=30)
        resposta.raise_for_status()
        geo = resposta.json()
        if geo.get('type') != 'FeatureCollection':
            raise ValueError('A fonte do mapa não retornou um GeoJSON válido.')
        ARQUIVO_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_GEOJSON.write_text(json.dumps(geo, ensure_ascii=False), encoding='utf-8')
    if geo.get('type') != 'FeatureCollection' or not geo.get('features'):
        raise ValueError('Arquivo GeoJSON inválido ou sem municípios.')
    return geo


with mapa:
    st.subheader('Distribuição territorial dos repasses em Goiás')
    st.caption('Mapa municipal de 2025 · Passe o mouse sobre um município para ver os repasses. Os filtros da barra lateral também se aplicam ao mapa.')
    indicador = st.selectbox(
        'Indicador geográfico',
        options=['icms_repassado', 'ipva_repassado'],
        format_func=lambda nome: 'ICMS repassado (R$)' if nome == 'icms_repassado' else 'IPVA repassado (R$)',
    )
    try:
        geometria = carregar_geojson()
    except (OSError, ValueError, requests.RequestException, json.JSONDecodeError) as erro:
        st.error('Não foi possível carregar a malha municipal. Confira sua internet ou salve o arquivo goias_municipios.geojson na pasta dados.')
        st.caption(f'Detalhes técnicos: {erro}')
        st.code('python baixar_mapa.py', language='bash')
    else:
        registros_mapa = []
        for feature in geometria['features']:
            propriedades = feature.get('properties') or {}
            nome = propriedades.get('nome') or propriedades.get('NM_MUN')
            codigo = propriedades.get('cd_geocmu') or propriedades.get('CD_MUN')
            if nome and codigo:
                registros_mapa.append({'nome_geo': str(nome), 'chave': normalizar_municipio(nome), 'ibge_id': str(codigo)})
        tabela_geo = pd.DataFrame(registros_mapa)
        if tabela_geo.empty or tabela_geo['chave'].duplicated().any():
            st.error('A malha municipal não possui nomes/códigos válidos e únicos para cruzamento.')
        else:
            tabela_fiscal = df.copy()
            tabela_fiscal['chave'] = tabela_fiscal['municipio'].map(normalizar_municipio)
            todos_associados = tabela_fiscal.merge(tabela_geo, on='chave', how='left', validate='one_to_one')
            nao_localizados = todos_associados[
                todos_associados['municipio'].isin(municipios) & todos_associados['ibge_id'].isna()
            ]
            todos_associados = todos_associados.dropna(subset=['ibge_id']).copy()
            associados = todos_associados[todos_associados['municipio'].isin(municipios)].copy()
            col1, col2, col3 = st.columns(3)
            col1.metric('Municípios com geometria', f'{len(associados)} de {len(filtrado)}')
            col2.metric('ICMS no mapa', reais(associados['icms_repassado'].sum()))
            col3.metric('IPVA no mapa', reais(associados['ipva_repassado'].sum()))
            if not nao_localizados.empty:
                with st.expander(f'{len(nao_localizados)} município(s) sem correspondência no mapa'):
                    st.dataframe(nao_localizados[['municipio', 'codigo_municipio']], hide_index=True)
            if associados.empty:
                st.warning('Nenhum município selecionado corresponde à malha. Confira os nomes da base.')
            else:
                st.components.v1.html(
                    criar_mapa_svg(geometria, associados, indicador),
                    height=860,
                    scrolling=False,
                )
                st.caption(
                    f'Exibindo {len(associados)} município(s) selecionado(s) de {len(todos_associados)} '
                    'com geometria. Os demais municípios aparecem em cinza. Passe o mouse sobre uma área '
                    'para consultar o município e o valor.'
                )
                st.caption('Fonte geográfica: malha municipal derivada do IBGE, disponibilizada em GeoJSON pelo projeto br-geojson. O código municipal fiscal é distinto do geocódigo IBGE; os vínculos foram feitos pelo nome do município.')

with dados:
    st.subheader('Base municipal consolidada')
    st.caption(f'{len(filtrado)} municípios selecionados — tabela e exportação seguem o filtro.')
    colunas=['codigo_municipio','municipio','ano','icms_20','fundeb_icms_5','icms_repassado','ipva_40','fundeb_ipva_10','ipva_repassado']
    st.dataframe(filtrado[colunas],use_container_width=True,hide_index=True)
    st.download_button('⬇️ Baixar CSV filtrado',filtrado.to_csv(index=False).encode('utf-8-sig'),file_name='goias_bi_filtrado.csv',mime='text/csv')
    with st.expander('Metodologia e limitações'):
        st.markdown('''**Fonte:** Conciliação das Distribuições 2025 (abas `ICMS_Bolão.dez` e `IPVA_Bolão.dez`).  
**Unidade:** município do Estado de Goiás no exercício de 2025.  
**Chave:** código municipal e ano.  
**Valores:** acumulados anuais na aba de dezembro; não somar novamente os meses.  
**Limitação:** duas abas da mesma pasta de trabalho não substituem uma segunda base independente solicitada pelo professor.  
**Regressão:** análise de associação, não prova de causalidade.''')
