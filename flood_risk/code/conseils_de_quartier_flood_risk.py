### 1. MODULE IMPORTS
import geopandas as gpd
from pathlib import Path

### 2. DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'
geoshapes_dir = code_dir.parent.parent / 'geographic_units' / 'data'

### 3. DATA IMPORTS
fr_shape = gpd.read_file(data_dir / 'flood_risk_geoshapes.geojson').dissolve().loc[0, 'geometry']
gdf_cq = gpd.read_file(geoshapes_dir / 'conseils_de_quartier_geoshapes.geojson')

### 4. CALCULATIONS
gdf_cq.loc[:, 'prop_at_flood_risk'] = gdf_cq.loc[:, 'geometry'].apply(lambda cq_shape: cq_shape.intersection(fr_shape).area / cq_shape.area)

### 5. EXPORT
gdf_cq.loc[:, ['conseil_de_quartier', 'prop_at_flood_risk']].to_csv(data_dir / 'conseils_de_quartier_flood_risk.csv', index = False)
