"""Importa os totais anuais de ICMS e IPVA por município da conciliação de 2025.
A fonte Excel pode ser grande; a leitura XML é feita por fluxo, sem carregar planilha inteira.
"""
import argparse
import sqlite3
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

N = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def extrair(xlsx, nome_aba, linha_inicial, colunas):
    with zipfile.ZipFile(xlsx) as zipf:
        strings = [''.join(t.text or '' for t in item.iter(N + 't'))
                   for item in ET.fromstring(zipf.read('xl/sharedStrings.xml'))]
        livro = ET.fromstring(zipf.read('xl/workbook.xml'))
        relacoes = {node.get('Id'): node.get('Target')
                    for node in ET.fromstring(zipf.read('xl/_rels/workbook.xml.rels'))}
        aba = next((s for s in livro.find(N + 'sheets') if s.get('name') == nome_aba), None)
        if aba is None:
            raise ValueError(f'Aba não encontrada: {nome_aba}')
        caminho = relacoes[aba.get(R + 'id')]
        caminho = caminho.lstrip('/') if caminho.startswith('/') else 'xl/' + caminho
        dados = []
        with zipf.open(caminho) as arquivo:
            for _, linha in ET.iterparse(arquivo, events=['end']):
                if linha.tag != N + 'row':
                    continue
                if int(linha.get('r', 0)) < linha_inicial:
                    linha.clear()
                    continue
                celulas = {}
                for celula in linha.findall(N + 'c'):
                    coluna = ''.join(k for k in celula.get('r', '') if k.isalpha())
                    if coluna not in colunas:
                        continue
                    elem = celula.find(N + 'v')
                    valor = elem.text if elem is not None else None
                    if celula.get('t') == 's' and valor is not None:
                        valor = strings[int(valor)]
                    celulas[coluna] = valor
                if celulas.get('B', '').isdigit() and celulas.get('C') and celulas.get('D'):
                    dados.append(celulas)
                linha.clear()
        return dados


def carregar(xlsx, banco):
    icms = extrair(xlsx, 'ICMS_Bolão.dez', 8, {'B', 'C', 'D', 'G', 'H', 'I'})
    ipva = extrair(xlsx, 'IPVA_Bolão.dez', 7, {'B', 'C', 'D', 'H', 'I', 'J'})
    por_codigo = {d['C']: d for d in ipva}
    if len(icms) != 246 or len(ipva) != 246 or len(por_codigo) != 246:
        raise ValueError('Quantidade inesperada de municípios; revise a planilha antes de importar.')
    registros = []
    for d in icms:
        outro = por_codigo.get(d['C'])
        if not outro or outro['D'].strip() != d['D'].strip():
            raise ValueError('Município ausente ou incompatível no IPVA: ' + d['D'])
        registros.append((d['C'], d['D'].strip(), 2025,
                          round(float(d['G']), 2), round(float(d['H']), 2), round(float(d['I']), 2),
                          round(float(outro['H']), 2), round(float(outro['I']), 2), round(float(outro['J']), 2)))
    banco = Path(banco)
    banco.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(banco) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS repasses_municipais (
            codigo_municipio TEXT NOT NULL,
            municipio TEXT NOT NULL,
            ano INTEGER NOT NULL,
            icms_20 REAL NOT NULL,
            fundeb_icms_5 REAL NOT NULL,
            icms_repassado REAL NOT NULL,
            ipva_40 REAL NOT NULL,
            fundeb_ipva_10 REAL NOT NULL,
            ipva_repassado REAL NOT NULL,
            PRIMARY KEY (codigo_municipio, ano))''')
        con.execute('DELETE FROM repasses_municipais WHERE ano=2025')
        con.executemany('''INSERT INTO repasses_municipais VALUES (?,?,?,?,?,?,?,?,?)''', registros)
        con.execute('''CREATE TABLE IF NOT EXISTS fontes (nome TEXT PRIMARY KEY, descricao TEXT)''')
        con.execute('INSERT OR REPLACE INTO fontes VALUES (?,?)',
                    ('conciliacao_2025','Conciliação das Distribuições 2025; ICMS_Bolão.dez e IPVA_Bolão.dez; totais anuais acumulados'))
        n = con.execute('SELECT COUNT(*) FROM repasses_municipais').fetchone()[0]
    print(f'Banco criado em: {banco} | Municípios: {n} | Ano: 2025')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--arquivo', default='dados/Conciliacao_das_Distribuicoes-2025.xlsx')
    parser.add_argument('--banco', default='saida/goias_bi.db')
    args = parser.parse_args()
    carregar(args.arquivo, args.banco)
