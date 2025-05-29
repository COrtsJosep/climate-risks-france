### 1. MODULE IMPORTS
import pandas as pd
import geopandas as gpd
from pathlib import Path
from pyogrio.errors import DataSourceError

### 2. DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. PARAMETERS
map_xmin = 590660.3999999985
map_ymin = 6782748.9307
map_xmax = 718969.9790000021
map_ymax = 6896220.694400001
n_divide = 2
layers = [# see https://geoweb.iau-idf.fr/server/rest/services/RISQUES/Cartoviz_zip/FeatureServer
    1, 
    7, 
    13, 
    18
]

### 4. DATA FETCHING
# Problem: If you call the API with an area that has too many records, you get a DataSourceError.
# Solution: Call API for the whole area, if it fails, split area into 4 squares, and evaluate each
# of the 4. If it fails, split again, etc, etc.
for layer in layers:
    gdfs = []
    tiles = [(map_xmin, map_ymin, map_xmax, map_ymax)]
    covered_area = 0
    total_area = (map_xmax - map_xmin) * (map_ymax - map_ymin)
    while tiles: # while there are tiles to evaluate
        xmin, ymin, xmax, ymax = tiles.pop() # take the last one to be added
        
        url = f'https://geoweb.iau-idf.fr/server/rest/services/RISQUES/Cartoviz_zip/FeatureServer/{layer}/query?f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry={{"xmin":{xmin},"ymin":{ymin},"xmax":{xmax},"ymax":{ymax},"spatialReference":{{"wkid":102110,"latestWkid":2154}}}}&geometryType=esriGeometryEnvelope&inSR=102110&outFields=*&outSR=102110&resultType=tile'
        
        try: 
            gdf = gpd.read_file(url)
            if not gdf.empty:
                gdf = gdf.query('niv == 99') # only areas that are always under water
                
            gdfs.append(gdf)
            covered_area += (xmax - xmin) * (ymax - ymin)
            print(f'Percentage of layer {layer:02d} covered area so far: {100 * covered_area / total_area:.2f}%')
        except DataSourceError: # if it failed because too many records
            xstep = (xmax - xmin) / n_divide
            ystep = (ymax - ymin) / n_divide
            for xi in range(n_divide):
                for yi in range(n_divide):
                    tiles.append( # split into 4 and add to the queue
                        (
                            xmin + xi * xstep, 
                            ymin + yi * ystep,
                            xmin + (xi + 1) * xstep,
                            ymin + (yi + 1) * ystep
                         )
                    )
        except Exception as e:
            print('Unexpected exception:', e)
            
    gdf = pd.concat(gdfs).dissolve(by = 'objectid') # concatenate all of them
    del gdfs

    gdf.explore().save(figures_dir / 'always_underwater_geoshapes' / f'layer_{layer:02d}.html')
    gdf.to_file(data_dir / 'always_underwater_geoshapes' / f'layer_{layer:02d}.geojson')
    del gdf
    
gdf = (
    pd.concat(
        [gpd.read_file(data_dir / 'always_underwater_geoshapes' / f'layer_{layer:02d}.geojson') for layer in layers]
    )
    .dissolve(by = 'objectid')
)

### 5. EXPORT
gdf.explore().save(figures_dir / 'always_underwater_geoshapes' / 'all_layers.html')
gdf.to_file(data_dir / 'always_underwater_geoshapes' / 'all_layers.geojson')
