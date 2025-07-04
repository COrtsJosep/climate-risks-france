### 1. PATH DEFINITIONS
import colorcet
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from matplotlib import pyplot as plt

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

### 5. JOIN WITH CONSEILS DE QUARTIER
gdf_cq = gpd.read_file(geoshapes_dir / 'conseils_de_quartier_geoshapes.geojson').set_index('conseil_de_quartier') # cq: conseil de quartier

gdf_zn = ( # zn: zone
    gdf_rc
    .dissolve(by = 'idZone')
    .loc[:, ['geometry']]
)

## 5.1. SMALL EXERCISE TO SEE CORRESPONDANCE QUALITY
zns = [] # zones (ID)
frac_in_zns = [] # fraction of area of the Conseil de Quartier inside the zone
for cq in gdf_cq.index:
    cq_shape = gdf_cq.loc[cq, 'geometry']

    gdf_overlap = gdf_zn.assign(frac_in_zn = lambda df: df.loc[:, 'geometry'].apply(lambda zn_shape: zn_shape.intersection(cq_shape).area / cq_shape.area))
    zn_max_frac_in_zn = gdf_overlap.loc[:, 'frac_in_zn'].idxmax() # zone with maximum overlap
    max_frac_in_zn = gdf_overlap.loc[:, 'frac_in_zn'].max() # fraction of area in the zone with maximum overlap
    
    zns.append(zn_max_frac_in_zn)
    frac_in_zns.append(max_frac_in_zn)

## 5.2. TRANSLATION OF RENT CONTROL BY ZONE TO BY CONSEIL DE QUARTIER
overlaps = [] # each column corresponds to a CdQ, each row corresponds to the % of CdQ in each rent control zone 
for cq in gdf_cq.index:
    cq_shape = gdf_cq.loc[cq, 'geometry']
    overlap = gdf_zn.loc[:, 'geometry'].apply(lambda zn_shape: zn_shape.intersection(cq_shape).area / cq_shape.area).rename(cq)
    overlaps.append(overlap)
    
df_ol = pd.concat(overlaps, axis = 1).sort_values(by = 'idZone')  # ol: overlap. Is a (#CdQ x #Zones) matrix (after being transposed in the next line)
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
                # for each combination of rooms, epoque and furnished, calculate the weighted average of the rent control values, for each CdQ.
                # this is done by matrix multiplication: the rent control values of all zones are weighted by the % they contain of a given CdQ.
                df_tmp = (
                    gdf_rc
                    .query(f'rooms == {rooms[1:]} and epoque == "{epoque[1:]}" and furnished == "{furnished[1:]}" and housingType == "{housing_type[1:]}"')
                    .loc[:, ['idZone'] + float_cols]
                    .drop_duplicates()
                    .sort_values(by = 'idZone')
                    .set_index('idZone')
                )
                df_rc = df_ol @ df_tmp
                df_rc.loc[:, 'rooms'] = rooms[1:]
                df_rc.loc[:, 'epoque'] = epoque[1:]
                df_rc.loc[:, 'furnished'] = furnished[1:]
                df_rc.loc[:, 'housingType'] = housing_type[1:]
                df_rc = df_rc.rename_axis(gdf_cq.index.names)
                
                dfs_rc.append(df_rc)

### 6. EXPORTS
(
    pd
    .DataFrame(data = {'conseil_de_quartier': gdf_cq.index, 'zn': zns, 'frac_in_zn': frac_in_zns})
    .set_index('conseil_de_quartier')
    .sort_values(by = 'frac_in_zn')
    .to_csv(data_dir / 'conseils_de_quartier_zone_overlap.csv')
)

(
    pd
    .concat(dfs_rc) # concatenate all room, epoque, furnished, housing type combinations
    .loc[:, ['rooms', 'epoque', 'furnished', 'housingType'] + float_cols]
    .to_csv(data_dir / 'conseils_de_quartier_rent_control.csv')
)

### 7. MAPS
gdf_map = gdf_cq.reset_index().merge(dfs_rc[0], how = 'inner', on = 'conseil_de_quartier')
gdf_map['ref'] = gdf_map['ref'].astype(float)
gdf_map.explore('ref', cmap = 'cool').save(figures_dir / 'rent_control_map_per_conseil_de_quartier.html')

cmap = plt.get_cmap('cet_glasbey_hv')
fig, ax = plt.subplots()
gdf_zn.plot(
    ax = ax, 
    cmap = cmap, 
    column = np.array(gdf_zn.index), 
    legend = True, 
    legend_kwds = {
        'title': 'Rent Control Zones',     
        'bbox_to_anchor': (1, 1), 
        'loc': 'upper left'},
    categorical = True,
    )
gdf_cq.boundary.plot(ax = ax, color = 'k')

plt.title('Conseil de Quartier - Rent Control Zone Overlap')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.figtext(0.05, -0.1, 'Colours denote Rent Control Zones.\nBlack lines denote Conseils de Quartier.\n', ha = 'left')
plt.savefig(figures_dir / 'cq_rcz_overlap_map.pdf', bbox_inches = 'tight')
