### 1. MODULE IMPORTS
import tqdm
import shapely
import pandas as pd
import geopandas as gpd
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'
geoshapes_dir = code_dir.parent.parent / 'geographic_units' / 'data'

### 3. DATA IMPORTS
print('Loading Heat Stress geotable...')
gdf_hs = gpd.read_file(data_dir / 'heat_stress_geoshapes.zip') # hs: heatstress
gdf_hs = gdf_hs.to_crs('EPSG:4326') # set same coordinate system as the other gdf
gdf_hs.loc[:, 'geometry'] = gdf_hs.force_2d() # flatten geometries to 2D

print('Loading Conseils de Quartier geotable...')
gdf_cq = gpd.read_file(geoshapes_dir / 'conseils_de_quartier_geoshapes.geojson').set_index('conseil_de_quartier') # cq: Conseil de Quartier

assert gdf_hs.crs == gdf_cq.crs, 'The geotables have different coordinate systems!'

### 4. MISC DEFINITION
def geo_weight_relative(
    p1: shapely.geometry.polygon.Polygon, 
    p2: shapely.geometry.polygon.Polygon
) -> float:
    ''' 
    Returns the area of the intersection between two polygons.
    '''
    return p1.intersection(p2).area

numeric_cols = [ # num. variables in the heatstress table
    'svf',
    'aspecratio',
    'hauteurmoy',
    'perméable',
    'voirie',
    'bati',
    'rugosite_t',
    'admitance',
    'albedo',
    'fluchaleur',
    'aleaj_note',
    'alean_note',
    'alea_j_cl',
    'sensi_j_cl',
    'incap_j_cl',
    'alea_n_cl',
    'sensi_n_cl',
    'incap_n_cl',
    'vulnj_note',
    'vulnn_note',
    'st_areasha',
    'st_lengths'
 ]

### 5. COMPUTATION
print('Calculating averages...')
series = []
for cq in tqdm.tqdm(gdf_cq.index): # takes around 10 minutes
    # take the polygon of the Conseil de Quartier
    cq_polygon = gdf_cq.loc[cq, 'geometry'] 
    
    # then calculate the area of the intersection with every single IMU,
    # and normalize the series so that the sum equals one
    gdf_hs.loc[:, 'geo_weight'] = gdf_hs.loc[:, 'geometry'].apply(lambda imu_polygon: geo_weight_relative(cq_polygon, imu_polygon))
    gdf_hs.loc[:, 'geo_weight'] = gdf_hs.loc[:, 'geo_weight'] / gdf_hs.loc[:, 'geo_weight'].sum()
    
    # now calculate the weighted average (normalized weights * variable),
    # for all variables at once using a matrix multiplication
    s = gdf_hs.loc[:, numeric_cols].multiply(gdf_hs.loc[:, 'geo_weight'], axis = 0).sum() 
    
    # set the name of the series to the name of the Conseil de Quartier
    s.name = cq
    
    # concatenate all series in a list, to later merge them in a df
    series.append(s)
    
df_wa = pd.DataFrame(series).rename_axis('conseil_de_quartier') # wa: weighted average

### 6. FIGURES
print('Exporting maps...')
gdf_cq.explore().save(figures_dir / 'map_per_conseil_de_quartier.html')
gdf_cq.join(df_wa).explore('fluchaleur').save(figures_dir / 'fluchaleur_map_per_conseil_de_quartier.html')
gdf_cq.join(df_wa).explore('vulnj_note').save(figures_dir / 'vulnj_note_map_per_conseil_de_quartier.html')
gdf_cq.join(df_wa).explore('vulnn_note').save(figures_dir / 'vulnn_note_map_per_conseil_de_quartier.html')

### 7. DATA EXPORTS
print('Exporting data...')
df_wa.to_csv(data_dir / 'conseils_de_quartier_heat_stress.csv')
