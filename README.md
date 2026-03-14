# 🚀 SMarketing — Application Web Marketing Automation

Application web complète de Marketing Automation & CRM, développée en **Flask + MySQL**, avec intégration **IA Grok (xAI)**.

---

## 📋 Fonctionnalités

| Module | Description |
|---|---|
| 🔐 Authentification | Inscription, connexion, gestion du profil |
| 🤖 IA Grok | Analyse du profil, génération de concurrents & prospects |
| ♟️ Concurrents | 500 concurrents générés par IA + SWOT + PDF |
| 👥 Prospects | 500 clients potentiels multiservices + PDF |
| 📧 Mass Mailing | Campagnes email avec templates IA, envoi individuel ou masse |
| 💼 Pipeline CRM | Kanban : réponse → intérêt → devis → BC → livraison → maintenance |
| 📄 Devis | Création interne avec lignes ou upload PDF, export PDF |
| 📋 Bons de commande | Création ou upload, suivi livraison, PV de réception |
| 🔧 Maintenance | Contrats de maintenance avec alertes de renouvellement |
| 📊 Dashboard | KPIs, entonnoir de conversion, graphiques |

---

## ⚙️ Installation

### 1. Prérequis
```bash
Python 3.10+
MySQL 8.0+
pip
```

### 2. Cloner / Créer le répertoire
```bash
mkdir marketing_automation
cd marketing_automation
```

### 3. Environnement virtuel
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 4. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 5. Créer la base de données MySQL
```sql
-- Dans MySQL :
mysql -u root -p
CREATE DATABASE marketing_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Ou exécutez le script fourni :
```bash
mysql -u root -p < init_db.sql
```

### 6. Configurer les variables d'environnement
Copiez `.env` et remplissez vos valeurs :
```bash
SECRET_KEY=changez-cette-cle-secrete
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=votre_mot_de_passe_mysql
MYSQL_DB=marketing_automation

# Clé API Grok (xAI) — https://console.x.ai/
GROQ_API_KEY=xai-votre-cle-api

# Email SMTP (Gmail ou autre)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=votre@email.com
MAIL_PASSWORD=votre-mot-de-passe-app
```

> 💡 Pour Gmail : activez "Mots de passe d'application" dans les paramètres de sécurité Google.

### 7. Lancer l'application
```bash
python app.py
```

Accédez à : **http://localhost:5000**

---

## 🗂️ Structure du Projet

```
marketing_automation/
├── app.py                    # Point d'entrée Flask
├── config.py                 # Configuration
├── requirements.txt          # Dépendances Python
├── .env                      # Variables d'environnement
├── init_db.sql               # Script SQL d'initialisation
│
├── models/
│   └── __init__.py           # Modèles SQLAlchemy (MySQL)
│       ├── User, Company
│       ├── Competitor
│       ├── Prospect
│       ├── EmailCampaign, EmailLog
│       ├── Opportunity
│       ├── Quote, QuoteItem
│       ├── Order
│       ├── MaintenanceContract
│       └── ActivityLog
│
├── routes/
│   ├── auth.py               # Authentification
│   ├── dashboard.py          # Tableau de bord
│   ├── competitors.py        # Gestion des concurrents
│   ├── prospects.py          # Gestion des prospects
│   ├── pipeline.py           # Pipeline CRM
│   └── mailing.py            # Campagnes email
│
├── utils/
│   ├── groq_ai.py               # Intégration API Grok (xAI)
│   └── pdf_generator.py      # Génération PDF (ReportLab)
│
├── templates/
│   ├── base.html             # Template de base (sidebar, topbar)
│   ├── auth/                 # login, register, profile
│   ├── dashboard/            # index
│   ├── competitors/          # index, form, view
│   ├── prospects/            # index, form, view
│   ├── pipeline/             # index (kanban), opportunity, quotes, orders, maintenance
│   └── mailing/              # index, create, view
│
└── static/
    ├── css/
    ├── js/
    └── uploads/              # Fichiers uploadés (devis, BC, PV, contrats)
```

---

## 🤖 Utilisation de l'IA Grok

L'IA Grok est utilisée pour :

| Fonction | Description |
|---|---|
| Analyse profil | Extrait mots-clés, secteur, ICP depuis la description |
| Génération concurrents | Identifie jusqu'à 500 concurrents dans votre pays |
| Génération prospects | Identifie jusqu'à 500 clients potentiels multiservices |
| Analyse SWOT | Génère une analyse SWOT pour chaque concurrent |
| Templates email | Génère des emails B2B personnalisés par secteur |

---

## 🔄 Cycle de Vente Complet

```
Prospect (nouveau)
    ↓ Email envoyé        → Statut : Contacté
    ↓ Réponse reçue       → Statut : A répondu + Création d'opportunité
    ↓ Intérêt manifesté   → Statut : Intéressé
    ↓ Devis créé/uploadé  → Statut : Devis envoyé
    ↓ BC signé            → Statut : GAGNÉ ✅
    ↓ Livraison + PV      → Statut : Livré
    ↓ Contrat maintenance → Statut : Maintenance 🔧
```

---

## 📊 Pipeline CRM — Stades

| Stade | Déclencheur |
|---|---|
| 💬 A répondu | Le prospect répond à votre email |
| ⭐ Intéressé | Marqué manuellement |
| 📄 Devis envoyé | Création ou upload d'un devis |
| 🏆 Gagné | Bon de commande signé |
| ❌ Perdu | Marqué perdu (avec raison) |
| 🚚 Livré | Livraison confirmée + PV optionnel |
| 🔧 Maintenance | Contrat de maintenance créé |

---

## 🔧 Configuration Email SMTP

Pour l'envoi réel des emails, configurez dans `.env` :

```bash
# Gmail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=votre@gmail.com
MAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Mot de passe d'application

# Office 365
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
```

---

## 📦 Dépendances Principales

| Package | Usage |
|---|---|
| Flask | Framework web |
| Flask-SQLAlchemy | ORM MySQL |
| Flask-Login | Gestion des sessions |
| Flask-Mail | Envoi d'emails |
| PyMySQL | Connecteur MySQL |
| ReportLab | Génération PDF |
| Requests | Appels API Grok |
| python-dotenv | Variables d'environnement |
| Werkzeug | Hashage des mots de passe |

---

## 🚀 Déploiement Production

```bash
# Installer Gunicorn
pip install gunicorn

# Lancer en production
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

---

## 📝 Notes importantes

- Les tables MySQL sont créées **automatiquement** au premier lancement
- Les fichiers uploadés (devis, BC, PV) sont stockés dans `static/uploads/`
- La génération IA nécessite une clé API Grok valide
- En développement, les emails peuvent être loggués au lieu d'être envoyés

---

*Développé avec Flask + MySQL + Grok AI*
