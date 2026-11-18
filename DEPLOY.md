# Deploying Vision Cart to Vercel

One Vercel project hosts everything:

| Part | Where it lives | How Vercel serves it |
|---|---|---|
| Web UI | `public/` | Static files from the CDN (fast, free of function cost) |
| API | `app/main.py` (`app = FastAPI`) | One Python Vercel Function, auto-detected |
| Config | `vercel.json`, `requirements.txt`, `.python-version` | Read at build time |

No build command, no output directory, no Docker.

## 1. Before you deploy
- [ ] `pytest -q` passes locally (`pip install -r requirements-dev.txt` first).
- [ ] You have a Gemini API key: <https://aistudio.google.com/apikey>.
- [ ] `python -m scripts.list_models` shows the model names your key can use. The defaults in `.env.example` (`gemini-3.6-flash`, `gemini-3.6-flash-image`) are unverified for your account: set `GEMINI_MODEL` / `GEMINI_IMAGE_MODEL` to names from that list.
- [ ] `.env` is **not** committed (it is in `.gitignore`).
- [ ] In Google AI Studio / Cloud, set a **monthly budget or quota cap** for the key. Each listing makes 1-2 model calls and each set of related pictures makes 3 more.

## 2. Deploy from GitHub (recommended)
```bash
git init && git add . && git commit -m "Vision Cart 1.2"
git branch -M main
git remote add origin https://github.com/<you>/vision-cart.git
git push -u origin main
```
1. <https://vercel.com/new> → import the repository.
2. Framework preset: **FastAPI** (auto-detected). Leave build/output/install commands empty.
3. **Environment Variables** (apply to Production *and* Preview):

| Name | Value | Notes |
|---|---|---|
| `GEMINI_API_KEY` | your key | Required. Mark as *Sensitive*. |
| `GEMINI_MODEL` | from `list_models` | Optional |
| `GEMINI_IMAGE_MODEL` | from `list_models` | Optional; if wrong, only the AI pictures are unavailable |
| `ENABLE_DOCS` | `false` | Hides `/docs`, `/redoc`, `/openapi.json` in production |
| `RATE_LIMIT_PER_MINUTE` | `20` | Per client, per instance. `0` disables |
| `ENABLE_IMAGE_GENERATION` | `true` / `false` | Turn off to save cost |

4. Click **Deploy**.

### CLI alternative
```bash
npm i -g vercel
vercel login
vercel                       # preview deployment (links the project)
vercel env add GEMINI_API_KEY production
vercel --prod
```

## 3. Verify the deployment
1. `https://<your-app>.vercel.app/health` → `{"status":"ok"}`
2. Open the site, add 1-3 photos of one product → listing appears, then full description, then 3 AI visuals.
3. Response headers on `/` include `Content-Security-Policy` and `Strict-Transport-Security` (browser dev tools → Network).
4. Vercel dashboard → **Logs**: you should see JSON lines (`request_completed`, with `request_id`). No keys or image data are logged.

## 4. Harden it (do this before sharing the link widely)
- **Firewall rate limit:** Vercel dashboard → *Firewall* → add a rule: path starts with `/api/` and method `POST` → *Rate limit* (for example 10 requests per minute per IP). This is the hard cap; the in-app limiter is only per instance.
- **Deployment Protection:** if the app is for a team or client demo, enable *Vercel Authentication* or password protection under *Settings → Deployment Protection*.
- **Spend cap** on the Gemini key (see checklist above).
- **Custom domain:** *Settings → Domains*. Vercel provisions TLS automatically.
- **Spend monitoring:** Vercel *Usage* tab plus the Google AI Studio usage dashboard.

## 5. Limits you should know
- **Request body: 4.5 MB** per function call (platform limit). The web UI compresses photos in the browser to stay under 3.8 MB in total. Direct API clients must do the same.
- **Function duration:** `vercel.json` sets `maxDuration` to 120 s, which fits the app's own 110 s request deadline. Hobby plans allow up to 300 s with Fluid Compute (default for new projects); lower the value if your plan caps it.
- **Cold starts:** the first request after idle can be slower (importing the Gemini SDK). Subsequent requests reuse the warm instance.
- **Stateless:** nothing is stored. Listings live only in the browser until the user copies or downloads them.

## 6. Troubleshooting
| Symptom | Likely cause / fix |
|---|---|
| Build fails on dependencies | Check Python is 3.12 (`.python-version`) and `requirements.txt` has not been replaced by the dev file. |
| `503 vision_misconfigured` | Wrong/missing `GEMINI_API_KEY`, or a model name your key can't use. Fix the env var and **redeploy** (env changes apply to new deployments only). |
| `500` on first request, logs mention settings | `GEMINI_API_KEY` missing for that environment (Production vs Preview). |
| "photos are too large to upload" | Browser could not fit photos under the 4.5 MB limit; use fewer photos. |
| `429 rate_limited` | In-app limiter or your Firewall rule. Wait and retry, or raise `RATE_LIMIT_PER_MINUTE`. |
| AI pictures say "not available" | `GEMINI_IMAGE_MODEL` is wrong for your key, or the quota is exhausted. The listing itself still works. |
| `504` after ~2 minutes | Gemini was slow; try again, fewer photos, or turn off AI pictures. |
| iPhone photos rejected | HEIC is not readable by browsers. Use *Settings → Camera → Formats → Most Compatible*, or export as JPEG. |

## 7. Updating
Push to `main` → Vercel builds and promotes automatically. Pull requests get preview URLs. Use *Instant Rollback* in the dashboard if a release misbehaves.
