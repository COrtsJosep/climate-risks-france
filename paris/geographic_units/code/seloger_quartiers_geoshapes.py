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

### 4. INCONSISTENCY SOLVING
## Solves: Île de la Cité is split in two
polygon_ic = gdf_rl.loc[gdf_rl.index == 'Île de la Cité'].dissolve().loc[0, 'geometry']
gdf_rl = gdf_rl.loc[gdf_rl.index != 'Île de la Cité']
gdf_rl.loc['Île de la Cité', 'geometry'] = polygon_ic

## Solves: Île Sant Louis is overlapped by a Seine et Berges polygon
polygon_isl = gdf_rl.loc[gdf_rl.index == 'Île Saint Louis', 'geometry'].item()
gdf_rl.loc[gdf_rl.index == 'Seine et Berges', 'geometry'] = gdf_rl.loc[gdf_rl.index == 'Seine et Berges', 'geometry'].apply(lambda polygon_sb: polygon_sb.difference(polygon_isl))

## Solves: There are two Bercys, only one is in Paris city
polygon_by = gdf_rl.loc['Bercy'].reset_index().loc[1, 'geometry']
gdf_rl = gdf_rl.loc[gdf_rl.index != 'Bercy']
gdf_rl.loc['Bercy', 'geometry'] = polygon_by

## Solves: There is one extra Seine et Berges, which has to be split up between the others
geom_collection_sb = gdf_rl.loc[gdf_rl.loc[:, 'geometry'].apply(lambda x: type(x) != shapely.Polygon), 'geometry'].item()
polygon_sb_0, polygon_sb_1, polygon_sb_2, _  = geom_collection_sb.geoms
gdf_rl_sb = gdf_rl.loc['Seine et Berges'].copy()
gdf_rl_sb.iloc[1, 0] = gdf_rl_sb.iloc[1, 0].union(polygon_sb_2)
gdf_rl_sb.iloc[4, 0] = gdf_rl_sb.iloc[4, 0].union(polygon_sb_0).union(polygon_sb_1)
gdf_rl.loc['Seine et Berges'] = gdf_rl_sb
gdf_rl = gdf_rl.loc[gdf_rl.loc[:, 'geometry'].apply(lambda x: type(x) == shapely.Polygon)]

### 5. MERGING
gdf_rl = gdf_rl.sort_values('Label')

gdf_rl = gdf_rl.to_crs('EPSG:3857') # set non-geo crs to be able to compute distances in the sjoin later
gdf_rl.loc[:, 'centroid'] = gdf_rl.loc[:, 'geometry'].apply(lambda p: p.centroid)
gdf_rl = gdf_rl.set_geometry('centroid') # calculate centroid for the sjoin (problem of IdSL being inside SeB)
gdf_lq = gdf_lq.to_crs('EPSG:3857')
gdf_lq.loc[:, 'centroid'] = gdf_lq.loc[:, 'geometry'].apply(lambda p: p.centroid)
gdf_lq = gdf_lq.set_geometry('centroid')

gdf_no_sb = gdf_lq.loc[gdf_lq.index != 'Seine et Berges'].join(
    other = gdf_rl.loc[gdf_rl.index != 'Seine et Berges'],
    lsuffix = '_lq',
    rsuffix = '_rl'
)
gdf_sb = gdf_lq.loc['Seine et Berges'].sjoin_nearest(
    right = gdf_rl.loc['Seine et Berges'],
    lsuffix = 'lq',
    rsuffix = 'rl'
) 

gdf = (
    pd
    .concat([gdf_no_sb, gdf_sb])
    .reset_index()
    .rename(columns = {'geometry_rl': 'geometry', 'postal_code': 'code_postal', 'label': 'seloger_quartier'})
    .loc[:, ['seloger_quartier', 'code_postal', 'geometry']]
    .set_geometry('geometry')
    .fillna('75012') # the one missing code_postal should be 75012
    .sort_values(by = ['code_postal', 'seloger_quartier'])
    .to_crs('EPSG:4326')
)

### 6. EXPORT
gdf.to_file(data_dir / 'seloger_quartiers_geoshapes.geojson')
gdf.explore().save(figures_dir / 'seloger_quartiers.html')
gdf_lq.set_geometry('geometry').explore().save(figures_dir / 'seloger_quartiers_low_quality.html')
