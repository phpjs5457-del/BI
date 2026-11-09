import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


BANCO = Path(__file__).parent / 'saida' / 'goias_bi.db'

st.set_page_config(
    page_title='Goiás BI | Inteligência Fiscal',
    page_icon='📊',
    layout='wide',
)
st.title('Goiás BI | Inteligência Fiscal')
st.caption('Repasses municipais de ICMS e IPVA · Goiás · exercício de 2025')
st.warning(
    'Versão provisória: ICMS e IPVA foram extraídos de abas diferentes da mesma '
    'planilha. A análise não substitui o cruzamento com uma segunda base pública independente.'
)

if not BANCO.exists():
    st.error(
        'Banco de dados não encontrado. Na pasta do projeto, execute: '
        '`python etl.py --arquivo dados/Conciliacao_das_Distribuicoes-2025.xlsx`'
    )
    st.stop()

with sqlite3.connect(BANCO) as con:
    df = pd.read_sql_query(
        'SELECT * FROM repasses_municipais ORDER BY municipio',
        con,
    )

if df.empty:
    st.error('O banco de dados não contém municípios. Reimporte a planilha com `etl.py`.')
    st.stop()

st.sidebar.header('Filtros')
municipios = st.sidebar.multiselect(
    'Municípios',
    options=df['municipio'].tolist(),
    default=df['municipio'].tolist(),
    help='Selecione um ou mais municípios para atualizar os indicadores e gráficos.',
)
filtrado = df[df['municipio'].isin(municipios)].copy()

if filtrado.empty:
    st.info('Selecione ao menos um município na barra lateral para ver os resultados.')
    st.stop()


def formatar_reais(valor):
    return 'R$ ' + f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


visao_geral, analise, dados = st.tabs(
    ['Visão geral', 'Relação estatística', 'Dados e metodologia']
)

with visao_geral:
    col1, col2, col3 = st.columns(3)
    col1.metric('Municípios selecionados', f'{len(filtrado)} de {len(df)}')
    col2.metric('ICMS repassado', formatar_reais(filtrado['icms_repassado'].sum()))
    col3.metric('IPVA repassado', formatar_reais(filtrado['ipva_repassado'].sum()))

    st.subheader('Maiores repasses anuais de ICMS')
    st.caption('Exibe até 20 municípios, em ordem crescente para facilitar a comparação.')
    ranking = filtrado.nlargest(20, 'icms_repassado').sort_values('icms_repassado')
    grafico_ranking = px.bar(
        ranking,
        x='icms_repassado',
        y='municipio',
        orientation='h',
        labels={
            'icms_repassado': 'ICMS repassado (R$)',
            'municipio': 'Município',
        },
    )
    grafico_ranking.update_layout(
        xaxis_tickprefix='R$ ',
        xaxis_tickformat=',.0f',
        yaxis_title=None,
        margin=dict(l=0, r=10, t=15, b=0),
    )
    st.plotly_chart(grafico_ranking, width='stretch')

with analise:
    st.subheader('Correlação e regressão linear simples')
    st.caption(
        'X = IPVA repassado (R$) · Y = ICMS repassado (R$). '
        'Cada ponto representa um município.'
    )

    valores = filtrado[['ipva_repassado', 'icms_repassado']].to_numpy(dtype=float)
    validos = np.isfinite(valores).all(axis=1)
    amostra = filtrado.loc[validos].copy()
    x = amostra['ipva_repassado'].to_numpy(dtype=float)
    y = amostra['icms_repassado'].to_numpy(dtype=float)

    if len(amostra) < 3 or np.unique(x).size < 2 or np.std(y) == 0:
        st.warning(
            'Ajuste indisponível: selecione pelo menos três municípios com valores '
            'válidos, IPVA diferente entre municípios e variação no ICMS.'
        )
    else:
        inclinacao, intercepto = np.polyfit(x, y, 1)
        correlacao = float(np.corrcoef(x, y)[0, 1])
        r_quadrado = correlacao**2

        col1, col2, col3 = st.columns(3)
        col1.metric('Municípios na análise', len(amostra))
        col2.metric('Correlação de Pearson (r)', f'{correlacao:.4f}')
        col3.metric('Coeficiente de determinação (R²)', f'{r_quadrado:.4f}')

        grafico = px.scatter(
            amostra,
            x='ipva_repassado',
            y='icms_repassado',
            hover_name='municipio',
            hover_data={'codigo_municipio': True},
            labels={
                'ipva_repassado': 'IPVA repassado (R$)',
                'icms_repassado': 'ICMS repassado (R$)',
                'codigo_municipio': 'Código municipal',
            },
        )
        grade = np.linspace(x.min(), x.max(), 100)
        grafico.add_trace(
            go.Scatter(
                x=grade,
                y=intercepto + inclinacao * grade,
                mode='lines',
                name='Regressão linear',
                line=dict(color='#E85D04', width=3),
            )
        )
        grafico.update_layout(
            xaxis_tickprefix='R$ ',
            xaxis_tickformat=',.0f',
            yaxis_tickprefix='R$ ',
            yaxis_tickformat=',.0f',
            margin=dict(l=0, r=10, t=15, b=0),
        )
        st.plotly_chart(grafico, width='stretch')
        st.markdown(
            f'**Equação ajustada:** ICMS estimado = '
            f'{formatar_reais(intercepto)} + ({inclinacao:.6f} × IPVA)'
        )
        st.caption(
            'Correlação descreve associação, não causalidade. O R² indica a proporção '
            'da variação observada no ICMS associada ao ajuste linear nesta amostra.'
        )

        st.subheader('Simulador')
        ipva_teste = st.number_input(
            'Informe um valor de IPVA repassado (R$)',
            min_value=0.0,
            value=float(np.median(x)),
            step=10000.0,
            format='%.2f',
        )
        st.metric(
            'ICMS estimado pelo modelo',
            formatar_reais(intercepto + inclinacao * ipva_teste),
        )
        st.caption(
            'Estimativa estatística, não previsão oficial. Valores fora da faixa '
            'observada podem não ser confiáveis.'
        )

with dados:
    st.subheader('Dados municipais')
    st.caption(
        f'{len(filtrado)} município(s) selecionado(s). A tabela e o CSV respeitam '
        'o filtro da barra lateral.'
    )
    colunas = [
        'codigo_municipio',
        'municipio',
        'ano',
        'icms_20',
        'fundeb_icms_5',
        'icms_repassado',
        'ipva_40',
        'fundeb_ipva_10',
        'ipva_repassado',
    ]
    st.dataframe(
        filtrado[colunas],
        width='stretch',
        hide_index=True,
        column_config={
            'codigo_municipio': st.column_config.TextColumn('Código municipal'),
            'municipio': st.column_config.TextColumn('Município'),
            'ano': st.column_config.NumberColumn('Ano', format='%d'),
            'icms_20': st.column_config.NumberColumn('ICMS 20% (R$)', format='R$ %.2f'),
            'fundeb_icms_5': st.column_config.NumberColumn(
                'FUNDEB ICMS 5% (R$)', format='R$ %.2f'
            ),
            'icms_repassado': st.column_config.NumberColumn(
                'ICMS repassado (R$)', format='R$ %.2f'
            ),
            'ipva_40': st.column_config.NumberColumn('IPVA 40% (R$)', format='R$ %.2f'),
            'fundeb_ipva_10': st.column_config.NumberColumn(
                'FUNDEB IPVA 10% (R$)', format='R$ %.2f'
            ),
            'ipva_repassado': st.column_config.NumberColumn(
                'IPVA repassado (R$)', format='R$ %.2f'
            ),
        },
    )
    st.download_button(
        'Baixar dados filtrados (CSV)',
        data=filtrado.to_csv(index=False).encode('utf-8-sig'),
        file_name='goias_bi_filtrado.csv',
        mime='text/csv',
    )

    with st.expander('Fonte, indicadores e limitações'):
        st.markdown(
            """
            - **Fonte:** Conciliação das Distribuições 2025, abas
              `ICMS_Bolão.dez` e `IPVA_Bolão.dez`.
            - **Unidade de análise:** município goiano no exercício de 2025.
            - **Chave de cruzamento:** código municipal; o ano compõe a chave do banco.
            - **Valores exibidos:** acumulados anuais da aba de dezembro; os meses
              não são somados novamente.
            - **Limitação principal:** ICMS e IPVA pertencem à mesma pasta de trabalho.
              Para atender ao requisito de duas bases independentes, é necessário
              incorporar outra fonte pública oficial e compatível por município e ano.
            - **Interpretação:** a regressão é descritiva; não demonstra causalidade
              e não deve ser interpretada como previsão oficial.
            """
        )
