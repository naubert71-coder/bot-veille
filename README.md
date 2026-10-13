# Bot Veille — veille automatisée sur flux RSS + Gemini

Un bot de veille qui collecte des flux RSS, les trie via un LLM (Gemini),
et vous envoie un digest HTML par e-mail chaque jour. 100 % gratuit, sans
serveur à entretenir : le calcul tourne sur GitHub Actions, le déclenchement
sur cron-job.org, l'IA sur le free tier Gemini, l'envoi sur Gmail SMTP.

Chaque utilisateur configure **ses propres accès** (sa clé Gemini, son Gmail,
son compte cron-job.org). Aucune donnée ne transite par un tiers.

---

## Comment ça marche

```
cron-job.org  ──(POST API)──▶  GitHub Actions  ──▶  run.py
                                                       │
                          ┌────────────────────────────┼────────────────┐
                          ▼                            ▼                ▼
                    collecte RSS              tri par Gemini        envoi mail
                  (config.yaml)            (prompts/*.md)          (SMTP)
```

- `run.py` : point d'entrée, orchestre le pipeline.
- `config.yaml` : **le seul fichier à éditer** (sources, format, fenêtre).
- `prompts/` : le prompt de tri — c'est là que se joue la pertinence.
- `engine/` : la logique (collecte, tri, rendu, envoi). À ne pas toucher.

---

## Installation (≈ 10 minutes)

### 1. Créer votre repo

Sur cette page GitHub, cliquez **Use this template → Create a new repository**.
Nommez-le (ex. `ma-veille`) et laissez-le **Public** (nécessaire pour la
free tier GitHub Actions).

### 2. Configurer `config.yaml`

Ouvrez `config.yaml` et adaptez :
- `sources.rss` : vos flux RSS. `configs/example.yaml` montre un exemple complet.
- `triage.prompt_file` : le fichier de prompt à utiliser (voir étape 3).
- `triage.model_chain` : les modèles Gemini accessibles avec **votre** clé
  (vérifiez la liste sur [aistudio.google.com](https://aistudio.google.com)).

### 3. Choisir / personnaliser le prompt

Le bot lit le prompt indiqué dans `config.yaml`. Deux options :
- Partez de `prompts/biblio.md` (générique) et adaptez le **THÈME DE LA VEILLE**.
- Copiez `prompts/example-scientifique.md` (exemple sur l'IA générative) et
  modifiez le thème, les exclusions et les priorités selon votre sujet.

### 4. Définir les 4 secrets GitHub

`Settings → Secrets and variables → Actions → New repository secret` :

| Secret | Valeur |
|--------|--------|
| `GEMINI_API_KEY` | clé API (sur aistudio.google.com → Get API key) |
| `EMAIL_SENDER` | l'adresse Gmail qui **envoie** |
| `EMAIL_PASSWORD` | **mot de passe d'application** Gmail (voir ⚠️ ci-dessous) |
| `EMAIL_RECEIVER` | l'adresse qui **reçoit** |

> ⚠️ **`EMAIL_PASSWORD` n'est PAS votre mot de passe Gmail.** Gmail bloque
> les connexions SMTP par mot de passe normal. Activez la vérification en
> 2 étapes sur [myaccount.google.com](https://myaccount.google.com), puis
> créez un **Mot de passe d'application** (Sécurité → Mots de passe
> d'application → Mail). Copiez le code à 16 caractères **sans les espaces**.

### 5. Créer un Personal Access Token (PAT)

`Settings (compte) → Developer settings → Personal access tokens →
Fine-grained tokens → Generate new token` :
- **Repository access** → *Only select repositories* → votre repo `ma-veille`.
- **Permissions → Repository permissions → Actions → Read and write**.

> ⚠️ Sans la permission **Actions: Read and write**, cron-job.org recevra un
> `403` silencieux et le job ne partira jamais.

Copiez le token (il n'apparaît qu'une fois). **Ne le partagez jamais.**

### 6. Configurer cron-job.org

Sur [cron-job.org](https://cron-job.org) → **Create cronjob** :

- **URL** (méthode **POST**) :
  `https://api.github.com/repos/VOTRE_PSEUDO/ma-veille/actions/workflows/veille.yml/dispatches`
- **HTTP method** : `POST`
- **Headers** :
  - `Authorization` : `Bearer <VOTRE_PAT>`
  - `Content-Type` : `application/json`
  - `Accept` : `application/vnd.github+json`
- **Body** (⚠️ le champ `ref` est **obligatoire**) :
  `{"ref":"main"}`
- **Schedule** : l'heure de votre choix, **fuseau `Europe/Paris`**.

> ⚠️ Deux pièges : le body doit contenir `"ref":"main"` (sinon `422`), et le
> fuseau doit être explicite (sinon l'heure est interprétée en UTC).

### 7. Tester

Sur cron-job.org, cliquez **Run now** sur votre job. Un run doit apparaître
dans l'onglet **Actions** de votre repo, puis vous recevez votre premier mail.

---

## Limites connues (free tier)

- **Quota Gemini** : le free tier limite à ~20 requêtes/jour **par modèle**.
  Un bot quotidien (1 run/jour) est très loin du plafond. Si vous épuisez le
  quota, le bot envoie un mail « aucune nouveauté » au lieu de planter.
- **Flux RSS** : certains éditeurs renvoient parfois un XML mal formé ; le
  bot les signale dans les logs (`flux illisible`) et continue avec les autres.
- **Fenêtre 24 h sans persistance** : si un run est raté (quota, panne), les
  articles de cette journée ne sont pas rattrapés au run suivant.

---

## Personnalisation avancée

- **Autre relais SMTP** : changez `smtp_host` / `smtp_port` dans `config.yaml`.
- **Taille du digest** : ajustez `triage.max_items` et `output.window_hours`.
- **Plusieurs veilles** : créez plusieurs fichiers `config-*.yaml` et lancez
  le workflow avec `VEILLE_CONFIG=config-science.yaml`.
