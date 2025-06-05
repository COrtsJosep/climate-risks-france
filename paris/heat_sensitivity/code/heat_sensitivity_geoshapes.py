### 1. MODULE IMPORTS
import urllib.request
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

### 3. DATA DOWNLOADS
## Heat sensitivity geoshapes
# zip URL from https://www.data.gouv.fr/fr/datasets/cartographie-des-zones-climatiques-locales-lcz-de-83-aires-urbaines-de-plus-de-50-000-habitants-2022/
heat_sensitivity_zip_url = 'https://www.data.gouv.fr/fr/datasets/r/58cd14e3-97e2-4724-8462-eb85d0f80892'
heat_sensitivity_zip_destination = data_dir / 'heat_sensitivity_geoshapes.zip'
print('Retrieving the Heat Sensitivity ZIP file...')
urllib.request.urlretrieve(heat_sensitivity_zip_url, heat_sensitivity_zip_destination)
