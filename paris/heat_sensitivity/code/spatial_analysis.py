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

def map_lcz_to_sensibilite(lcz: str) -> str:
    '''
    Translates from the LCZ type to the Sensitivity category.
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
        
def map_sensibilte_to_int(sns: str) -> int:
    '''
    Transforms from Sensibility category to a numeric scale.
    '''

    if sns == 'Très Forte Sensibilité':
        return 5
    elif sns == 'Forte Sensibilité':
        return 4
    elif sns == 'Sensibilité Moyenne':
        return 3
    elif sns == 'Faible Sensibilité':
        return 2
    elif sns == 'Sensibilité Variable':
        return 1
    else: # 'Sensibilité Faible à Nulle'
        return 0
        
### 3. DATA LOADING
gdf_lcz = ( # lcz: local climatic zone
    gpd
    .read_file(data_dir / 'heat_sensitivity_geoshapes.zip') 
    .assign(
        sns_str = lambda gdf: gdf.loc[:, 'lcz'].map(map_lcz_to_sensibilite),
        sns_int = lambda gdf: gdf.loc[:, 'sns_str'].map(map_sensibilte_to_int)
    )
    .set_index('identifier')
)

gdf_cq = ( # cq: conseil de quartier
    gpd
    .read_file(geoshapes_dir / 'conseils_de_quartier_geoshapes.geojson')
    .set_index(['conseil_de_quartier'])
    .to_crs(gdf_lcz.crs)
)

### 5. COMPUTATION
print('Calculating averages...')
series = []
for cq in tqdm.tqdm(gdf_cq.index): # takes around 10 minutes
    # take the polygon of the conseil_de Quartier
    cq_polygon = gdf_cq.loc[cq, 'geometry'] 
    result_s = pd.Series()
    
    # then calculate the area of the intersection with every single LCZ,
    # and normalize the series so that the sum equals one
    gdf_lcz.loc[:, 'geo_weight'] = gdf_lcz.loc[:, 'geometry'].apply(lambda lcz_polygon: cq_polygon.intersection(lcz_polygon).area)
    gdf_lcz.loc[:, 'geo_weight'] = gdf_lcz.loc[:, 'geo_weight'] / gdf_lcz.loc[:, 'geo_weight'].sum()
    
    nonzero_weight_mask = gdf_lcz.loc[:, 'geo_weight'] > 0
    gdf_lcz_sub = (
        gdf_lcz
        .loc[nonzero_weight_mask]
        .copy()
    )    
    result_s['mean'] = gdf_lcz_sub.loc[:, 'sns_int'].multiply(gdf_lcz_sub.loc[:, 'geo_weight'], axis = 0).sum() 
    
    # now the percentile differences
    gdf_lcz_sub.sort_values('sns_int', inplace = True)
    cumsum = gdf_lcz_sub.loc[:, 'geo_weight'].cumsum().round(5)
    result_s['median'] = gdf_lcz_sub.loc[cumsum >= 0.5, 'sns_int'].iloc[0]
    result_s['mode'] = gdf_lcz_sub.loc[:, ['sns_int', 'geo_weight']].groupby(by = 'sns_int').sum().idxmax().item()
    
    # now the weighted standard deviation, like here: https://www.itl.nist.gov/div898/software/dataplot/refman2/ch2/weightsd.pdf
    N_positive = gdf_lcz_sub.shape[0]
    numerator = ((gdf_lcz_sub.loc[:, 'sns_int'] - result_s['mean']) ** 2).multiply(gdf_lcz_sub.loc[:, 'geo_weight'], axis = 0).sum()
    denominator = (N_positive - 1) * gdf_lcz_sub.loc[:, 'geo_weight'].sum() / N_positive
    result_s['std'] = (numerator / denominator) ** 0.5
    
    gdf_lcz_sub.loc[:, 'delta'] = gdf_lcz_sub.loc[:, 'sns_int'] - result_s['mode']
    result_s['mean_delta'] = gdf_lcz_sub.loc[:, 'delta'].multiply(gdf_lcz_sub.loc[:, 'geo_weight'], axis = 0).sum() 
    result_s['median_delta'] = gdf_lcz_sub.loc[cumsum >= 0.5, 'delta'].iloc[0]
    result_s['mode_delta'] = gdf_lcz_sub.loc[:, ['delta', 'geo_weight']].groupby(by = 'delta').sum().idxmax().item()
    
    for cutoff in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        result_s[f'{cutoff}_delta'] = gdf_lcz_sub.loc[cumsum >= cutoff, 'delta'].iloc[0]    
        
    # set the name of the series to the name of the Conseil de Quartier
    result_s.name = cq
    
    # concatenate all series in a list, to later merge them in a df
    series.append(result_s)
    
df_rs = pd.DataFrame(series) # rs: results
df_rs.to_csv(data_dir / 'sns_int_statistics.csv')
