import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Check WTTJ search html or json
url = "https://www.welcometothejungle.com/fr/jobs?query=stage%20data&refinementList%5Bcontract_type%5D%5B%5D=internship"
r = requests.get(url, headers=headers)
print("WTTJ status:", r.status_code)
# Search for scripts or JSON-LD
soup = BeautifulSoup(r.text, "html.parser")
scripts = soup.find_all("script")
print("Found scripts:", len(scripts))
for s in scripts:
    content = s.string or ""
    if "algolia" in content.lower():
        print("Found script mentioning algolia! Length:", len(content))
        # Search for key and app
        m_app = re.findall(r'appId["\']?\s*:\s*["\']([a-zA-Z0-9]+)["\']', content)
        m_key = re.findall(r'apiKey["\']?\s*:\s*["\']([a-zA-Z0-9]+)["\']', content)
        print("m_app:", m_app)
        print("m_key:", m_key)
