import requests
from bs4 import BeautifulSoup
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
}
r = requests.get("https://welovedevs.com/app/fr/jobs?query=stage", headers=headers)
soup = BeautifulSoup(r.text, "html.parser")
next_data = soup.find("script", id="__NEXT_DATA__")
if next_data:
    data = json.loads(next_data.string)
    print("Found NEXT_DATA in WeLoveDevs! Keys:", list(data.keys()))
    page_props = data.get("props", {}).get("pageProps", {})
    print("pageProps keys:", list(page_props.keys()))
    jobs = page_props.get("jobs", []) or page_props.get("initialJobs", []) or page_props.get("results", [])
    print("Jobs count in NEXT_DATA:", len(jobs))
    if jobs:
        print("First job sample:", jobs[0].get("title", jobs[0]))
else:
    print("No NEXT_DATA found.")
