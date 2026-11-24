# 🎯 Stage Agent — Assistant de Veille & Candidatures (BUT 3 Data & IA)

Outil modulaire en Python conçu pour la recherche de stage de fin d'études en **BUT 3 Informatique (spécialité DATA/IA)**. Il combine la **veille automatique d'offres en présentiel / hybride local**, la **génération de lettres de motivation PDF** et l'orchestration de **campagnes de candidatures spontanées**.

---

## 🗺️ Périmètre & Critères de Recherche

* **Candidat :** Bastien Poissonnet (IUT de La Rochelle — Site de Niort / Niortech).
* **Période de stage :** Du 22 mars au 25 juin 2027 (14 semaines).
* **Zones cibles :**
  * **La Rochelle (17)**
  * **Niort (79)**
  * **La Roche-sur-Yon / Vendée (85)**
  * **Paris / Île-de-France (75, 92, 93, 94)**
* **Format de travail :** **Présentiel ou Hybride uniquement** (le 100 % full remote est exclu).
* **Contrat :** **Stage conventionné uniquement** (les alternances, apprentissages et stages de découverte/3ème sont automatiquement rejetés).

---

## 🏗️ Architecture du Projet

```text
stage-agent/
│
├── config/
│   ├── settings.py                 # Configuration centrale (.env + profile.json)
│   └── profile.json                # Profil complet de Bastien (compétences, critères, dates)
│
├── data/
│   ├── lettre_type.txt             # Modèle type de lettre de motivation
│   └── target_companies.csv        # Base de sourcing pour la campagne spontanée (17, 79, 85, 75)
│
├── src/
│   ├── collectors/                 # Collecteurs d'offres sans clé API ni blocage
│   │   ├── base.py                 # Interface abstraite BaseJobCollector
│   │   ├── hellowork.py            # Collecteur HelloWork (HTML + JSON-LD JobPosting)
│   │   ├── un_jeune_une_solution.py # Collecteur officiel 1jeune1solution.gouv.fr (__NEXT_DATA__)
│   │   └── web_search.py           # Collecteur complémentaire DuckDuckGo (ddgs) pour WTTJ
│   │
│   ├── matcher/                    # Filtrage strict & qualification
│   │   ├── filter.py               # Exclut alternances, full-remote, seniors, hors zone et non-tech
│   │   └── scorer.py               # Score d'adéquation sur 100 avec bonus présentiel local
│   │
│   ├── letters/                    # Générateur de lettres de motivation personnalisées (PDF)
│   │   └── generator.py            # Adapte data/lettre_type.txt à l'entreprise, au secteur et à l'offre
│   │
│   ├── spontaneous/                # Campagne de candidatures spontanées locales
│   │   ├── models.py               # Modèles TargetCompany et SpontaneousApplication
│   │   ├── pitch_generator.py      # Rédacteur d'e-mails d'accompagnement
│   │   ├── mailer.py               # Envoi SMTP sécurisé (Dry-Run, délai anti-spam, PJ lettre + CV)
│   │   ├── tracker.py              # Historique et relance automatique à J+7
│   │   └── campaign.py             # Orchestrateur CLI de la campagne spontanée
│   │
│   ├── storage/                    # Tableaux de suivi locaux
│   │   ├── tracker_csv.py          # Synchronisation incrémentale dans candidatures.csv
│   │   └── tracker_md.py           # Dashboard Markdown interactif candidatures.md
│   │
│   └── models.py                   # Schéma Pydantic JobOffer
│
├── main.py                         # Point d'entrée CLI principal
├── run_daily.py                    # Lanceur autonome pour la veille quotidienne
├── scripts/
│   └── register_daily_task.ps1     # Enregistrement dans le Planificateur de tâches Windows
├── CV_Bastien_Poissonnet.pdf       # Ton CV joint automatiquement aux envois
├── candidatures.csv                # Tableau de suivi des offres publiées
├── suivi_spontanees.csv            # Tableau de suivi des candidatures spontanées (J+7)
├── candidatures.md                 # Tableau de bord Markdown complet
├── .env.example                    # Modèle de configuration SMTP
└── requirements.txt                # Dépendances Python
```

---

## ⚡ Configuration Initiale (`.env`)

Aucune clé API n'est requise pour collecter les offres (HelloWork, 1jeune1solution et Web Search fonctionnent sans compte).

La configuration `.env` sert uniquement pour l'envoi d'e-mails SMTP lors des campagnes spontanées :

```powershell
Copy-Item .env.example .env
```

Dans `.env`, renseigne tes identifiants Gmail (avec un mot de passe d'application généré sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)) :
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=bastien.poissonnet@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SENDER_EMAIL=bastien.poissonnet@gmail.com
SENDER_NAME=Bastien Poissonnet
SMTP_DELAY_MIN=5
SMTP_DELAY_MAX=15
```

---

## 🚀 Guide d'Utilisation

### Interface Web Locale (Streamlit)

* **Sur Windows :** double-cliquez sur `launch_ui.bat` ou lancez `.venv\Scripts\streamlit run app.py`.
* **Sur Mac (utilisateur tiers) :** consultez [GUIDE_INSTALLATION_MAC.md](file:///c:/Users/basti/OneDrive/Documents/stage-agent/GUIDE_INSTALLATION_MAC.md). Pour générer une archive propre sans vos données personnelles prête à envoyer sur Mac :
  ```powershell
  .venv\Scripts\python scripts\export_for_mac.py
  ```
  Cela crée `StageAgent_Pour_Mac.zip` (vierge de vos fichiers `.env`, CV et suivis).

L'interface s'ouvre dans le navigateur (`http://localhost:8501`) avec 5 onglets : **Offres publiées**, **Spontanées & Relances J+7**, **Lettre à la carte**, **Veille & Modèle** et **Mon Profil**.

---

### Mode 1 : Veille sur les offres publiées (`HelloWork`, `1jeune1solution`, `Web Search`)

```powershell
# Scan complet sur toutes les sources :
.venv\Scripts\python main.py

# Interroger une seule source :
.venv\Scripts\python main.py --source hellowork
.venv\Scripts\python main.py --source 1jeune1solution
.venv\Scripts\python main.py --source web_search

# Ajuster le seuil de score minimal ou la limite par source :
.venv\Scripts\python main.py --min-score 50 --limit 30
```

Le script filtre les offres, calcule leur score, génère une lettre PDF dans `letters/` pour chaque nouvelle offre qualifiée et met à jour `candidatures.csv` et `candidatures.md`.

---

### Mode 2 : Campagne de Candidatures Spontanées Locales

```powershell
# Simulation (Dry-Run par défaut, aucun e-mail envoyé) :
.venv\Scripts\python main.py --spontaneous
.venv\Scripts\python main.py --spontaneous --dept 79   # 17, 79, 85 ou 75

# Envoi réel via SMTP (avec confirmation, PJ lettre + CV et délai anti-spam) :
.venv\Scripts\python main.py --spontaneous --dept 79 --send

# Relances automatiques à J+7 (simulation puis envoi réel) :
.venv\Scripts\python main.py --relance
.venv\Scripts\python main.py --relance --send
```

---

## ✉️ Lettres de motivation personnalisées

Le modèle est dans `data/lettre_type.txt` (modifiable). Les lettres PDF sont générées dans `letters/` :

* **Offres publiées** : une lettre par nouvelle offre qualifiée (chemin dans la colonne `Lettre` de `candidatures.csv`, texte dans `candidatures.md`).
* **Candidatures spontanées** : une lettre par entreprise, jointe au mail avec le CV.
* **Lettre isolée** :
  ```powershell
  .venv\Scripts\python main.py --letter "Entreprise" --address "79000 Niort" --sector "éditeur logiciel" --job-title "Stage Data"
  ```

---

## ⏰ Veille quotidienne

`run_daily.py` lance le scan, écrit `logs/veille_AAAA-MM-JJ.log` et `logs/derniere_veille.txt` (résumé des nouvelles offres). Il **n'envoie aucune candidature**.

Activer la tâche planifiée Windows (tous les jours à 08:00 ; rattrapage au démarrage si le PC était éteint) :
```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 -Time "08:00"
Start-ScheduledTask -TaskName StageAgent-VeilleQuotidienne   # test immédiat
powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 -Remove   # désactiver
```
