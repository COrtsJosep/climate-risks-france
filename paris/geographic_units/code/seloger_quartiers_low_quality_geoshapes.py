### 0. NOT FOR FINAL USE
# Generates polygons that are too low resolution

### 1. MODULE IMPORTS
import time
import tqdm
import json
import shapely
import requests
import geopandas as gpd
from pathlib import Path

### 2. DIRECTORY DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. DICTIONARY CREATION 
municipalityIds = {
    'AD08FR36650',
    'AD08FR36666',
    'AD08FR36667',
    'AD08FR36635',
    'AD08FR36644',
    'AD08FR36669',
    'AD08FR36661',
    'AD08FR36674',
    'AD08FR36647',
    'AD08FR31096',
	'AD08FR36659',
	'AD08FR36662',
	'AD08FR36637',
	'AD08FR36639',
	'AD08FR36640',
	'AD08FR36651',
	'AD08FR36654',
	'AD08FR36658',
	'AD08FR36664'
}
placeIds, labels, postal_codes = [], [], []

for municipalityId in tqdm.tqdm(municipalityIds, desc = 'Municipalities'):
    response = requests.get(
        f'https://www.seloger.com/search-mfe-bff/places/relations?placeId={municipalityId}&placeType=NBH2',
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0'}
    )
    relations = response.json()['relations']

    placeIds += [relation['placeId'] for relation in relations]
    labels += [relation['label'] for relation in relations]
    postal_codes += [relation['postal_codes'][0] if relation['postal_codes'] else None for relation in relations]
    time.sleep(1)

### 4. POLYGON FETCHING
geometries = []
for placeId in tqdm.tqdm(placeIds, desc = 'Places'):
    response = requests.get(f'https://www.seloger.com/serp-bff/places/geom?placeId={placeId}&level_of_detail=18')
    geojson = json.dumps(response.json()['result'])
    geometries.append(shapely.from_geojson(geojson))
    time.sleep(1)

### 5. GEODATAFRAME CREATION
gdf = gpd.GeoDataFrame(
    data = {
        'placeId': placeIds,
        'label': labels,
        'postal_code': postal_codes,
        'geometry': geometries
    },
    crs = 'EPSG:4326'
)

### 6. EXPORT
gdf.to_file(data_dir / 'seloger_quartiers_low_quality.geojson', driver = 'GeoJSON')
gdf.explore().save(figures_dir / 'seloger_quartiers_low_quality.html')
