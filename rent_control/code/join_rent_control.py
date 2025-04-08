import tabula
import pandas as pd
import geopandas as gpd
from pathlib import Path

### 2. PATH DEFINITIONS
code_dir = Path(__file__).parent
data_dir = code_dir.parent / 'data'
figures_dir = code_dir.parent / 'figures'

### 3. PDF TABLE PARSING 
dfs_org = tabula.read_pdf(data_dir / 'rent_control_paris.pdf', pages = 'all', lattice = False, stream = True) # read tables in the pdf (need to be heavily cleaned)
colnames = [
    'Secteur géographique', 
    'Nombre de pièces', 
    'Époque de construction',
    'Loyer de référence minoré - LV', # LV: Locations vides
    'Loyer de référence - LV', 
    'Loyer de référence majoré - LV', 
    'Majoration unitaire du loyer de référence - LM', # LM: Locations meublées
    'Loyer de référenceminoré - LM', 
    'Loyer de référence - LM', 
    'Loyer de référence majoré - LM'
]

dfs = []
for i, df_org in enumerate(dfs_org):
    df = (
        df_org
        .copy()
        .dropna(subset = 'Unnamed: 2') # drop empty rows (falsely created)
    )

    df = (
        pd.concat(
            [
                df.iloc[:, :7],
                pd.concat(
                    [
                        df.iloc[:, 7].str.split(' ', n = 1, expand = True), # split two columns falsely joined
                        df.iloc[:, 8]
                    ],
                    axis = 1
                )
            ],
            axis = 1
        )
        .loc[7:]
        .reset_index(drop = True)
    )

    df.columns = colnames # set the correct colnames
    n = df.shape[0]
    df.loc[:, 'Secteur géographique'] = [str(i + 1)] * n # create column with SG
    df.loc[:, 'Nombre de pièces'] = ( # create column with NdP
        ['1'] * int(n / 4) 
        + ['2'] * int(n / 4) 
        +  ['3'] * int(n / 4) 
        + ['4 et plus'] * int(n / 4)
    )
    df = df.map(lambda x: x.replace(',', '.')) # change ,s by .s in the decimal numbers
    
    df = df.pivot(index = 'Secteur géographique', columns = ['Nombre de pièces', 'Époque de construction']) # turn the whole table into a single line
    df.columns = df.columns.map('|'.join) # flatten the column multiindex

    dfs.append(df)
    
### 4. DATAFRAME DEFINITIONS
df_rc = pd.concat(dfs, axis = 0) # rc: rent control
df_rc = df_rc.astype(float)
df_rc.index = df_rc.index.astype(int)

df_cw = ( # cw: crosswalk
    pd
    .read_csv(data_dir / 'quartier_secteur_crosswalk.csv', sep = '|')
    .set_index('Secteur géographique')
)
df_rc.index = df_rc.index.astype(int)

gdf_qt = ( # qt: quartier
    gpd
    .read_file('https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/quartier_paris/exports/geojson?lang=fr&timezone=Europe%2FBerlin')
    .loc[:, ['c_qu', 'geometry']]
    .rename(columns = {'c_qu': 'Quartier'})
    .set_index('Quartier')
)
gdf_qt.index = gdf_qt.index.astype(int)

### 5. JOINING
gdf = (
    gdf_qt
    .join(
        df_cw
        .join(df_rc)
        .reset_index(drop = False)
        .set_index('Quartier')
    )
    .reset_index(drop = False)
)

### 6. FIGURES
gdf.explore('Loyer de référence minoré - LV|1|avant 1946').save(figures_dir / 'loyer_de_ref_map.html')
