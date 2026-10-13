# Watch Bot — automated RSS + Gemini digest

A monitoring bot that collects RSS feeds, triages them with an LLM (Gemini),
and sends you a daily HTML digest by email. 100% free, no server to maintain:
compute runs on GitHub Actions, scheduling on cron-job.org, the LLM on the
Gemini free tier, delivery over Gmail SMTP.

Each user configures **their own credentials** (their Gemini key, their Gmail,
their cron-job.org account). No data ever passes through a third party.

---

## How it works

```
cron-job.org  ──(POST API)──▶  GitHub Actions  ──▶  run.py
                                                       │
                          ┌────────────────────────────┼────────────────┐
                          ▼                            ▼                ▼
                    RSS collection               Gemini triage       email send
                  (config.yaml)               (prompts/*.md)          (SMTP)
```

- `run.py` : entry point, orchestrates the pipeline.
- `config.yaml` : **the only file you edit** (sources, format, window).
- `prompts/` : the triage prompt — this is where relevance is decided.
- `engine/` : the logic (collect, triage, render, send). Do not touch.

---

## Installation (≈ 10 minutes)

### 1. Create your repo

On this GitHub page, click **Use this template → Create a new repository**.
Name it (e.g. `my-watch`) and keep it **Public** (required for the
GitHub Actions free tier).

### 2. Configure `config.yaml`

Open `config.yaml` and edit:
- `sources.rss` : your RSS feeds. `configs/example.yaml` shows a full example.
- `triage.prompt_file` : the prompt file to use (see step 3).
- `triage.model_chain` : the Gemini models accessible with **your** key
  (check the list on [aistudio.google.com](https://aistudio.google.com)).

### 3. Pick / customize the prompt

The bot reads the prompt set in `config.yaml`. Two options:
- Start from `prompts/biblio.md` (generic) and adapt the **WATCH THEME**.
- Copy `prompts/example-scientifique.md` (an example on generative AI) and
  change the theme, exclusions and priorities to fit your subject.

### 4. Set the 4 GitHub secrets

`Settings → Secrets and variables → Actions → New repository secret` :

| Secret | Value |
|--------|-------|
| `GEMINI_API_KEY` | API key (on aistudio.google.com → Get API key) |
| `EMAIL_SENDER` | the Gmail address that **sends** |
| `EMAIL_PASSWORD` | Gmail **app password** (see ⚠️ below) |
| `EMAIL_RECEIVER` | the address that **receives** |

> ⚠️ **`EMAIL_PASSWORD` is NOT your Gmail password.** Gmail blocks SMTP
> logins with the normal password. Turn on 2-Step Verification on
> [myaccount.google.com](https://myaccount.google.com), then create an
> **App password** (Security → App passwords → Mail). Copy the 16-character
> code **without spaces**.

### 5. Create a Personal Access Token (PAT)

`Settings (account) → Developer settings → Personal access tokens →
Fine-grained tokens → Generate new token` :
- **Repository access** → *Only select repositories* → your `my-watch` repo.
- **Permissions → Repository permissions → Actions → Read and write**.

> ⚠️ Without the **Actions: Read and write** permission, cron-job.org gets a
> silent `403` and the job never runs.

Copy the token (it appears only once). **Never share it.**

### 6. Configure cron-job.org

On [cron-job.org](https://cron-job.org) → **Create cronjob** :

- **URL** (method **POST**) :
  `https://api.github.com/repos/YOUR_USERNAME/my-watch/actions/workflows/veille.yml/dispatches`
- **HTTP method** : `POST`
- **Headers** :
  - `Authorization` : `Bearer <YOUR_PAT>`
  - `Content-Type` : `application/json`
  - `Accept` : `application/vnd.github+json`
- **Body** (⚠️ the `ref` field is **required**) :
  `{"ref":"main"}`
- **Schedule** : the time you want, **timezone `Europe/Paris`** (or yours).

> ⚠️ Two pitfalls: the body must contain `"ref":"main"` (otherwise `422`), and
> the timezone must be explicit (otherwise the hour is read as UTC).

### 7. Test it

On cron-job.org, click **Run now** on your job. A run should appear in the
**Actions** tab of your repo, then you receive your first email.

---

## Known limits (free tier)

- **Gemini quota** : the free tier caps at ~20 requests/day **per model**.
  A daily bot (1 run/day) is far below the cap. If you run out of quota, the
  bot sends an "no news" email instead of crashing.
- **RSS feeds** : some publishers occasionally return malformed XML; the bot
  logs them (`unreadable feed`) and continues with the others.
- **24h window, no persistence** : if a run is skipped (quota, outage), that
  day's articles are not caught up on the next run.

---

## Advanced customization

- **Different SMTP relay** : change `smtp_host` / `smtp_port` in `config.yaml`.
- **Digest size** : tune `triage.max_items` and `output.window_hours`.
- **Several watches** : create multiple `config-*.yaml` files and run the
  workflow with `VEILLE_CONFIG=config-science.yaml`.
