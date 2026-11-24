# 🍎 Guide complet d'installation et d'utilisation sur Mac — Stage Agent

Ce guide explique pas à pas comment installer et utiliser **Stage Agent** sur un Mac, **sans aucune connaissance en programmation ni ligne de commande**.

---

## 📦 Étape 1 : Installer Python sur votre Mac (1 seule fois)

Sur les Mac récents, le programme Python n'est pas installé d'office.

1. Ouvrez Safari (ou Chrome) et allez sur :  
   👉 **[https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/)**
2. Cliquez sur le bouton de téléchargement de la dernière version stable (par exemple **Download Python 3.12.x** ou **3.13.x** — fichier `.pkg` *macOS 64-bit universal2 installer*).
3. Double-cliquez sur le fichier téléchargé dans votre dossier **Téléchargements**.
4. Cliquez sur **Continuer** → **Accepter** → **Installer** (entrez votre mot de passe Mac si demandé).
5. Une fois terminé, cliquez sur **Fermer** (vous pouvez mettre le fichier `.pkg` à la corbeille).

> 💡 *Astuce :* si une fenêtre macOS vous propose d'installer les « Outils de développement en ligne de commande (Xcode) », **ignorez-la / cliquez sur Annuler** — le téléchargement depuis `python.org` suffit largement.

---

## 📁 Étape 2 : Préparer le dossier `StageAgent`

1. Récupérez le fichier **`StageAgent_Pour_Mac.zip`** qui vous a été envoyé.
2. Double-cliquez sur le fichier `.zip` pour le décompresser : un dossier **`StageAgent`** apparaît.
3. **Déplacez** ce dossier `StageAgent` dans votre dossier **Documents** (important : ne le laissez pas dans *Téléchargements*, sinon vous risquez de le supprimer par erreur et le raccourci Bureau pointerait vers un dossier déplacé).

---

## 🚀 Étape 3 : Lancer l'installation automatique (et passer la sécurité Mac)

1. Ouvrez le dossier `Documents` → `StageAgent`.
2. Repérez le fichier **`Installer_Mac.command`**.

### ⚠️ Comment autoriser le fichier face à la sécurité macOS (Gatekeeper)
Comme ce fichier vient d'un autre ordinateur, macOS affiche par défaut un message de sécurité (*« Impossible d'ouvrir Installer_Mac.command car son développeur n'est pas vérifié »*). Voici comment l'autoriser proprement :

* **Méthode A (macOS Ventura / anciens macOS) :**
  1. Faites un **Clic droit** (ou `Ctrl` + clic) sur `Installer_Mac.command`.
  2. Cliquez sur **Ouvrir** dans le menu.
  3. Dans la fenêtre qui s'affiche, cliquez à nouveau sur **Ouvrir**.

* **Méthode B (macOS Sonoma / Sequoia) :**
  1. Double-cliquez sur `Installer_Mac.command` → cliquez sur **OK** (ou **Terminé**) sur le message d'avertissement.
  2. Ouvrez **Réglages Système** (icône engrenage) → **Confidentialité et sécurité**.
  3. Descendez tout en bas jusqu'à la rubrique *Sécurité* : vous verrez le message *« Installer_Mac.command a été bloqué... »* avec un bouton **Ouvrir quand même**. Cliquez dessus, puis confirmez **Ouvrir**.

### Pendant l'installation
* Une fenêtre s'ouvre et installe automatiquement tout ce dont l'outil a besoin (1 à 2 minutes la première fois).
* À la fin :
  * Une icône **`Stage Agent`** est créée automatiquement sur votre **Bureau**.
  * Votre navigateur s'ouvre tout seul sur l'interface de l'application (`http://localhost:8501`).

> 🛠️ **Si jamais macOS dit « Vous n'avez pas les autorisations » sur `.command` :**
> Ouvrez l'application *Terminal* (Loupe Spotlight `Cmd + Espace` → tapez `Terminal`), tapez `chmod +x ` (avec un espace à la fin), glissez le fichier `Installer_Mac.command` et `Lancer_Mac.command` dans la fenêtre du Terminal, puis appuyez sur **Entrée**. Vous pourrez ensuite double-cliquer normalement.

---

## 🖥️ Étape 4 : Utilisation au quotidien

* **Pour ouvrir l'outil :** double-cliquez simplement sur l'icône **`Stage Agent`** sur votre **Bureau** (si macOS vous le demande la toute première fois sur l'icône Bureau, refaites *Réglages Système → Confidentialité et sécurité → Ouvrir quand même* une seule fois).
* **Aucune fenêtre noire ne reste gênante :** l'application démarre en arrière-plan et ouvre votre navigateur sur `http://localhost:8501`.
* **Pour fermer l'outil :** cliquez sur le bouton **« ⏻ Fermer l'application »** en bas du menu de gauche dans l'interface, puis fermez l'onglet du navigateur.

---

## ⚙️ Étape 5 : Configurer votre propre profil (à faire en premier !)

À la première ouverture, l'application contient un profil d'exemple. Allez dans le dernier onglet **`⚙️ Mon Profil`** :

1. **Identité & Formation :** renseignez votre prénom/nom, e-mail, téléphone, adresse, formation, spécialité, école et dates de stage.
2. **Critères de recherche :**
   * **Mots-clés de recherche :** mettez 2 à 4 mots-clés simples de votre domaine (ex. `marketing, communication, digital` ou `ressources humaines, rh`).
   * **Villes / régions cibles :** ex. `Paris, Lyon` (ou votre ville).
   * **Codes départements :** ex. `75, 92, 69` (laissez vide pour chercher dans toute la France).
   * **Cases à cocher importantes :**
     * ✅ **Stages uniquement (exclure alternances)** : laissez coché pour ne recevoir que des stages.
     * ☐ **Exclure le 100 % télétravail** : cochez si vous voulez uniquement du présentiel / hybride.
     * ☐ **Exclure les métiers non-tech (mode IT/Data)** : **DÉCOCHEZ cette case** si vous ne cherchez pas un stage en informatique/dev (par exemple si vous cherchez en commerce, marketing, RH, communication, etc.).
3. **Compétences & Atouts :** indiquez vos compétences clés (ex. `Excel, Canva, Gestion de projet, Anglais`) et un court résumé de vos expériences.
4. Cliquez sur **« 💾 Enregistrer mon profil »**.
5. **Mon CV (PDF) :** cliquez sur **Browse files** pour importer votre CV au format `.pdf`.

---

## 🧭 Étape 6 : Guide des autres onglets

### 1. 🚀 Offres Publiées
* Dans le menu de gauche, cliquez sur **« 🚀 Lancer la collecte »** : l'outil va chercher les stages correspondants sur **HelloWork**, **1jeune1solution** (portail du gouvernement) et via recherche web (**Welcome to the Jungle**).
* Les offres trouvées apparaissent triées par score de pertinence.
* Vous pouvez changer la colonne **Statut** (`À contacter` → `Candidaté` → `Entretien` → `Refusé`) directement dans le tableau, puis cliquer sur **« 💾 Enregistrer les changements de statut »**.
* En bas de l'onglet, sélectionnez une offre pour ouvrir son lien ou **télécharger sa lettre de motivation PDF** personnalisée.

### 2. 📬 Spontanées & Relances J+7
* **Étape importante avant tout envoi :** tout en bas de cet onglet se trouve le tableau **`data/target_companies.csv`**. Ajoutez-y les entreprises que vous ciblez avec leur **vraie adresse e-mail de recrutement** (vérifiée sur leur site web ou LinkedIn), puis cliquez sur **« 💾 Sauvegarder target_companies.csv »**.
* **Envoyer sans configuration compliquée (recommandé) :**
  1. Choisissez une entreprise dans la liste **« Prévisualiser le mail et la lettre pour »**.
  2. Cliquez sur **« 📄 Générer la lettre PDF pour cette entreprise »** puis téléchargez-la.
  3. Cliquez sur **« 📧 Ouvrir le brouillon dans ma messagerie »** : votre application Mail / Gmail s'ouvre avec le destinataire, l'objet et le texte déjà remplis ! Il ne vous reste plus qu'à glisser votre CV et la lettre PDF puis envoyer.
* **Option envoi groupé automatique (SMTP Gmail) :**
  * Si vous souhaitez que l'outil envoie les mails tout seul avec le CV et la lettre déjà attachés (et gère les relances automatiques à J+7) :
    1. Activez la validation en 2 étapes sur votre compte Google.
    2. Créez un *Mot de passe d'application* sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (16 caractères).
    3. Renseignez ces infos dans l'onglet **`⚙️ Mon Profil`** → *Configuration e-mail automatique (SMTP)*.
    4. Faites toujours un essai avec **« 🧪 Simuler la campagne (Dry-Run) »** avant de cocher la confirmation d'envoi réel.

### 3. ✉️ Lettre à la Carte
* Permet de générer en 5 secondes une lettre de motivation PDF sur mesure pour n'importe quelle entreprise trouvée ailleurs (LinkedIn, Indeed, connaissance...).

### 4. ⏰ Veille & Modèle
* Permet de modifier librement votre texte de lettre type (`data/lettre_type.txt`) tout en conservant les balises entre accolades (`{nom_entreprise}`, `{nom_candidat}`, `{formation}`, etc.).

---

## ❓ Dépannage rapide

| Problème | Solution |
| :--- | :--- |
| **La page `localhost:8501` ne s'ouvre pas ou affiche une erreur** | Attendez 5 secondes et actualisez la page (`Cmd + R`), ou relancez `Stage Agent` sur le Bureau. Consultez `StageAgent/logs/streamlit.log` si besoin. |
| **Aucune offre ne remonte lors du scan** | Vérifiez dans `⚙️ Mon Profil` : si vous n'êtes pas dans l'informatique, vérifiez que **« Exclure les métiers non-tech » est bien DÉCOCHÉ**, élargissez le seuil de score minimal à `25` dans la barre latérale, ou laissez le champ *Départements* plus large. |
| **Erreur au double-clic sur l'icône Bureau après avoir déplacé le dossier** | Si vous avez déplacé le dossier `StageAgent` après l'installation, relancez simplement `Installer_Mac.command` depuis le nouvel emplacement pour mettre à jour le raccourci. |
