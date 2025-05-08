### 1. PATH DEFINITIONS
import pandas as pd
import geopandas as gpd
from pathlib import Path

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
    .drop_duplicates('idZone')
    .loc[:, ['idZone', 'geometry']]
    .set_index('idZone')
)

## 5.1. SMALL EXERCISE TO SEE CORRESPONDANCE QUALITY
zns = [] # zones (ID)
frac_in_zns = [] # fraction of area of the Conseil de Quartier inside the zone
for sl in gdf_sl.index:
    sl_shape = gdf_sl.loc[sl, 'geometry']

    gdf_overlap = gdf_zn.assign(frac_in_zn = lambda df: df.loc[:, 'geometry'].apply(lambda zn_shape: zn_shape.intersection(sl_shape).area / sl_shape.area))
    zn_max_frac_in_zn = gdf_overlap.loc[:, 'frac_in_zn'].idxmax() # zone with maximum overlap
    max_frac_in_zn = gdf_overlap.loc[:, 'frac_in_zn'].max() # fraction of area in the zone with maximum overlap
    
    zns.append(zn_max_frac_in_zn)
    frac_in_zns.append(max_frac_in_zn)
    
## 5.2. TRANSLATION OF RENT CONTROL BY ZONE TO BY CODE POSTAL
overlaps = [] # each column corresponds to a SeLoger Quartier, each row corresponds to the % of SeLoger Quartier in each rent control zone 
for sl in gdf_sl.index:
    sl_shape = gdf_sl.loc[sl, 'geometry']
    overlap = gdf_zn.loc[:, 'geometry'].apply(lambda zn_shape: zn_shape.intersection(sl_shape).area / sl_shape.area).rename(sl)
    overlaps.append(overlap)
    
df_ol = pd.concat(overlaps, axis = 1) # ol: overlap. Is a (#SeLoger Quartier x #Zones) matrix (after being transposed in the next line)

df_ol_pr = (df_ol.loc[df_ol.index < 15] / df_ol.loc[df_ol.index < 15].sum()).T # pr: Paris. here I divide by the sum so that all weights add to 1
gdf_rc_pr = gdf_rc.loc[(gdf_rc.loc[:, 'city'] == 'paris') & (gdf_rc.loc[:, 'period'] == '2024-07-01')] # filter for Paris and last rent control values 

dfs_rc_pr = []
for rooms in ROOMS:
    for epoque in EPOQUE:
        for furnished in FURNISHED: 
            # for each combination of rooms, epoque and furnished, calculate the weighted average of the rent control values, for each CdQ.
            # this is done by matrix multiplication: the rent control values of all zones are weighted by the % they contain of a given CdQ. 
            df_rc_pr = df_ol_pr @ gdf_rc_pr.query(f'rooms == {rooms[1:]} and epoque == "{epoque[1:]}" and furnished == "{furnished[1:]}"').set_index('idZone').loc[:, float_cols]
            df_rc_pr.loc[:, 'rooms'] = rooms[1:]
            df_rc_pr.loc[:, 'epoque'] = epoque[1:]
            df_rc_pr.loc[:, 'furnished'] = furnished[1:]
            df_rc_pr = df_rc_pr.rename_axis(gdf_sl.index.names)
            
            dfs_rc_pr.append(df_rc_pr)

### 6. EXPORTS
(
    pd
    .DataFrame(data = {'zn': zns, 'frac_in_zn': frac_in_zns}, index = gdf_sl.index)
    .sort_values(by = 'frac_in_zn')
    .to_csv(data_dir / 'seloger_quartiers_zone_overlap.csv')
)

(
    pd
    .concat(dfs_rc_pr) # concatenate all room, epoque, furnished combinations
    .loc[:, ['rooms', 'epoque', 'furnished'] + float_cols]
    .to_csv(data_dir / 'seloger_quartiers_rent_control.csv')
)

gdf_map = gdf_sl.reset_index().merge(dfs_rc_pr[0], how = 'inner', on = 'seloger_quartier')
gdf_map['ref'] = gdf_map['ref'].astype(float)
gdf_map.explore('ref', cmap = 'cool').save(figures_dir / 'rent_control_map_per_seloger_quartier.html')
