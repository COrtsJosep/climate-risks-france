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
gdf_cp = gpd.read_file(geoshapes_dir / 'codes_postaux_geoshapes.geojson').to_crs('EPSG:4326') # cp: code postal

### 4. CALCULATIONS
gdf_cp.loc[:, 'prop_at_flood_risk'] = gdf_cp.loc[:, 'geometry'].apply(
    lambda cp_shape: cp_shape.difference(au_shape).intersection(fr_shape).area / cp_shape.difference(au_shape).area
)

### 5. EXPORT
gdf_cp.explore('prop_at_flood_risk').save(figures_dir / 'codes_postaux_flood_risk.html')
gdf_cp.loc[:, ['code_postal', 'prop_at_flood_risk']].to_csv(data_dir / 'codes_postaux_flood_risk.csv', index = False)
