### 1. MODULE IMPORTS
import shapely
import urllib.request
import geopandas as gpd
from pathlib import Path
import contextily as ctx
from matplotlib import pyplot as plt

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. DOWNLOAD
# zip url from https://www.data.gouv.fr/fr/datasets/les-conseils-de-quartier-par-arrondissement-prs/
conseils_zip_url = 'https://opendata.paris.fr/explore/dataset/conseils-quartiers/download?format=shp'
conseils_zip_destination = data_dir / 'conseils_de_quartier_geoshapes.zip'
print('Retrieving the Conseils de Quartier ZIP file...')
urllib.request.urlretrieve(conseils_zip_url, conseils_zip_destination)

### 4. MODIFICATIONS AND EXPORT
gdf = (
    gpd
    .read_file(conseils_zip_destination)
    .set_index('nom_quart')
    .rename_axis('conseil_de_quartier')
    .loc[:, 'geometry']
)
gdf.to_file(conseils_zip_destination.with_suffix('.geojson'))
conseils_zip_destination.unlink()

### 5. FIGURES
centre_paris = shapely.Point((2.348922, 48.853328)) # square in front of Notre Dame
ax = gdf.boundary.plot(figsize = (16, 16), color = 'k')
ctx.add_basemap(
    ax, 
    zoom = 13,
    source = ctx.providers.CartoDB.Positron, 
    crs = gdf.crs.to_string()
)
note = ''
iterator = (
    gpd
    .GeoDataFrame(geometry = gdf)
    .assign(dtc = lambda gdf: gdf.loc[:, 'geometry'].apply(lambda cq: cq.distance(centre_paris)))
    .sort_values(by = 'dtc')
    .iterrows()
)
for i, row in enumerate(iterator):
    cq_name = f"{row[0]}"
    cq = row[1]['geometry']
    
    note += f'{i + 1}: {cq_name}\n'
    
    x, y = cq.representative_point().coords[0]    
    ax.plot(x, y, 'wo', mec = 'k', ms = 11)
    ax.text(x, y, str(i + 1), {'size': 5, 'verticalalignment': 'center', 'horizontalalignment': 'center'})
    
plt.figtext(0.1, -0.9, note, ha = 'left')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('Conseil de Quartier Boundaries')
plt.savefig(figures_dir / 'cq_map.pdf', bbox_inches = 'tight')
