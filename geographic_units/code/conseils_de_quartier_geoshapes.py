### 1. MODULE IMPORTS
import urllib.request
import geopandas as gpd
from pathlib import Path


### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

### 3. DOWNLOAD
# zip url from https://www.data.gouv.fr/fr/datasets/les-conseils-de-quartier-par-arrondissement-prs/
conseils_zip_url = 'https://opendata.paris.fr/explore/dataset/conseils-quartiers/download?format=shp'
conseils_zip_destination = data_dir / 'conseils_de_quartier_geoshapes.zip'
print('Retrieving the Conseils de Quartier ZIP file...')
urllib.request.urlretrieve(conseils_zip_url, conseils_zip_destination)

### 4. MODIFICATIONS AND EXPORT
(
    gpd
    .read_file(conseils_zip_destination)
    .set_index('nom_quart')
    .rename_axis('conseil_de_quartier')
    .loc[:, 'geometry']
    .to_file(conseils_zip_destination.with_suffix('.geojson'))
)

conseils_zip_destination.unlink()
