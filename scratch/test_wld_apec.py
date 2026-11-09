import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
}

# Check WeLoveDevs jobs page
r = requests.get("https://welovedevs.com/app/fr/jobs?query=stage", headers=headers)
print("WLD /app/fr/jobs status:", r.status_code)
if r.status_code == 200:
    soup = BeautifulSoup(r.text, "html.parser")
    print("WLD page title:", soup.title.string if soup.title else "")

# Check Emploi Store / Apec / Indeed
r_apec = requests.get("https://www.apec.fr/cms/services/proxy/pole-emploi/offres?motsCles=stage+data", headers=headers)
print("APEC proxy status:", r_apec.status_code)
