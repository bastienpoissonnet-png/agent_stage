import requests

r = requests.get("https://remotive.com/api/remote-jobs?category=data", headers={"User-Agent": "StageAgent/1.0"})
if r.status_code == 200:
    jobs = r.json().get("jobs", [])
    print("Remotive jobs total:", len(jobs))
    for j in jobs[:3]:
        print("Remotive:", j.get("title"), "|", j.get("company_name"), "|", j.get("job_type"), "| tags:", j.get("tags"))

r_ok = requests.get("https://remoteok.com/api", headers={"User-Agent": "StageAgent/1.0"})
if r_ok.status_code == 200:
    jobs_ok = r_ok.json()
    # RemoteOK first element is legal disclaimer dict
    print("RemoteOK jobs total:", len(jobs_ok))
    for j in jobs_ok[1:4]:
        print("RemoteOK:", j.get("position"), "|", j.get("company"), "| tags:", j.get("tags"))
