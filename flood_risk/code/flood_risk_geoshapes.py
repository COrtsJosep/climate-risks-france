### 1. MODULE IMPORTS
import shapely
import svgpathtools
import urllib.request
import geopandas as gpd
from typing import Tuple
from pathlib import Path

### 2. DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

## The downloaded svg & URL can be generated here
# https://geoweb.iau-idf.fr/server/rest/services/RISQUES/cartoviz_zini_simplifiees/MapServer -> export map
# https://geoweb.iau-idf.fr/server/rest/services/RISQUES/cartoviz_zini_simplifiees/MapServer/export?bbox=589967.8495417576%2C6782748.9307%2C719662.529458243%2C6896220.694400001&bboxSR=&layers=&layerDefs=&size=&imageSR=&historicMoment=&format=svg&transparent=true&dpi=&time=&timeRelation=esriTimeRelationOverlaps&layerTimeOptions=&dynamicLayers=&gdbVersion=&mapScale=&rotation=&datumTransformations=&layerParameterValues=&mapRangeValues=&layerRangeValues=&clipping=&spatialFilter=&f=html

### 3. DOWNLOAD, IMPORT AND TRANSLATION
svg_url = 'https://geoweb.iau-idf.fr/server/rest/directories/arcgisoutput/RISQUES/cartoviz_zini_simplifiees_MapServer/_ags_map14e5ad0ccf8543ae90ad27806daaeecc.svg'
svg_destination = data_dir / 'flood_risk_area.svg'
urllib.request.urlretrieve(svg_url, svg_destination)
paths, attributes = svgpathtools.svg2paths(svg_destination)

svg_xs = [line.start.real for segment in paths for line in segment] + [line.end.real for segment in paths for line in segment]
svg_ys = [line.start.imag for segment in paths for line in segment] + [line.end.imag for segment in paths for line in segment]
svg_xmax, svg_xmin = max(svg_xs), min(svg_xs)
svg_ymax, svg_ymin = max(svg_ys), min(svg_ys)

map_xmin = 590660.3999999985
map_ymin = 6782748.9307
map_xmax = 718969.9790000021
map_ymax = 6896220.694400001

width_scale_factor = (map_xmax - map_xmin) / (svg_xmax - svg_xmin)
height_scale_factor = (map_ymax - map_ymin) / (svg_ymax - svg_ymin)

### 4. FUNCTION DEFINITIONS
def almost_equal(t1: Tuple[float], t2: Tuple[float]) -> bool:
    return abs(t1[0] - t2[0]) + abs(t1[1] - t2[1]) < 1e-8
    
def translate(point: complex) -> Tuple[float]:
    x = map_xmin + (point.real - svg_xmin) * width_scale_factor
    y = map_ymin + (point.imag - svg_ymin) * height_scale_factor
    
    return (x, y)

def polygonize(path: svgpathtools.Path) -> shapely.geometry.Polygon:
    points = [translate(line.start) for line in path]
    if not almost_equal(points[0], points[-1]):
        end_point = translate(path[-1].end)
        points.append(end_point)
        
    return shapely.geometry.Polygon(points)        

def path_to_shapely(path: svgpathtools.Path) -> shapely.geometry.MultiPolygon:
    '''Convert an svgpathtools svgpathtools.Path to a shapely geometry.'''
    
    polygons = [polygonize(subpath) for subpath in path.continuous_subpaths()]               
    return shapely.union_all(geometries = polygons)

### 5. FILE CREATION
fill_to_label = {
    '#B2526B': 'Impact fort',
    '#D49FAD': 'Impact modéré',
    '#B2B2B2': 'Impact non mesuré'
}

filtered_paths = [path for path, attribute in zip(paths, attributes) if fill_to_label[attribute['fill']] == 'Impact fort']
filtered_attributes = [attribute for attribute in attributes if fill_to_label[attribute['fill']] == 'Impact fort']
geometries = [shapely.union_all([path_to_shapely(path) for path in filtered_paths])]

gdf = (
    gpd
    .GeoDataFrame(data = {'index': list(range(len(geometries))), 'geometry': geometries}, crs = 'EPSG:2154')
    .to_crs('EPSG:4326')
)

### 6. EXPORT
gdf.to_file(data_dir / 'flood_risk_geoshapes.geojson')
gdf.explore().save(figures_dir / 'flood_risk_areas.html')







