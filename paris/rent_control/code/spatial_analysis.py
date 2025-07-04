### 1. PATH DEFINITIONS
import colorcet
import numpy as np
import pandas as pd
from tqdm import tqdm
import geopandas as gpd
from pathlib import Path
from matplotlib import pyplot as plt

pd.set_option('future.no_silent_downcasting', True)

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'
geoshapes_dir = code_dir.parent.parent / 'geographic_units' / 'data'

### 3. CONSTANTS
cols = [
    'city', 
    'period', 
    'housingType', 
    'rooms', 
    'epoque', 
    'furnished', 
    'idZone', 
    'ref', 
    'refmaj', 
    'refmin', 
    'geometry'
]
float_cols = ['ref', 'refmaj', 'refmin']
int_cols = ['rooms', 'idZone']

CITY = ['paris', 'plaine-commune', 'est-ensemble']
PERIOD = {
    'paris': ['2015-08-01', '2016-08-01', '2017-08-01', '2019-07-01', '2020-07-01', '2021-07-01', '2022-07-01', '2023-07-01', '2024-07-01'],
    'plaine-commune': ['2021-06-01', '2022-06-01', '2023-06-01', '2024-06-01'],
    'est-ensemble': ['2021-12-01', '2022-06-01', '2023-06-01', '2024-06-01']
}
HOUSING_TYPE = {
    'paris': [''], # no distinction in Paris 
    'plaine-commune': ['_maison', '_appartement'], 
    'est-ensemble': ['_maison', '_appartement']
}
ROOMS = ['_' + str(i) for i in range(1, 5)]
EPOQUE = ['_inf1946', '_1946-1970', '_1971-1990', '_sup1990']
FURNISHED = ['_meuble', '_non-meuble']

### 4. CONCATENATION OF ALL THE GDFs
gdfs = []
for city in CITY:
    for period in PERIOD[city]:
        for housing_type in HOUSING_TYPE[city]:
            for rooms in ROOMS:
                for epoque in EPOQUE:
                    for furnished in FURNISHED:   
                        path = data_dir / 'rent_control_geoshapes' / city / period / f'{housing_type}{rooms}{epoque}{furnished}.geojson'[1:]
                        gdf = gpd.read_file(path)
                    
                        gdf.loc[:, 'city'] = city
                        gdf.loc[:, 'period'] = period
                        gdf.loc[:, 'housingType'] = housing_type[1:] if housing_type != '' else None
                        gdf.loc[:, 'rooms'] = rooms[1:]
                        gdf.loc[:, 'epoque'] = epoque[1:]
                        gdf.loc[:, 'furnished'] = furnished[1:]
                        
                        gdf.loc[:, int_cols] = gdf.loc[:, int_cols].astype(int)
                        gdf.loc[:, float_cols] = gdf.loc[:, float_cols].map(lambda x: x.replace(',', '.')).astype(float)    
                        gdf.loc[:, 'geometry'] = gdf.loc[:, 'geometry'].buffer(0) # buffer(0) to solve POLYGON Z ((2.42459619926827 48.8593851232184 0, 2.42407274878426 48.8595139091785 0), EMPTY) situations in the Est-Ensemble polygons starting in 2022-06-01
                        
                  
                        gdf = gdf.loc[:, cols]
                        gdfs.append(gdf)

for city in CITY: # sanity checks
    gdfs_city = [gdf.loc[:, 'geometry'] for gdf in gdfs if gdf.loc[0, 'city'] == city]
    print(f'All {city.title()} polygons equal?', all([gdfs_city[i].equals(gdfs_city[i+1]) for i in range(len(gdfs_city)-1)]))
    
    gdfs_city_dissolved = [gdf.loc[:, ['idZone', 'geometry']].dissolve(by = 'idZone') for gdf in gdfs if gdf.loc[0, 'city'] == city]
    print(f'All {city.title()} dissolved polygons equal?', all([gdfs_city_dissolved[i].equals(gdfs_city_dissolved[i+1]) for i in range(len(gdfs_city_dissolved)-1)]))
del gdf, gdfs_city, gdfs_city_dissolved

gdf_rc = ( # rc: rent control 
    pd
    .concat(gdfs, axis = 0, ignore_index = True)
    .dissolve(
        by = ['city', 'period', 'housingType', 'rooms', 'epoque', 'furnished', 'idZone'], 
        sort = True, 
        as_index = False,
        dropna = False
    )
)

### 5. JOIN WITH SELOGER QUARTIERS
gdf_sl = gpd.read_file(geoshapes_dir / 'seloger_quartiers_geoshapes.geojson').set_index(['seloger_quartier', 'code_postal']) # sl: SeLoger

gdf_zn = ( # zn: zone
    gdf_rc
    .dissolve(by = 'idZone')
    .loc[:, ['geometry']]
)
   
## 5.2. TRANSLATION OF RENT CONTROL BY ZONE TO BY CODE POSTAL
overlaps = [] # each column corresponds to a SeLoger Quartier, each row corresponds to the % of SeLoger Quartier in each rent control zone 
for sl in gdf_sl.index:
    sl_shape = gdf_sl.loc[sl, 'geometry']
    overlap = gdf_zn.loc[:, 'geometry'].apply(lambda zn_shape: zn_shape.intersection(sl_shape).area / sl_shape.area).rename(sl)
    overlaps.append(overlap)
    
df_ol = pd.concat(overlaps, axis = 1).sort_values(by = 'idZone') # ol: overlap. Is a (#SeLoger Quartier x #Zones) matrix (after being transposed in the next line)
df_ol = (df_ol / df_ol.sum()).T # here I divide by the sum so that all weights add to 1

# filter for last rent control values 
most_recent_periods = set([l[-1] for k, l in PERIOD.items()])
gdf_rc = gdf_rc.loc[(gdf_rc.loc[:, 'period'].isin(most_recent_periods))]

# for Paris, app. and msn values are the same, but not for the others.
# so duplicate the rows for Paris  and fill them with app. and msn.
gdf_rc_non_paris = gdf_rc.query('city != "paris"')
gdf_rc_paris = gdf_rc.query('city == "paris"')
gdf_rc_paris_app = (
    gdf_rc_paris
    .copy()
    .fillna('appartement') # only this col has na
)
gdf_rc_paris_msn = (
    gdf_rc_paris
    .copy()
    .fillna('maison')
)

gdf_rc = pd.concat(
    [gdf_rc_non_paris,
     gdf_rc_paris_app,
     gdf_rc_paris_msn
    ]
)

dfs_rc = []
for rooms in ROOMS:
    for epoque in EPOQUE:
        for furnished in FURNISHED: 
            for housing_type in {housing_type for housing_type in HOUSING_TYPE.values() for housing_type in housing_type if housing_type}:
                # for each combination of rooms, epoque and furnished, calculate the weighted average of the rent control values, for each SLQ.
                # this is done by matrix multiplication: the rent control values of all zones are weighted by the % they contain of a given SLQ.
                df_tmp = (
                    gdf_rc
                    .query(f'rooms == {rooms[1:]} and epoque == "{epoque[1:]}" and furnished == "{furnished[1:]}" and housingType == "{housing_type[1:]}"')
                    .loc[:, ['idZone', 'ref']]
                    .drop_duplicates()
                    .sort_values(by = 'idZone')
                    .set_index('idZone')
                )
                df_rc = (df_ol @ df_tmp).rename(columns = {'ref': 'mean'})

                
                for sl in tqdm(df_ol.index, desc = f'{rooms}{epoque}{furnished}{housing_type}'):
                    df_sl = (
                        pd
                        .concat([df_ol.loc[sl], df_tmp], axis = 1)
                        .loc[df_ol.loc[sl] > 0]
                        .rename(columns = {sl: 'weight'})
                        .sort_values('ref')
                        .assign(cumsum = lambda df: df.loc[:, 'weight'].cumsum().round(5))
                    )
                    
                    df_rc.loc[sl, 'median'] = df_sl.loc[df_sl.loc[:, 'cumsum'] >= 0.5, 'ref'].iloc[0]
                    df_rc.loc[sl, 'mode'] = df_sl.groupby(by = 'ref')['weight'].sum().idxmax().item()     
                    
                    # now the weighted standard deviation, like here: https://www.itl.nist.gov/div898/software/dataplot/refman2/ch2/weightsd.pdf
                    N_positive = df_sl.shape[0]
                    numerator = ((df_sl.loc[:, 'ref'] - df_rc.loc[sl, 'mean']) ** 2).multiply(df_sl.loc[:, 'weight'], axis = 0).sum()
                    denominator = (N_positive - 1) * df_sl.loc[:, 'weight'].sum() / N_positive
                    if denominator < 10 ** -8:
                        df_rc.loc[sl, 'std'] = 0.0
                    else:
                        df_rc.loc[sl, 'std'] = (numerator / denominator) ** 0.5
                    
                    df_sl.loc[:, 'delta'] = df_sl.loc[:, 'ref'] - df_rc.loc[sl, 'mean']
                    
                    df_rc.loc[sl, 'mean_delta'] = df_sl.loc[:, 'delta'].multiply(df_sl.loc[:, 'weight'], axis = 0).sum() 
                    df_rc.loc[sl, 'median_delta'] = df_sl.loc[df_sl.loc[:, 'cumsum'] >= 0.5, 'delta'].iloc[0]
                    df_rc.loc[sl, 'mode_delta'] = df_sl.groupby(by = 'delta')['weight'].sum().idxmax().item() 
    
                    for cutoff in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
                        df_rc.loc[sl, f'{cutoff}_delta'] = df_sl.loc[df_sl.loc[:, 'cumsum'] >= cutoff, 'delta'].iloc[0]  
                
                
                df_rc.loc[:, 'rooms'] = rooms[1:]
                df_rc.loc[:, 'epoque'] = epoque[1:]
                df_rc.loc[:, 'furnished'] = furnished[1:]
                df_rc.loc[:, 'housingType'] = housing_type[1:]
                df_rc = df_rc.rename_axis(gdf_sl.index.names)
                
                dfs_rc.append(df_rc)

### 6. EXPORTS
(
    pd
    .concat(dfs_rc) # concatenate all room, epoque, furnished, housing type combinations
    .to_csv(data_dir / 'ref_statistics.csv')
)
