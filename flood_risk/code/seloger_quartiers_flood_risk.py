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
gdf_sl = gpd.read_file(geoshapes_dir / 'seloger_quartiers_geoshapes.geojson')

### 4. CALCULATIONS
gdf_sl.loc[:, 'prop_at_flood_risk'] = gdf_sl.loc[:, 'geometry'].apply(lambda sl_shape: sl_shape.intersection(fr_shape).area / sl_shape.area)
gdf_sl.loc[gdf_sl.loc[:, 'seloger_quartier'] == 'Seine et Berges', 'prop_at_flood_risk'] = 1.0 # these areas are ONLY river

### 5. EXPORT
gdf_sl.loc[:, ['seloger_quartier', 'code_postal', 'prop_at_flood_risk']].to_csv(data_dir / 'seloger_quartiers_flood_risk.csv', index = False)
