import sys
sys.path.insert(0, ".")
import requests
from src.collectors.france_travail import FranceTravailCollector

ft = FranceTravailCollector()
token = ft._get_access_token()
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

tests = [
    {"natureContrat": "FS", "departement": "75", "motsCles": "informatique"},
    {"natureContrat": "FS", "departement": "75", "motsCles": "data"},
    {"natureContrat": "FS", "departement": "17"},
    {"natureContrat": "FS", "departement": "79"},
    {"natureContrat": "FS", "departement": "85"},
    {"natureContrat": "FS", "motsCles": "python"},
    {"natureContrat": "FS", "motsCles": "data"},
    {"natureContrat": "FS", "codeROME": "M1805"},
]

for t in tests:
    r = requests.get(ft.search_url, headers=headers, params=t, timeout=10)
    print(t, "->", r.status_code, "Results:", len(r.json().get("resultats", [])) if r.status_code in (200, 206) else 0)
    if r.status_code in (200, 206) and r.json().get("resultats"):
        first = r.json()["resultats"][0]
        print("  Sample:", first.get("intitule"), "|", first.get("entreprise", {}).get("nom"), "|", first.get("lieuTravail", {}).get("libelle"))
