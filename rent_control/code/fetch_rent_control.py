### 1. MODULE IMPORTS
import geopandas as gpd
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

### 3. CONSTANTS
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

### 4. DATA DOWNLOADS
## URL can be found by scanning the API requests (inspect page -> network) launched when using http://www.referenceloyer.drihl.ile-de-france.developpement-durable.gouv.fr/paris/
for city in CITY:
    for period in PERIOD[city]:
        for housing_type in HOUSING_TYPE[city]:
            for rooms in ROOMS:
                for epoque in EPOQUE:
                    for furnished in FURNISHED:   
                        url = f'http://www.referenceloyer.drihl.ile-de-france.developpement-durable.gouv.fr/{city}/kml/{period}/drihl_medianes{housing_type}{rooms}{epoque}{furnished}.kml'
                        destination = data_dir / 'rent_control_geoshapes' / city / period / f'{housing_type}{rooms}{epoque}{furnished}.geojson'[1:] # ignore leading underscore
                        
                        print('Fetching', url)
                        
                        destination.parent.mkdir(parents = True, exist_ok = True) # create directory
                        gpd.read_file(url).to_file(destination, driver = 'GeoJSON')
