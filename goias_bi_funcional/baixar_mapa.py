from pathlib import Path
import requests

URL = 'https://cdn.jsdelivr.net/gh/henriquemalvar/br-geojson@main/dist/municipios/GO.geojson'
destino = Path(__file__).resolve().parent / 'dados' / 'goias_municipios.geojson'
resposta = requests.get(URL, timeout=60)
resposta.raise_for_status()
geo = resposta.json()
if geo.get('type') != 'FeatureCollection' or not geo.get('features'):
    raise ValueError('Arquivo GeoJSON sem geometrias válidas')
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_bytes(resposta.content)
print(f'Mapa salvo em: {destino} ({len(geo["features"])} geometrias)')
