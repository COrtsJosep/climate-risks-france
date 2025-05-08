### 0. NOT FOR FINAL USE
# Generates polygons that are too low resolution

### 1. MODULE IMPORTS
import json
import shapely
import requests
import geopandas as gpd
from pathlib import Path

### 2. DIRECTORY DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dif.parent / 'figures'

### 3. DICTIONARY CREATION 
response = requests.get('https://www.seloger.com/search-mfe-bff/places/relations?paceId=AD08FR31096&placeType=NBH2')

placeIds = [relation['placeId'] for relation in relations]
labels = [relation['label'] for relation in relations]
postal_codes = [relation['postal_codes'][0] if relation['postal_codes'] else None for relation in relations]

### 4. POLYGON FETCHING
geometries = []
for placeId in placeIds:
    response = requests.get(f'https://www.seloger.com/serp-bff/places/geom?placeId={placeId}&level_of_detail=18')
    geojson = json.dumps(response.json()['result'])
    geometries.append(shapely.from_geojson(geojson))

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
