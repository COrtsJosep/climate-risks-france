### 1. MODULE IMPORTS
import ast
import shapely
import pandas as pd
import geopandas as gpd
from pathlib import Path

### 2. DIRECTORY DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. DATA PREPARATION
with open(data_dir / 'response_list.txt', 'r') as f:
    response_list_string = f.read()
    
response_list = ast.literal_eval(response_list_string)
df_rl = pd.DataFrame(data = response_list)
df_rl = df_rl.loc[df_rl.loc[:, 'HousePrice'].apply(lambda x: type(x) == dict)]
df_rl.loc[:, 'HousePrice'] = df_rl.loc[:, 'HousePrice'].apply(lambda d: d['parsedValue'])
df_rl.loc[:, 'ApartmentPrice'] = df_rl.loc[:, 'ApartmentPrice'].apply(lambda d: d['parsedValue'])
df_rl.loc[:, 'CenterLat'] = df_rl.loc[:, 'CenterLat'].apply(lambda d: d['parsedValue'] if type(d) == dict else d)
df_rl.loc[:, 'CenterLong'] = df_rl.loc[:, 'CenterLong'].apply(lambda d: d['parsedValue'] if type(d) == dict else d)
df_rl.loc[:, 'geometry'] = df_rl.loc[:, 'Wkt'].apply(lambda wkt: shapely.from_wkt(wkt))

gdf_rl = gpd.GeoDataFrame(data = df_rl.drop_duplicates().to_dict(orient = 'list'), crs = 'EPSG:4326')
gdf_lq = gpd.read_file(data_dir / 'seloger_quartiers_low_quality_geoshapes.geojson').set_index('label')

gdf_rl = (
    gdf_rl
    .loc[gdf_rl.loc[:, 'Label'].isin(gdf_lq.index), ['Label', 'geometry']]
    .sort_values('Label')
    .set_index('Label')
)

### 4. MERGING
gdf = (
    gdf_rl
    .join(gdf_lq, rsuffix = '_lq')
    .reset_index()
    .rename(columns = {'postal_code': 'code_postal', 'Label': 'seloger_quartier'})
    .loc[:, ['seloger_quartier', 'code_postal', 'geometry']]
    .set_geometry('geometry')
    .sort_values(by = ['code_postal', 'seloger_quartier'])
    .to_crs('EPSG:4326')
)

### 5. EXPORT
gdf.to_file(data_dir / 'seloger_quartiers_geoshapes.geojson')
gdf.explore().save(figures_dir / 'seloger_quartiers.html')
gdf_lq.explore().save(figures_dir / 'seloger_quartiers_low_quality.html')
