import requests

# Test 1jeune1solution open API
try:
    r = requests.get("https://api.1jeune1solution.gouv.fr/v1/stages?motCle=data", timeout=5)
    print("1jeune1solution status:", r.status_code, "len:", len(r.text))
except Exception as e:
    print("1jeune1solution err:", e)

# Test JobTeaser RSS or open endpoints
try:
    r_jt = requests.get("https://www.jobteaser.com/fr/job-offers.rss?contract=internship", timeout=5)
    print("Jobteaser RSS status:", r_jt.status_code, "len:", len(r_jt.text))
except Exception as e:
    print("Jobteaser err:", e)
