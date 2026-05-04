import pandas as pd

df = pd.read_excel('eximps-cloves quotation.xlsx', sheet_name=0)
print("Total rows:", len(df))
print("Total columns:", len(df.columns))
print("\nColumn names:", df.columns.tolist())
print("\nFirst 80 rows:")
print(df.head(80).to_string())
