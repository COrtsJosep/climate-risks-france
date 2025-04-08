### 1. MODULE IMPORTS
import urllib.request
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'

### 3. DATA DOWNLOADS
## Rent control PDFs
# PDF from https://www.drihl.ile-de-france.developpement-durable.gouv.fr/arretes-fixant-les-loyers-de-reference-les-loyers-a291.html
paris_pdf_url = 'https://www.drihl.ile-de-france.developpement-durable.gouv.fr/IMG/pdf/arrete_idf-2023-05-30-00005.pdf'
paris_pdf_destination = data_dir / 'rent_control_paris.pdf'
print('Retrieving the Paris rent control PDF file...')
urllib.request.urlretrieve(paris_pdf_url, paris_pdf_destination)

## Crosswalks
# quartier_secteur_crosswalk.csv comes from the rent_control_paris.pdf file!
