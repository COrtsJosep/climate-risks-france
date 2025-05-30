### 1. MODULE IMPORTS
import tabula
import requests
import pandas as pd
import urllib.request
import geopandas as gpd
from pathlib import Path
from zipfile import ZipFile

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

### 3. GEOSHAPES - DOWNLOAD AND EXTRACT
zip_url = 'https://www.observatoires-des-loyers.org/datagouv/2023/Base_OP_2023_L3800.zip'
zip_destination = data_dir / 'rent_zones.zip'
urllib.request.urlretrieve(zip_url, zip_destination)

with ZipFile(zip_destination) as zipfile:
    zipfile.extract('L3800_zone_elem_2023.kml', path = data_dir)
    zipfile.extract('table_zones_2023_L3800_1.xls', path = data_dir)
zipfile.close()
   
### 4. GEOSHAPES - LOAD DATA
gdf_zn = gpd.read_file(data_dir / 'L3800_zone_elem_2023.kml')
df_zn = pd.read_excel(data_dir / 'table_zones_2023_L3800_1.xls', header = 2)

for path in data_dir.iterdir():
    path.unlink() # delete everything created so far

### 5. GEOSHAPES - MERGE AND EXPORT
zone_dict = {
    'L3800.1.01': 'Zone 1',
    'L3800.1.02': 'Zone 2',
    'L3800.1.03': 'Zone 3',
    'L3800.1.04': 'Zone A',
    'L3800.1.05': 'Zone B',
    'L3800.1.06': 'Zone C'
}

gdf_ds = ( # ds: dissolved
    gdf_zn
    .merge(df_zn, left_on = 'VAR5', right_on = 'var5')
    .assign(rent_control_zone = lambda df: df.loc[:, 'var4'].map(zone_dict))
    .rename(columns = {'var5': 'rent_control_category', 'rent_control_zone': 'zone'})
    .loc[:, ['zone', 'geometry']]
    .dissolve('zone')
    #.to_file(data_dir / 'rent_control_zones_geoshapes.geojson')
)

### 6. RENT CONTROL - DOWNLOAD AND LOAD
pdf_url = 'https://www.isere.gouv.fr/contenu/telechargement/76673/598917/file/3_Tableau_loyers%20de%20r%C3%A9f%C3%A9rence_ANIL.pdf'
pdf_destination = data_dir / 'rent_control_table.pdf'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
response = requests.get(pdf_url, headers = headers)
with open(pdf_destination, 'wb') as f:
        f.write(response.content)

df1_rc, df2_rc = tabula.read_pdf(pdf_destination, stream = True, pages = 'all')
pdf_destination.unlink() # delete it after it's been read

### 7. RENT CONTROL - CORRECTIONS
colnames = [
    'zone',
    'rooms',
    'epoque',
    'refLN',
    'refmajLN',
    'refminLN',
    'maj',
    'refLM',
    'refmajLM',
    'refminLM'
]
float_cols = colnames[3:]

epoque_map = {
    'avant 1946': 'inf1946', 
    '1946-1970': '1946-1970', 
    '1971-1990': '1971-1990', 
    'après 1990': 'sup1990'
}
furnished_map = {'LN': 'non-meuble', 'LM': 'meuble'}

df_rc = pd.concat([df1_rc.loc[7:], df2_rc.loc[7:]], axis = 0)
df_rc = pd.concat([
    pd.Series(['Zone 1'] * 16 + ['Zone 2'] * 16 + ['Zone A'] * 16), 
    pd.Series(sorted(list(range(1, 5)) * 4) * 3),
    df_rc.iloc[:, 2].dropna().reset_index(drop = True),
    df_rc.iloc[:, 3].str.split(' ', n = 2, expand = True).dropna().reset_index(drop = True),
    df_rc.iloc[:, 4].dropna().reset_index(drop = True),
    df_rc.iloc[:, 5].str.split(' ', n = 1, expand = True).dropna().reset_index(drop = True),
    df_rc.iloc[:, 6].dropna().reset_index(drop = True)
], axis = 1)
    
df_rc.columns = colnames
df_rc.loc[:, float_cols] = df_rc.loc[:, float_cols].map(lambda x: x.replace(',', '.')).astype(float)
df_rc = (
    pd
    .wide_to_long(
        df_rc, 
        ['ref', 'refmaj', 'refmin'], 
        i = ['zone', 'rooms', 'epoque'], 
        j = 'furnished', 
        suffix = 'L\D'
    )
    .reset_index()
    .replace({'epoque': epoque_map, 'furnished': furnished_map})
)

### 8. MERGE EVERYTHING AND EXPORT
(
    gpd
    .GeoDataFrame(
        data = (
            df_rc
            .set_index('zone')
            .join(gdf_ds)
            .reset_index(drop = False)
            .to_dict(orient = 'list')), # somehow index is not included???
        crs = gdf_ds.crs
    )
    .set_index('zone')
    .to_file(data_dir / 'rent_control_geoshapes.geojson')
)
