# PrêtOffice — frontend

Interface web React/TypeScript en français pour l’API Django REST de PrêtOffice.

## Prérequis et lancement

Node.js 22.13 ou supérieur et npm :

```bash
npm install
cp .env.example .env
npm run dev
```

En développement, le proxy Vite transmet `/api` à
`http://127.0.0.1:8000` (personnalisable avec `VITE_API_PROXY_TARGET`) afin
d’éviter une configuration CORS locale. Définissez `VITE_API_URL` sur l’URL
absolue de l’API pour un déploiement où frontend et API sont séparés. Pour
produire et vérifier une version de production :

```bash
npm run build
npm run lint
npm test
npm run preview
```

Générer à nouveau les types OpenAPI après une évolution du contrat backend :

```bash
npm run generate:api
```

Cette commande attend le schéma à `http://127.0.0.1:8000/api/schema/`.

## Authentification et données

Le jeton d’accès reste en mémoire. Le jeton refresh est conservé dans
`sessionStorage` afin de survivre à un rechargement de l’onglet. Ce mécanisme
n’est qu’un compromis de développement : avant la mise en production, il faut
le remplacer par un cookie `httpOnly`, `Secure`, avec la protection CSRF
appropriée côté backend.

L’intercepteur renouvelle une seule fois l’accès après un 401 et rejoue la
requête initiale. Si le renouvellement échoue, la session est effacée. Les
routes privées vérifient l’existence d’un profil prêteur et affichent une
explication claire si le compte n’en possède pas.

## Écrans

- Connexion et inscription, avec validation côté formulaire et erreurs API.
- Tableau de bord : compteurs d’emprunteurs, invitations ouvertes et demandes
  en attente, alimentés par les listes paginées réelles.
- Emprunteurs : liste paginée, recherche sur la page courante, filtres par date
  et fiche modifiable.
- Invitations : création, copie du lien de la page frontend, filtres par statut
  et dates, pagination, révocation.
- Page publique mobile d’invitation : vérification du lien, saisie et envoi des
  informations, confirmation, réponses génériques pour les liens invalides et
  message clair pour le throttling HTTP 429.
- Demandes : création, filtres, pagination, décision (approbation ou refus).
- Détail d’un prêt : totaux, échéancier, historique et saisie des
  remboursements, annulation du prêt si l’API l’autorise.
- Profil du prêteur : consultation et modification des coordonnées.

Tous les montants et totaux sont fournis par l’API; aucune opération financière
n’est calculée dans le navigateur. Les montants sont présentés en XAF et les
dates en français.

## Écarts connus avec l’API

- Il n’existe pas d’endpoint pour lister les prêts accordés. `GET /api/loans/`
  liste les demandes et un prêt n’est accessible qu’avec son identifiant. La
  page « Prêts » signale cette limite; un prêt approuvé peut être ouvert depuis
  la décision.
- Le dashboard backend ne fournit pas le total prêté, le total remboursé, le
  solde global, les retards ni les prochaines échéances. Le frontend ne les
  agrège pas à partir des données.
- L’API n’expose pas l’annulation compensatoire d’un remboursement; aucun
  bouton d’annulation de paiement n’est proposé.
- Le formulaire d’invitation utilise les champs texte du schéma OpenAPI. Le
  champ facultatif de pièce justificative n’est pas téléversé par ce formulaire.

## Configuration CORS du backend

Le proxy évite CORS en développement. Si le frontend déployé contacte l’API
directement depuis une autre origine, ajouter l’origine exacte du frontend à
`CORS_ALLOWED_ORIGINS` dans la configuration d’environnement backend. Ne pas
utiliser `*` en production. L’origine de déploiement et le transport HTTPS
doivent être configurés avant exposition publique.
