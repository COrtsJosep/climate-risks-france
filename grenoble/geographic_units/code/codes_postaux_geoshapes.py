### 1. MODULE IMPORTS
import shapely
import zipfile
import pandas as pd
import urllib.request
import geopandas as gpd
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. DONWLOADS
## IRIS - Commune crosswalk
# zip url from https://www.insee.fr/fr/information/7708995#
iris_zip_url = 'https://www.insee.fr/fr/statistiques/fichier/7708995/reference_IRIS_geo2024.zip'
iris_zip_destination = data_dir / 'reference_IRIS_geo2024.zip'
print('Retrieving the IRIS - Commune Crosswalk ZIP file...')
urllib.request.urlretrieve(iris_zip_url, iris_zip_destination)
print('Extracting IRIS - Commune Crosswalk xlsx file...')
with zipfile.ZipFile(iris_zip_destination, 'r') as zip_object:
    zip_object.extractall(path = data_dir)
iris_zip_destination.with_suffix('.xlsx').rename(data_dir / 'iris_commune_crosswalk.xlsx')
print('Deleting the IRIS - Commune Crosswalk ZIP file...')
iris_zip_destination.unlink()

## Code Postal - Commune crosswalk
# csv url from https://datanova.laposte.fr/datasets/laposte-hexasmal
code_postal_csv_url = 'https://datanova.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/metadata-attachments/base-officielle-codes-postaux.csv'
code_postal_csv_destination = data_dir / 'commune_code_postal_crosswalk.csv'
print('Retrieving the Commune - Code Postal csv file...')
urllib.request.urlretrieve(code_postal_csv_url, code_postal_csv_destination)

## IRIS geoshapes
# 7z url from https://geoservices.ign.fr/irisge
iris_7z_url = 'https://data.geopf.fr/telechargement/download/IRIS-GE/IRIS-GE_3-0__SHP_LAMB93_FXX_2024-01-01/IRIS-GE_3-0__SHP_LAMB93_FXX_2024-01-01.7z'
iris_7z_destination = data_dir / 'IRIS-GE_3-0__SHP_LAMB93_FXX_2024-01-012.7z'
print('Retrieving the IRIS 7z file...')
try:
    urllib.request.urlretrieve(iris_7z_url, iris_7z_destination) 
except:
    print('Failed with 403 error. Why would géoservices do that? Anyways, I will download the files by hand and save them in iris_geoshapes.zip ...')
    
### 4. GEOSHAPE CREATION
print('\n\nLoading IRIS geotable...')
gdf_ir = ( # ir: IRIS
    gpd
    .read_file(data_dir / 'iris_geoshapes.zip')
    .loc[:, ['CODE_IRIS', 'geometry']]
    .set_index('CODE_IRIS')
)

print('Loading IRIS - Commune crosswalk...')
df_ic = ( # ic: IRIS - Commune
    pd
    .read_excel(
        data_dir / 'iris_commune_crosswalk.xlsx',
        sheet_name = 'Emboitements_IRIS',
        header = 5, # table starts on the 6th row
    )
    .query('REG == 84') # only region 84 (Auvergne-Rhône-Alpes)
    .loc[:, ['CODE_IRIS', 'DEPCOM']]
    .set_index('CODE_IRIS')
)

print('Loading Commune - Code Postal crosswalk...')
df_cc = ( # cc: Commune - Code Postal
    pd
    .read_csv(
        data_dir / 'commune_code_postal_crosswalk.csv', 
        usecols = ['code_commune_insee', 'code_postal'],
        dtype = str
    )
    .drop_duplicates()
    .reset_index(drop = True)
    .rename(columns = {'code_commune_insee': 'DEPCOM', 'code_postal': 'CP'})
)

### 5. JOIN
print('Joining tables...')
gdf = (
    gdf_ir
    .join(df_ic, how = 'inner', sort = True)
    .merge(df_cc, how = 'left', on = 'DEPCOM')
    .dropna(subset = 'CP')
    .dissolve(by = 'CP')
    .loc[:, 'geometry']
    .rename_axis('code_postal')
)

### 6. CORRECTIONS
## Grenoble commune has two codes postaux -- so in gdf, they share the same
## overlapping shape. In reality, they should be split by a big road that
## crosses the city: north of it is 38000, south is 38100. I have drawn
## a rough line that should split the areas and assign to each one the correct
## area.
d1090_coordinates = (
	(912000.4509191889, 6457039.053827161),
	(913575.7331876741, 6457133.469878229),
	(914617.1009851759, 6457616.500211682),
	(915675.3285901955, 6458380.670238501),
)
d1090_line = shapely.LineString(coordinates = d1090_coordinates)
gdf.loc[gdf.index == '38000'] = shapely.ops.split(
    gdf.loc[gdf.index == '38000'].item(),
    d1090_line
).geoms[1]
gdf.loc[gdf.index == '38100'] = shapely.ops.split(
    gdf.loc[gdf.index == '38100'].item(),
    d1090_line
).geoms[0]

### 7. EXPORT
gdf.to_file(data_dir / 'codes_postaux_geoshapes.geojson')
gdf.explore().save(figures_dir / 'codes_postaux.html')
