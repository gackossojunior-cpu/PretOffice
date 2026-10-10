# Backend PrêtOffice

API REST de gestion multi-prêteurs construite avec Django REST Framework et
SimpleJWT. Les routes existantes restent préfixées par `/api/`.

## Installation et lancement

Depuis ce dossier, avec Python 3.14 :

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Pour un environnement de développement, laissez `DJANGO_DEBUG=true`. Avant
tout déploiement, remplacez `DJANGO_SECRET_KEY` par une valeur aléatoire d'au
moins 50 caractères, configurez `DJANGO_ALLOWED_HOSTS`, le moteur/base de
données, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` et l'email SMTP. Le
fichier `.env` est ignoré par Git.

```bash
python manage.py migrate
python manage.py check
python manage.py runserver
```

Le backend démarre sur `http://127.0.0.1:8000` par défaut.

## Comptes et authentification

L'inscription crée un compte prêteur et son profil dans une transaction
atomique. Les validateurs Django s'appliquent au mot de passe; les doublons de
nom d'utilisateur et d'adresse email sont rejetés.

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "mon_preteur",
    "email": "preteur@example.invalid",
    "first_name": "Sam",
    "last_name": "Exemple",
    "phone": "+0000000000",
    "password": "UnMotDePasseLong-123!",
    "password_confirm": "UnMotDePasseLong-123!"
  }'

curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"mon_preteur","password":"UnMotDePasseLong-123!"}'
```

Le login renvoie `access` et `refresh`. Incluez le jeton d'accès dans
`Authorization: Bearer <access>`. Le refresh est rotatif et l'ancien jeton est
blacklisté :

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/refresh/ \
  -H 'Content-Type: application/json' \
  -d '{"refresh":"<refresh>"}'

curl http://127.0.0.1:8000/api/lenders/me/ \
  -H 'Authorization: Bearer <access>'

curl -X PATCH http://127.0.0.1:8000/api/lenders/me/ \
  -H 'Authorization: Bearer <access>' \
  -H 'Content-Type: application/json' \
  -d '{"business_name":"Mon établissement"}'
```

## Ressources API

Toutes les routes privées exigent un JWT. Les réponses d'erreur ont la forme
`{"detail":"…","errors":{…}}`. Les objets appartenant à un autre prêteur sont
filtrés et apparaissent comme inexistants (404).

| Méthode | Route | Description |
| --- | --- | --- |
| POST | `/api/auth/register/` | Créer un prêteur et son profil |
| POST | `/api/auth/login/` | Obtenir les jetons JWT |
| POST | `/api/auth/token/refresh/` | Renouveler les jetons |
| GET, PATCH | `/api/lenders/me/` | Consulter ou modifier le profil |
| GET | `/api/borrowers/` | Lister ses emprunteurs |
| GET, PATCH, PUT | `/api/borrowers/<id>/` | Consulter ou modifier un emprunteur à soi |
| GET, POST | `/api/invitations/` | Lister ou créer ses invitations |
| GET | `/api/invitations/<id>/` | Consulter une invitation à soi |
| POST | `/api/invitations/<id>/revoke/` | Révoquer une invitation en attente |
| GET, POST | `/api/invitations/public/<token>/` | Vérifier ou utiliser une invitation |
| POST | `/api/invitations/public/<token>/apply/` | Alias historique de soumission |
| GET, POST | `/api/loans/` | Lister ou créer une demande de prêt |
| POST | `/api/loans/<id>/decision/` | Approuver ou refuser une demande |
| GET | `/api/loans/<id>/` | Consulter le prêt accordé |
| GET | `/api/loans/<id>/installments/` | Lister les échéances |
| GET, POST | `/api/loans/<id>/repayments/` | Lister ou enregistrer un remboursement |
| POST | `/api/loans/<id>/cancel/` | Annuler un prêt sans remboursement |
| GET | `/api/schema/` | Schéma OpenAPI |
| GET | `/api/docs/` | Interface Swagger |

Les listes sont paginées (`page`, `page_size`, maximum 100). Elles acceptent
les filtres documentés par leur vue (`status`, `borrower`, dates) et un tri
`ordering` restreint aux champs autorisés.

### Invitations

```bash
curl -X POST http://127.0.0.1:8000/api/invitations/ \
  -H 'Authorization: Bearer <access>' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

La réponse inclut `invitation_url`. Le prêteur peut configurer l'origine
partagée par `INVITATION_PUBLIC_BASE_URL`. Les liens publics expirés, révoqués,
déjà utilisés ou inconnus répondent de façon générique. La soumission publique
est limitée à 10 requêtes par heure et l'usage unique est protégé par une
transaction et une mise à jour conditionnelle.

### Demandes, prêts et remboursements

Une demande est créée au nom du prêteur authentifié; `lender` fourni par le
client est ignoré. Le champ `borrower` doit appartenir à ce prêteur.

```bash
curl -X POST http://127.0.0.1:8000/api/loans/ \
  -H 'Authorization: Bearer <access>' \
  -H 'Content-Type: application/json' \
  -d '{
    "borrower": 1,
    "amount_requested": "100000.00",
    "duration_months": 12,
    "interest_rate": "5.00",
    "purpose": "Fonds de commerce"
  }'

curl -X POST http://127.0.0.1:8000/api/loans/1/decision/ \
  -H 'Authorization: Bearer <access>' \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "APPROVE",
    "reason": "Dossier accepté",
    "interest_type": "SIMPLE",
    "frequency": "MONTHLY"
  }'

curl -X POST http://127.0.0.1:8000/api/loans/1/repayments/ \
  -H 'Authorization: Bearer <access>' \
  -H 'Content-Type: application/json' \
  -d '{"amount":"10000.00","payment_method":"MOBILE_MONEY"}'
```

Les montants sont des décimaux. Les intérêts simples sont calculés sur la durée
totale; `interest_type: "NONE"` désactive les intérêts. Les pénalités sont
désactivées par défaut. Les règlements s'imputent sur les échéances les plus
anciennes; le surpaiement est refusé. Les paiements ne sont pas supprimables.
La commande `python manage.py update_overdue_loans` peut être lancée par cron.

## Décisions métier par défaut

- Devise d'affichage : `XAF`, configurable par `CURRENCY_CODE`.
- Intérêt simple calculé pour la durée entière; option sans intérêt.
- Périodicité mensuelle par défaut, ou hebdomadaire.
- Pénalités désactivées par défaut; si activées, une pénalité configurée est
  appliquée une fois par échéance en retard.
- Remboursement anticipé autorisé.
- Pas de suppression physique des prêts ou remboursements. L'annulation d'un
  prêt est tracée et refusée après tout remboursement.

Ces comportements sont des propositions par défaut à valider par le métier,
notamment le calcul des pénalités et la règle d'annulation après paiement.

## Démo

```bash
python manage.py load_demo_data
```

La commande est idempotente et crée deux prêteurs, des emprunteurs, des
invitations, des prêts, leurs échéanciers et des remboursements. Les comptes
créés n'ont **pas** de mot de passe utilisable : définissez-en un manuellement
depuis l'administration Django si vous souhaitez les utiliser pour une
démonstration interactive.

## Tests et contrôles de déploiement

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
python manage.py spectacular --validate
python manage.py check --deploy
```

En production, exécutez `check --deploy` avec `DJANGO_DEBUG=false`, une clé
forte, des hôtes autorisés et les paramètres HTTPS configurés. N'activez HSTS
qu'une fois HTTPS stable sur le domaine.
