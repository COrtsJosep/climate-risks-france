import zipfile
import urllib.request
from pathlib import Path

code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

# zip URL from https://data-iau-idf.opendata.arcgis.com/datasets/iau-idf::ilots-de-chaleur-urbains-icu-classification-des-imu-en-zone-climatique-locale-lcz-al%C3%A9as-et-vuln%C3%A9rabilit%C3%A9s-%C3%A0-la-chaleur-de-jour-et-de-nuit-en-%C3%AEle-de-france/about
heatstress_zip_url = 'https://hub.arcgis.com/api/v3/datasets/2846134ea6b94177af1366d11e517187_18/downloads/data?format=shp&spatialRefId=2154&where=1%3D1'
heatstress_zip_destination = data_dir / 'heatstress_geoshapes.zip'

print('Retrieving the Heat Stress ZIP file...')
urllib.request.urlretrieve(heatstress_zip_url, heatstress_zip_destination)

# zip url from https://www.data.gouv.fr/fr/datasets/les-conseils-de-quartier-par-arrondissement-prs/
conseils_zip_url = 'https://opendata.paris.fr/explore/dataset/conseils-quartiers/download?format=shp'
conseils_zip_destination = data_dir / 'conseils_de_quartier_geoshapes.zip'
print('Retrieving the Conseils de Quartier ZIP file...')
urllib.request.urlretrieve(conseils_zip_url, conseils_zip_destination)

# zip url from https://www.insee.fr/fr/information/7708995#
iris_zip_url = 'https://www.insee.fr/fr/statistiques/fichier/7708995/reference_IRIS_geo2024.zip'
iris_zip_destination = data_dir / 'reference_IRIS_geo2024.zip'
print('Retrieving the IRIS - Commune Crosswalk ZIP file...')
urllib.request.urlretrieve(iris_zip_url, iris_zip_destination)

print('Extracting IRIS - Commune Crosswalk xlsx file...')
with zipfile.ZipFile(iris_zip_destination, 'r') as zip_object:
    zip_object.extractall(path = data_dir)
    
iris_zip_destination.with_suffix('.xlsx').rename(data_dir / 'iris_commune_crosswalk.xlsx')

print('Deleting the IRIS - Commune Crosswalk ZIP file...')
iris_zip_destination.unlink()

# csv url from https://datanova.laposte.fr/datasets/laposte-hexasmal
code_postal_csv_url = 'https://datanova.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/metadata-attachments/base-officielle-codes-postaux.csv'
code_postal_csv_destination = data_dir / 'commune_code_postal_crosswalk.csv'
print('Retrieving the Commune - Code Postal csv file...')
urllib.request.urlretrieve(code_postal_csv_url, code_postal_csv_destination)

# 7z url from https://geoservices.ign.fr/irisge
iris_7z_url = 'https://data.geopf.fr/telechargement/download/IRIS-GE/IRIS-GE_3-0__SHP_LAMB93_FXX_2024-01-01/IRIS-GE_3-0__SHP_LAMB93_FXX_2024-01-01.7z'
iris_7z_destination = data_dir / 'IRIS-GE_3-0__SHP_LAMB93_FXX_2024-01-012.7z'
print('Retrieving the IRIS 7z file...')
try:
    urllib.request.urlretrieve(iris_7z_url, iris_7z_destination) 
except:
    print('Failed with 403 error. Why would géoservices do that? Anyways, I will download the files by hand and save them in iris_geoshapes.zip ...')

'''
# gpkg URL from https://r.iresmi.net/posts/2024/codes_postaux/
postalcode_gpkg_url = 'https://r.iresmi.net/posts/2024/codes_postaux/codes_postaux_fr_2024.gpkg'
postalcode_gpkg_destination = data_dir / 'postalcode_geoshapes.gpkg'
print('Retrieving the postal code GPKG file...')
urllib.request.urlretrieve(postalcode_gpkg_url, postalcode_gpkg_destination)

# zip URL from http://download.geonames.org/export/zip/
print('Retrieving postal code ZIP file...')
postalcode_zip_url = 'http://download.geonames.org/export/zip/FR.zip'
postalcode_zip_destination = data_dir / 'postalcode_records.zip'
urllib.request.urlretrieve(postalcode_zip_url, postalcode_zip_destination)

print('Extracting postal code csv file...')
with zipfile.ZipFile(postalcode_zip_destination, 'r') as zip_object:
    zip_object.extractall(path = data_dir)
    
(data_dir / 'FR.txt').rename(data_dir / 'postalcode_records.txt')
(data_dir / 'readme.txt').rename(data_dir / 'postalcode_records_readme.txt')

print('Deleting postal code ZIP file...')
postalcode_zip_destination.unlink()

print('All done!')

#pd.read_csv(data_dir / 'FR' / 'zipcodes.fr.csv')
#zip_destination = data_dir / 'codes_postaux_fr_2024.gpkg'
#df_idf = df.query('state == "Île-de-France"')
#gdf_idf = gdf.loc[gdf.loc[:, 'code_postal'].isin(df_idf.loc[:, 'zipcode'])]
'''
