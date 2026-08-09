# DEPLOY — Clow Landing (30-min go-live)

Ship the waitlist to production. Assumes you already own the `clow-tau.vercel.app` Vercel project.

## TL;DR — one command

### Full stack (backend + landing)
```bash
# One-time
curl -L https://fly.io/install.sh | sh   # flyctl
npm i -g vercel                           # vercel CLI
fly auth login
vercel login && vercel link

# Every deploy — Fly backend (3 services) + Vercel landing, sequenced
export API_TOKEN=$(openssl rand -hex 32)  # shared bearer across services
export SLACK_WEBHOOK=https://hooks.slack.com/...   # optional
PREFIX=myco- ./scripts/deploy_fullstack.sh
```

`PREFIX=myco-` prepends to Fly app names (`myco-gtm-engine`, `myco-security-agent`, `myco-evo-metaclaw`) because Fly names are globally unique — the defaults are almost certainly taken. Auto-creates apps + volumes + secrets, sets `GTM_ENGINE_URL`/`_TOKEN` on Vercel to wire the landing to the backend, then runs `smoke.sh` to confirm.

### Landing only (skip Fly backend)
```bash
SKIP_FLY=1 ./scripts/deploy_fullstack.sh    # → landing goes to Vercel; waitlist falls back to GitHub Issues (needs GH_TOKEN + GH_REPO)
# or directly:
./scripts/deploy_vercel.sh
```

### Backend only (skip Vercel)
```bash
SKIP_VERCEL=1 API_TOKEN=... ./scripts/deploy_fullstack.sh
```

Then read the sections below only if you're setting up for the first time, debugging, or picking specific pieces.

---

---

## 1. Files to publish (all in this repo)

```
clow_landing.html      # the landing page
api/waitlist.js        # POST endpoint — writes to Airtable
api/og.js              # dynamic OG image
vercel.json            # routing + security headers
```

## 2. Env vars (Vercel dashboard → Settings → Environment Variables)

The waitlist tries backends in this order and returns 200 on first success. **Both are OPTIONAL** — if neither is set, signups still return 200 (client-side Plausible + landing localStorage catch them, and you get real signal without any storage config).

### Option A — gtm-engine on Fly.io (recommended)
Full ICP scoring, deal pipeline, hot-lead Slack, KafCa events. Requires deploying the Rust backend first (§ 8).

| Key | Value |
|-----|-------|
| `GTM_ENGINE_URL` | `https://gtm-engine.fly.dev` (or your Fly hostname) |
| `GTM_ENGINE_TOKEN` | matches `API_TOKEN` you set on gtm-engine |

### Option B — GitHub Issues (zero-vendor fallback)
Each waitlist signup becomes one labeled issue in a repo you own. Free forever, auditable, exportable via GitHub's own tools. No third-party service.

| Key | Value |
|-----|-------|
| `GH_TOKEN` | Fine-grained PAT with `issues:write` scope on ONE repo. Create at [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new) |
| `GH_REPO` | `your-github/clow-waitlist` (recommended: dedicated private repo) |

Setup for Option B (60 seconds):
1. Create a private repo `clow-waitlist` (or reuse an existing one)
2. github.com/settings/personal-access-tokens/new → **Fine-grained**, only that repo, **Contents: read, Issues: read/write**
3. Paste the `github_pat_...` into `GH_TOKEN`
4. Deploy. Every signup becomes an issue with labels `waitlist`, `source:...`, `plan:...`

You can filter/export via GitHub's built-in issue search: `is:issue label:waitlist label:plan:pro`.

## 3. Add `@vercel/og` dep (only if you deploy `api/og.js`)

```bash
# In your Vercel project root
npm init -y   # if no package.json yet
npm i @vercel/og
```

## 4. Deploy

```bash
git pull                            # get this branch
cp clow_landing.html index.html     # OR keep the vercel.json rewrite — either works
vercel --prod
```

## 5. Verify (60 seconds)

- [ ] `https://clow-tau.vercel.app/` — landing loads <3s
- [ ] Submit test email → 200 → email visible in Airtable
- [ ] Fake email `not-an-email` → inline error, no network call
- [ ] `https://clow-tau.vercel.app/api/og` → PNG loads
- [ ] Paste `https://clow-tau.vercel.app` in a fresh X compose window → card renders with title + subtitle
- [ ] View source → CSP header present (DevTools → Network → response headers)

## 6. Kill switches (if things break)

| Symptom | Fix |
|---------|-----|
| Waitlist returns 200 but nothing lands in GH/gtm-engine | Env vars not set — check Vercel dashboard. `/api/waitlist` returns 200 by design even with no store (client-side Plausible still records the signal). |
| GitHub returns 401 | PAT expired or scope mismatch. Regenerate fine-grained token with `Issues: read/write` on the exact repo in `GH_REPO`. |
| GitHub returns 404 | `GH_REPO` typo — must be `owner/repo` exact form, case-sensitive. |
| GitHub returns 403 (rate limit) | 5000 req/hr on PATs; irrelevant unless you're testing in a loop. |
| gtm-engine returns 502 | Service asleep on Fly (auto_stop_machines). First request wakes it in ~2s; next requests are fast. |
| `/api/og` 500 | Missing `@vercel/og` dep. Run `npm i @vercel/og` and redeploy. |
| Waitlist form spins forever | Landing's offline localStorage queue already caught the email. Check `console.error` in Vercel logs. |
| X card renders text-only | OG image not resolving. Curl `/api/og` — expect 200 image/png. |

## 7. Post-deploy (Day 1)

1. Fire X Thread 1 from `X_THREADS.md` at 9am UTC via @XTech73781
2. Update Plausible domain to `clow-tau.vercel.app` (already in `<head>`)
3. Watch `airtable.com/appXXX/Waitlist` — first 100 signups get $7/mo Pro-for-life
4. Update `Clow_GTM_Blueprint.md` metrics dashboard end of Week 1

---

## 8. Backend layer (optional but recommended — Fly.io)

Deploy `clow-agents/backend/*` to Fly.io for real GTM automation. All optional — landing works without it (waitlist writes straight to Airtable). Fly `machines auto_stop` keeps idle cost at ~$0.

```bash
cd clow-agents/backend
fly deploy -c gtm-engine/fly.toml     -a gtm-engine
fly deploy -c security-agent/fly.toml -a security-agent
fly deploy -c evo-metaclaw/fly.toml   -a evo-metaclaw

# Verify all three at once
./scripts/smoke.sh   # locally
GTM=https://gtm-engine.fly.dev SEC=https://security-agent.fly.dev EVO=https://evo-metaclaw.fly.dev ./scripts/smoke.sh
```

**Env vars per service** (Fly secrets): copy from `.env.example`; at minimum set `API_TOKEN` (bearer) + `SLACK_WEBHOOK`.

**Wire waitlist → gtm-engine** (Vercel env, optional):
```
GTM_ENGINE_URL=https://gtm-engine.fly.dev
GTM_ENGINE_TOKEN=<same API_TOKEN as gtm-engine>
```
Failure is silent — Airtable still gets the row.

**Wire evo-metaclaw → SkillOpt worker** (Fly secrets for evo-metaclaw, optional):
```
SKILLOPT_WORKER_URL=http://<worker-fly-6pn-host>:9000
SKILLOPT_WORKER_TOKEN=<match WORKER_TOKEN on the Python worker>
```
Falls back to fitness-driven simulation if unset — evolution loop never blocks.

---

## 9. Ops dashboard

`dashboard.html` — single file, no build. Drop on any static host (Vercel, Netlify, GitHub Pages, or a `file://` open). Enter service URLs + bearer token once (stored in localStorage). Auto-refreshes every 30s. Shows: MRR forecast, top leads, deal pipeline by stage, security compliance, evolution leaderboard.

```bash
# Local
open dashboard.html   # macOS   |  xdg-open dashboard.html   # Linux

# Deploy alongside landing (Vercel serves both):
vercel --prod
# → https://clow-tau.vercel.app/dashboard.html
```

⚠️ **Never expose `dashboard.html` publicly without adding auth in front** — it holds your bearer token in localStorage. Vercel Password Protection, Cloudflare Access, or a `noindex,nofollow` meta + obscure path are the standard mitigations. `noindex` is already set in the file.

---

*Deploy checklist v1.1 · Ship in <30 min · KafCa mode · Backend + dashboard added*
