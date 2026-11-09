import sys
sys.path.insert(0, ".")
import requests
from src.collectors.france_travail import FranceTravailCollector

ft = FranceTravailCollector()
token = ft._get_access_token()
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

queries = [
    {"motsCles": "stage data", "departement": "75"},
    {"motsCles": "stage python", "departement": "75"},
    {"motsCles": "stage developpeur", "departement": "17"},
    {"motsCles": "stage developpeur", "departement": "79"},
    {"motsCles": "stage developpeur", "departement": "85"},
    {"natureContrat": "FS", "motsCles": "informatique", "departement": "17"},
    {"natureContrat": "FS", "motsCles": "informatique", "departement": "79"},
    {"natureContrat": "FS", "motsCles": "informatique", "departement": "85"},
    {"natureContrat": "FS", "motsCles": "informatique", "departement": "75"},
    {"natureContrat": "FS", "motsCles": "python"},
    {"natureContrat": "FS", "motsCles": "data"},
]

for q in queries:
    r = requests.get(ft.search_url, headers=headers, params=q, timeout=10)
    cnt = len(r.json().get("resultats", [])) if r.status_code in (200, 206) else 0
    print(q, "-> Status:", r.status_code, "Count:", cnt)
