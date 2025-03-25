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

heatstress_geoshapes_path = data_dir / 'heatstress_geoshapes.zip'
iris_geoshapes_path = data_dir / 'iris_geoshapes.zip'
iris_commune_crosswalk_path = data_dir / 'iris_commune_crosswalk.xlsx'
commune_code_postal_crosswalk_path = data_dir / 'commune_code_postal_crosswalk.csv'

### 3. DATA IMPORTS
print('Loading Heat Stress geotable...')
gdf_hs = gpd.read_file(heatstress_geoshapes_path) # hs: heatstress
gdf_hs.loc[:, 'geometry'] = gdf_hs.force_2d() # flatten geometries to 2D

print('Loading IRIS geotable...')
gdf_ir = ( # ir: IRIS
    gpd
    .read_file(iris_geoshapes_path)
    .loc[:, ['CODE_IRIS', 'geometry']]
    .set_index('CODE_IRIS')
)

assert gdf_hs.crs == gdf_ir.crs, 'The geotables have different coordinate systems!'

print('Loading IRIS - Commune crosswalk...')
df_ic = ( # ic: IRIS - Commune
    pd
    .read_excel(
        iris_commune_crosswalk_path,
        sheet_name = 'Emboitements_IRIS',
        header = 5, # table starts on the 6th row
    )
    .query('REG == 11') # only region 11 (Île-de-France)
    .loc[:, ['CODE_IRIS', 'DEPCOM']]
    .set_index('CODE_IRIS')
)

print('Loading Commune - Code Postal crosswalk...')
df_cc = ( # cc: Commune - Code Postal
    pd
    .read_csv(
        commune_code_postal_crosswalk_path, 
        usecols = ['code_commune_insee', 'code_postal'],
        dtype = str
    )
    .drop_duplicates()
    .reset_index(drop = True)
    .rename(columns = {'code_commune_insee': 'DEPCOM', 'code_postal': 'CP'})
)
df_cc.loc[df_cc.loc[:, 'CP'] == '93380', 'DEPCOM'] = '93059' # There is one error on Pierrefite-sur-Seine

### 4. JOIN CROSSWALKS
print('Joining tables...')
gdf_cp = (
    gdf_ir
    .join(df_ic, how = 'inner', sort = True)
    .merge(df_cc, how = 'left', on = 'DEPCOM')
    .dropna(subset = 'CP')
    .dissolve(by = 'CP')
)

### 5. MISC DEFINITION
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
 
### 6. COMPUTATION
print('Calculating averages...')
series = []
for cp in tqdm.tqdm(gdf_cp.index): # takes around 10 minutes
    # take the polygon of the Code Postal
    cp_polygon = gdf_cp.loc[cp, 'geometry'] 
    
    # then calculate the area of the intersection with every single IMU,
    # and normalize the series so that the sum equals one
    gdf_hs.loc[:, 'geo_weight'] = gdf_hs.loc[:, 'geometry'].apply(lambda imu_polygon: geo_weight_relative(cp_polygon, imu_polygon))
    gdf_hs.loc[:, 'geo_weight'] = gdf_hs.loc[:, 'geo_weight'] / gdf_hs.loc[:, 'geo_weight'].sum()
    
    # now calculate the weighted average (normalized weights * variable),
    # for all variables at once using a matrix multiplication
    s = gdf_hs.loc[:, numeric_cols].multiply(gdf_hs.loc[:, 'geo_weight'], axis = 0).sum() 
    
    # set the name of the series to the Code Postal
    s.name = cp
    
    # concatenate all series in a list, to later merge them in a df
    series.append(s)
    
df_wa = pd.DataFrame(series) # wa: weighted average

### 6. FIGURES
print('Exporting maps...')
gdf_cp.explore().save(figures_dir / 'map_per_code_postal.html')
gdf_cp.join(df_wa).explore('fluchaleur').save(figures_dir / 'fluchaleur_map_per_code_postal.html')
gdf_cp.join(df_wa).explore('vulnj_note').save(figures_dir / 'vulnj_note_map_per_code_postal.html')
gdf_cp.join(df_wa).explore('vulnn_note').save(figures_dir / 'vulnn_note_map_per_code_postal.html')
    
### 7. DATA EXPORTS
print('Exporting data...')
df_wa.to_csv(data_dir / 'code_postal_heatstress.csv')
