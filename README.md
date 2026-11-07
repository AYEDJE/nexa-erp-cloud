# NexaERP Cloud

NexaERP Cloud est une application ERP orientée SaaS et multi-entreprises. Le dépôt contient une API Python construite avec FastAPI, une interface web et des modules de gestion métier, de sécurité et de traitement documentaire.

## Fonctionnalités

Les modules présents dans l’application couvrent notamment :

- la gestion des produits, des utilisateurs et des entreprises ;
- les factures, les achats, les fournisseurs et les stocks ;
- la trésorerie ;
- l’authentification SaaS et l’isolation des données par entreprise ;
- les rôles, permissions, traces d’activité et fonctions d’audit ;
- les documents, l’OCR, la recherche, les fonctions IA et les sauvegardes.

## Technologies

- Python et [FastAPI](https://fastapi.tiangolo.com/) pour l’API ;
- SQLAlchemy pour l’accès aux données ;
- HTML, CSS et JavaScript pour l’interface web ;
- pytest pour les tests.

Les dépendances Python sont répertoriées dans [`requirements.txt`](requirements.txt).

## Structure du dépôt

```text
.
├── app/
│   ├── api/          # Routes et modules de l’API
│   ├── core/         # Configuration et composants centraux
│   ├── models/       # Modèles de données
│   ├── routers/      # Routes d’authentification et de plateforme
│   ├── schemas/      # Schémas de validation
│   ├── services/     # Services métier
│   ├── utils/        # Utilitaires
│   └── main.py       # Création de l’application FastAPI
├── frontend/         # Pages et ressources de l’interface web
├── tests/            # Tests
├── requirements.txt
└── pytest.ini
```

## Prérequis

- Python 3.10 ou supérieur ;
- pip.

## Installation et démarrage

À la racine du dépôt, créez un environnement virtuel et installez les dépendances :

```bash
git clone https://github.com/AYEDJE/nexa-erp-cloud.git
cd nexa-erp-cloud
python -m venv .venv
```

Activez ensuite l’environnement virtuel.

Linux / macOS :

```bash
source .venv/bin/activate
```

Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
```

Installez les dépendances et démarrez l’API :

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

L’API est alors accessible sur `http://127.0.0.1:8000`. La documentation interactive FastAPI est disponible sur `http://127.0.0.1:8000/docs`.

L’application expose également les routes `/health` pour le contrôle de santé et `/` pour les informations de statut.

## Interface web

Les pages de l’interface se trouvent dans `frontend/`. Pour les servir localement, lancez par exemple depuis la racine :

```bash
python -m http.server 8080 --directory frontend
```

Puis ouvrez `http://127.0.0.1:8080` dans votre navigateur. Selon la configuration de l’application, l’URL de l’API peut nécessiter un ajustement pour l’utilisation locale.

## Tests

Lancez les tests avec pytest :

```bash
pytest
```

## Configuration et déploiement

La configuration de la base de données, des secrets et des autres paramètres de déploiement dépend de l’environnement et des modules du projet. Avant un déploiement, configurez ces valeurs de manière sécurisée, n’exposez pas de secrets dans le dépôt et vérifiez les paramètres CORS, l’authentification, les sauvegardes ainsi que la configuration de la base de données.

Pour la production, utilisez HTTPS et un serveur ASGI configuré pour votre environnement. Consultez la documentation FastAPI et Uvicorn pour les options de déploiement.

## Contribution

Les contributions sont les bienvenues. Pour proposer une évolution, créez une branche dédiée, effectuez vos changements et ouvrez une pull request en décrivant leur objectif et les tests effectués.

## Licence

Aucun fichier de licence n’a été identifié dans le dépôt. Les conditions de réutilisation et de redistribution restent donc à préciser par le propriétaire du projet.
