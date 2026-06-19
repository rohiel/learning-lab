# Deploying Anam's Learning Lab

One Docker image serves the API **and** the SPA, with SQLite on a persistent
volume. You need a host that **stays always-on**, because the nightly 8 PM job
pre-generates the next day's questions — a host that sleeps on idle would
silently skip it.

| Host | Persistent disk | Always-on | Verdict |
|---|---|---|---|
| **Railway** | Volume (any plan) | Yes | **Recommended** |
| Render | Disk (paid instances) | Paid only (free sleeps) | OK on a paid instance |

---

## Option A — Railway (recommended)

1. **Create the service.** New Project → *Deploy from GitHub repo* → pick this
   repo/branch. Railway detects the `Dockerfile` and builds it.
2. **Add a volume** for SQLite. Service → *Variables/Volumes* → add a Volume,
   mount path **`/data`** (the image defaults `DATABASE_URL` to
   `sqlite:////data/tutor.db`).
3. **Set environment variables** (Service → Variables):
   - `ANTHROPIC_API_KEY` = your key  *(required)*
   - `API_SHARED_SECRET` = a long random string  *(required)*
   - `SCHEDULER_TZ` = `America/New_York`  *(default; the nightly tz)*
   - `SCHEDULER_HOUR` = `20`  *(default)*
   - optionally `ANTHROPIC_MODEL` (default `claude-sonnet-4-6`)
   - Railway sets `PORT`; the image listens on 8000, so add
     `PORT=8000` **or** change the start command to `--port $PORT`.
4. **Deploy.** Health check path: `/api/health`.
5. **Custom domain.** Service → *Settings → Networking → Custom Domain* → enter
   your domain → Railway shows a **CNAME target** → add that CNAME at your DNS
   registrar. TLS is issued automatically.

## Option B — Render

1. New → *Web Service* → connect the repo → Runtime **Docker**.
2. Instance type: a **paid** tier (free spins down and the nightly job won't run).
3. *Disks* → add a disk mounted at **`/data`**.
4. Environment: same variables as above. Render provides `PORT` (default 10000),
   so set the **Docker Command** to
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (or set `PORT=8000`).
5. Health check path: `/api/health`.
6. *Settings → Custom Domains* → add your domain → create the shown CNAME at your
   registrar.

---

## After the first deploy

- A default student (**Anam**) is auto-created on first boot
  (`AUTO_SEED_STUDENT=true`, `DEFAULT_STUDENT_NAME`).
- **Prepare questions** — either wait for tonight's 8 PM run, or prep immediately:
  ```bash
  curl -X POST https://YOUR_DOMAIN/api/admin/seed \
    -H "X-API-Key: $API_SHARED_SECRET" -H "Content-Type: application/json" \
    -d '{"student_id":1,"days":[1,2,3]}'
  # or run the whole nightly batch now:
  curl -X POST https://YOUR_DOMAIN/api/admin/run-nightly -H "X-API-Key: $API_SHARED_SECRET"
  ```
- **Open the app** at `https://YOUR_DOMAIN/` — the SPA loads, reads the secret
  injected by the server, and talks to `/api` same-origin (no CORS needed).

## Notes

- **Backups:** the whole database is the single file on the `/data` volume. Copy
  it off periodically (Railway/Render let you download volume contents or run a
  one-off shell).
- **Rotating the secret:** change `API_SHARED_SECRET` and redeploy — the SPA
  picks it up at runtime (no rebuild). Anyone with an open tab will need to
  reload.
- **Postgres later:** set `DATABASE_URL` to a `postgresql+psycopg://…` URL and add
  `psycopg[binary]` to `backend/requirements.txt`; the models are already
  portable.
- **The shared secret is visible** to anyone who loads the page (it's a one-family
  gate, not strong auth). For real privacy, add a password→cookie login.
