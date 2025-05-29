### 1. IMPORTS
import pandas as pd
import geopandas as gpd
from pathlib import Path

### 2. PATH & OTHER DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'
geoshapes_dir = code_dir.parent.parent / 'geographic_units' / 'data'

float_cols = [
    'LNM - Loyer de référence',
    'LNM - Loyer de référence majoré',
    'LNM - Loyer de référence minoré',
    'LM - Majoration unitaire du loyer de référence',
    'LM - Loyer de référence',
    'LM - Loyer de référence majoré',
    'LM - Loyer de référence minoré',
]

### 3. LOAD
gdf_sg = ( # sg: secteur géographique
    gpd
    .read_file(data_dir / 'rent_control_geoshapes.geojson')
    .set_index('Secteur géographique')
) 
gdf_sg_unique = (
    gdf_sg
    .drop_duplicates('geometry')
    .loc[:, 'geometry']
)
gdf_sl = ( # sl: seloger quartier
    gpd
    .read_file(geoshapes_dir / 'seloger_quartiers_geoshapes.geojson')
    .set_index(['seloger_quartier', 'code_postal'])
)

### 4. TRANSLATION OF RENT CONTROL BY ZONE TO BY SELOGER QUARTIER
overlaps = [] # each column corresponds to a SeLoger Quartier, each row corresponds to the % of SeLoger Quartier in each rent control zone 
for sl in gdf_sl.index:
    sl_shape = gdf_sl.loc[sl, 'geometry']
    overlap = (
        gdf_sg_unique
        .apply(lambda zn_shape: zn_shape.intersection(sl_shape).area / sl_shape.area)
        .rename(sl)
    )
    overlaps.append(overlap)
    
df_ol = pd.concat(overlaps, axis = 1) # ol: overlap
df_ol = (df_ol / df_ol.sum()).T # is a (#SeLoger Quartier x #Zones) matrix

dfs_rc = []
for np in gdf_sg.loc[:, 'Nombre de pièces'].unique():
    for ec in gdf_sg.loc[:, 'Époque de construction'].unique():
        mask = (gdf_sg.loc[:, 'Nombre de pièces'] == np) & (gdf_sg.loc[:, 'Époque de construction'] == ec) 
        df_rc = df_ol @ gdf_sg.loc[mask, :].loc[:, float_cols]
        df_rc.loc[:, 'Nombre de pièces'] = np
        df_rc.loc[:, 'Époque de construction'] = ec
        df_rc = df_rc.rename_axis(gdf_sl.index.names)
        
        dfs_rc.append(df_rc)
        
### 5. CONCATENATE AND EXPORT
(
    pd
    .concat(dfs_rc) # concatenate all rooms, epoques combinations
    .loc[:, ['Nombre de pièces', 'Époque de construction'] + float_cols]
    .to_csv(data_dir / 'seloger_quartiers_rent_control.csv')
)

(
    gdf_sl
    .join(dfs_rc[0], how = 'inner')
    .explore(float_cols[0])
    .save(figures_dir / 'seloger_quartiers_rent_control.html')
)
