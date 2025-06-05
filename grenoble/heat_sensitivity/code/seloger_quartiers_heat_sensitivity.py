### 1. IMPORTS
import tqdm
import pandas as pd
import geopandas as gpd
from pathlib import Path

### 2. PATH & OTHER DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'
geoshapes_dir = code_dir.parent.parent / 'geographic_units' / 'data'

numeric_cols = [
    'hre',
    'are',
    'bur',
    'ror',
    'bsr',
    'war',
    'ver',
    'vhr',
    'Faible Sensibilité',
    'Forte Sensibilité',
    'Sensibilité Faible à Nulle',
    'Sensibilité Moyenne',
    'Sensibilité Variable',
    'Très Forte Sensibilité'
]

def map_lcz_to_sensibilite(lcz: str) -> str:
    '''
    Translates from the LCZ type to the Sensitivity category
    '''
    if lcz in ('1', '2'):
        return 'Très Forte Sensibilité'
    elif lcz == '3':
        return 'Forte Sensibilité'
    elif lcz in ('4', '5'):
        return 'Sensibilité Moyenne'
    elif lcz in ('6', '9'):
        return 'Faible Sensibilité'
    elif lcz in ('7', '8', '10', 'E'):
        return 'Sensibilité Variable'
    else: # letters except E
        return 'Sensibilité Faible à Nulle'

### 3. DATA LOADING
gdf_lcz = gpd.read_file(data_dir / 'heat_sensitivity_geoshapes.zip') # lcz: local climatic zone
gdf_lcz = pd.concat(
    [gdf_lcz, 100 * pd.get_dummies(gdf_lcz.loc[:, 'lcz'].map(map_lcz_to_sensibilite))],
    axis = 1
).set_index('identifier')

gdf_sl = ( # sl: seloger quartier
    gpd
    .read_file(geoshapes_dir / 'seloger_quartiers_geoshapes.geojson')
    .set_index(['seloger_quartier', 'code_postal'])
    .to_crs(gdf_lcz.crs)
)

### 5. COMPUTATION
print('Calculating averages...')
series = []
for sl in tqdm.tqdm(gdf_sl.index): # takes around 10 minutes
    # take the polygon of the SeLoger Quartier
    sl_polygon = gdf_sl.loc[sl, 'geometry'] 
    
    # then calculate the area of the intersection with every single LCZ,
    # and normalize the series so that the sum equals one
    gdf_lcz.loc[:, 'geo_weight'] = gdf_lcz.loc[:, 'geometry'].apply(lambda lcz_polygon: sl_polygon.intersection(lcz_polygon).area)
    gdf_lcz.loc[:, 'geo_weight'] = gdf_lcz.loc[:, 'geo_weight'] / gdf_lcz.loc[:, 'geo_weight'].sum()
    nonzero_weight_mask = gdf_lcz.loc[:, 'geo_weight'] > 0
    
    # now calculate the weighted average (normalized weights * variable),
    # for all variables at once using matrix multiplication
    s = gdf_lcz.loc[nonzero_weight_mask, numeric_cols].multiply(gdf_lcz.loc[nonzero_weight_mask, 'geo_weight'], axis = 0).sum() 
    
    # set the name of the series to the name of the SeLoger Quartier
    s.name = sl
    
    # concatenate all series in a list, to later merge them in a df
    series.append(s)
    
df_wa = pd.DataFrame(series) # wa: weighted average
df_wa.index.names = gdf_sl.index.names

### 6. FIGURES
print('Exporting maps...')
gdf_sl.explore().save(figures_dir / 'map_per_seloger_quartier.html')
gdf_sl.join(df_wa).explore('Très Forte Sensibilité').save(figures_dir / 'tfs_map_per_seloger_quartier.html')
gdf_sl.join(df_wa).explore('bur').save(figures_dir / 'bur_map_per_seloger_quartier.html')

### 7. DATA EXPORTS
print('Exporting data...')
df_wa.to_csv(data_dir / 'seloger_quartiers_heat_sensitivity.csv')
