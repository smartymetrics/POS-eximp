import os
from dotenv import load_dotenv

load_dotenv()
print("Env keys available:")
for k in os.environ.keys():
    if any(x in k.lower() for x in ["db", "postgres", "sql", "conn", "url", "key"]):
        print(f" - {k}")
