### 1. MODULE IMPORTS
import geopandas as gpd
from pathlib import Path

### 2. DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'
geoshapes_dir = code_dir.parent.parent / 'geographic_units' / 'data'

### 3. DATA IMPORTS
fr_shape = gpd.read_file(data_dir / 'flood_risk_geoshapes.geojson').dissolve().loc[0, 'geometry'] # fr: flood risk
au_shape = gpd.read_file(data_dir / 'always_underwater_geoshapes' / 'all_layers.geojson').to_crs('EPSG:4326').dissolve().loc[0, 'geometry'] # au: always underwater
gdf_cq = gpd.read_file(geoshapes_dir / 'conseils_de_quartier_geoshapes.geojson') # cq: conseil de quartier

### 4. CALCULATIONS
gdf_cq.loc[:, 'prop_at_flood_risk'] = gdf_cq.loc[:, 'geometry'].apply(
    lambda cq_shape: cq_shape.difference(au_shape).intersection(fr_shape).area / cq_shape.difference(au_shape).area
)

del gdf_cq['geometry']

gdf_cq.loc[:, 'mean'] = gdf_cq.loc[:, 'prop_at_flood_risk']
gdf_cq.loc[:, 'median'] = gdf_cq.loc[:, 'prop_at_flood_risk'].round()
gdf_cq.loc[:, 'mode'] = gdf_cq.loc[:, 'median'] 
gdf_cq.loc[:, 'std'] = (gdf_cq.loc[:, 'prop_at_flood_risk'] * (1 - gdf_cq.loc[:, 'prop_at_flood_risk'])) ** 0.5

gdf_cq.loc[:, 'mean_delta'] = (gdf_cq.loc[:, 'prop_at_flood_risk'] - gdf_cq.loc[:, 'mode'])
gdf_cq.loc[:, 'median_delta'] = (gdf_cq.loc[:, 'prop_at_flood_risk'] - gdf_cq.loc[:, 'mode']).round()
gdf_cq.loc[:, 'mode_delta'] = gdf_cq.loc[:, 'median_delta']

for c in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
    gdf_cq.loc[:, f'{c}_delta'] = ((1 - gdf_cq.loc[:, 'prop_at_flood_risk']) <= c) - gdf_cq.loc[:, 'mode']

### 5. EXPORT
gdf_cq.to_csv(data_dir / 'flood_risk_statistics.csv', index = False)
