### 1. MODULE IMPORTS
import urllib.request
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

### 3. DATA DOWNLOADS
## Heatstress geoshapes
# zip URL from https://data-iau-idf.opendata.arcgis.com/datasets/iau-idf::ilots-de-chaleur-urbains-icu-classification-des-imu-en-zone-climatique-locale-lcz-al%C3%A9as-et-vuln%C3%A9rabilit%C3%A9s-%C3%A0-la-chaleur-de-jour-et-de-nuit-en-%C3%AEle-de-france/about
heatstress_zip_url = 'https://hub.arcgis.com/api/v3/datasets/2846134ea6b94177af1366d11e517187_18/downloads/data?format=shp&spatialRefId=2154&where=1%3D1'
heatstress_zip_destination = data_dir / 'heat_stress_geoshapes.zip'
print('Retrieving the Heat Stress ZIP file...')
urllib.request.urlretrieve(heatstress_zip_url, heatstress_zip_destination)
