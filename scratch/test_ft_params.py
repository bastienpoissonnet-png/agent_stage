import sys
sys.path.insert(0, ".")
import requests
from src.collectors.france_travail import FranceTravailCollector

ft = FranceTravailCollector()
token = ft._get_access_token()
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

# Test different parameters
test_cases = [
    {"motsCles": "stage", "departement": "75"},
    {"motsCles": "stage data", "departement": "75"},
    {"motsCles": "stage informatique", "departement": "17"},
    {"natureContrat": "E2", "motsCles": "informatique"},
    {"natureContrat": "FS", "motsCles": "informatique"},
    {"typeContrat": "AUT", "motsCles": "stage"},
    {"codeROME": "M1805", "motsCles": "stage", "departement": "75"},
    {"codeROME": "M1805", "departement": "75"},
]

for tc in test_cases:
    r = requests.get(ft.search_url, headers=headers, params=tc, timeout=10)
    print(tc, "-> Status:", r.status_code, "Count:", len(r.json().get("resultats", [])) if r.status_code in (200, 206) else r.text[:100])
