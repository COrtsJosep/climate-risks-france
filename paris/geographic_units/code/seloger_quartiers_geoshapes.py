### 1. MODULE IMPORTS
import ast
import shapely
import pandas as pd
import geopandas as gpd
from pathlib import Path
import contextily as ctx
from matplotlib import pyplot as plt

### 2. DIRECTORY DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. DATA PREPARATION
with open(data_dir / 'response_list.txt', 'r') as f:
    response_list_string = f.read()
    
response_list = ast.literal_eval(response_list_string)
df_rl = pd.DataFrame(data = response_list)
df_rl.loc[:, 'geometry'] = df_rl.loc[:, 'Wkt'].apply(lambda wkt: shapely.from_wkt(wkt))

gdf_rl = gpd.GeoDataFrame(
    data = df_rl.loc[:, ['Label', 'geometry']].drop_duplicates().to_dict(orient = 'list'), 
    crs = 'EPSG:4326'
)
gdf_lq = gpd.read_file(data_dir / 'seloger_quartiers_low_quality.geojson').set_index('label')

def match_quartiers(name_target, shape_target) -> bool:
    for name, shape in zip(gdf_lq.index, gdf_lq.geometry):
        if name == name_target and shape.intersects(shape_target):
            return True
    return False

gdf_rl = (
    gdf_rl
    .loc[
        gdf_rl.apply(lambda gdf: match_quartiers(gdf['Label'], gdf['geometry']), axis = 1), 
        ['Label', 'geometry']
    ]
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
polygon_by = gdf_rl.loc['Bercy'].reset_index().loc[0, 'geometry']
gdf_rl = gdf_rl.loc[gdf_rl.index != 'Bercy']
gdf_rl.loc['Bercy', 'geometry'] = polygon_by

## Solves: There is one extra Seine et Berges, which has to be split up between the others
geom_collection_sb = gdf_rl.loc[gdf_rl.loc[:, 'geometry'].apply(lambda x: type(x) != shapely.Polygon), 'geometry'].item()
polygon_sb_0, polygon_sb_1, polygon_sb_2, _  = geom_collection_sb.geoms
gdf_rl_sb = gdf_rl.loc['Seine et Berges'].copy()
gdf_rl_sb.iloc[1, 0] = gdf_rl_sb.iloc[1, 0].union(polygon_sb_2)
gdf_rl_sb.iloc[4, 0] = gdf_rl_sb.iloc[4, 0].union(polygon_sb_0).union(polygon_sb_1)
gdf_rl.loc['Seine et Berges'] = gdf_rl_sb
gdf_rl = gdf_rl.loc[gdf_rl.loc[:, 'geometry'].apply(lambda x: type(x) != shapely.GeometryCollection)]

### 5. MERGING
gdf_rl = gdf_rl.sort_values('Label')

gdf_rl = gdf_rl.to_crs('EPSG:3857') # set non-geo crs to be able to compute distances in the sjoin later
gdf_rl.loc[:, 'centroid'] = gdf_rl.loc[:, 'geometry'].apply(lambda p: p.centroid)
gdf_rl = gdf_rl.set_geometry('centroid') # calculate centroid for the sjoin (problem of IdSL being inside SeB)
gdf_lq = gdf_lq.to_crs('EPSG:3857')
gdf_lq.loc[:, 'centroid'] = gdf_lq.loc[:, 'geometry'].apply(lambda p: p.centroid)
gdf_lq = gdf_lq.set_geometry('centroid')

nonunique_names = (
    'Seine et Berges',
    'Sud',
    'Centre',
    'Centre Ville', 
    'Centre Ville-Mairie',
    'Nord',
    'Anatole France',
    "L'Avenir",
    'Bercy'
)
    
gdf_unique = gdf_lq.loc[~gdf_lq.index.isin(nonunique_names)].join(
    other = gdf_rl.loc[~gdf_rl.index.isin(nonunique_names)],
    lsuffix = '_lq',
    rsuffix = '_rl'
)
gdf_nonunique = gdf_lq.loc[gdf_lq.index.isin(nonunique_names)].sjoin_nearest(
    right = gdf_rl.loc[gdf_rl.index.isin(nonunique_names)],
    lsuffix = 'lq',
    rsuffix = 'rl'
) 

gdf = (
    pd
    .concat([gdf_unique, gdf_nonunique])
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

centre_paris = shapely.Point((2.348922, 48.853328)) # square in front of Notre Dame
ax = gdf.boundary.plot(figsize = (16, 16), color = 'k')
ctx.add_basemap(
    ax, 
    zoom = 13,
    source = ctx.providers.CartoDB.Positron, 
    crs = gdf.crs.to_string()
)
note = ''
iterator = (
    gdf
    .assign(dtc = lambda gdf: gdf.loc[:, 'geometry'].apply(lambda sl: sl.distance(centre_paris)))
    .sort_values(by = 'dtc')
    .iterrows()
)
for i, row in enumerate(iterator):
    sl_name = f"{row[1]['seloger_quartier']}, {row[1]['code_postal']}"
    sl = row[1]['geometry']
    
    note += f'{i + 1}: {sl_name}\n'
    
    x, y = sl.representative_point().coords[0]    
    ax.plot(x, y, 'wo', mec = 'k', ms = 11)
    ax.text(x, y, str(i + 1), {'size': 5, 'verticalalignment': 'center', 'horizontalalignment': 'center'})
    
plt.figtext(0.1, -2.7, note, ha = 'left')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('SeLoger Quartier Boundaries')
plt.savefig(figures_dir / 'sl_map.pdf', bbox_inches = 'tight')
