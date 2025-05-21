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
gdf_sl = gpd.read_file(geoshapes_dir / 'seloger_quartiers_geoshapes.geojson') # sl: seloger

### 4. CALCULATIONS
gdf_sl.loc[:, 'prop_at_flood_risk'] = gdf_sl.loc[:, 'geometry'].apply(
    lambda sl_shape: sl_shape.difference(au_shape).intersection(fr_shape).area / sl_shape.difference(au_shape).area
)

### 5. EXPORT
gdf_sl.explore('prop_at_flood_risk').save(figures_dir / 'seloger_quartiers_flood_risk.html')
gdf_sl.loc[:, ['seloger_quartier', 'code_postal', 'prop_at_flood_risk']].to_csv(data_dir / 'seloger_quartiers_flood_risk.csv', index = False)
