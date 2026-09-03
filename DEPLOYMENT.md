# Deployment

Two pieces, deployed separately: the **backend** (FastAPI, does the actual simulation) on
[Render](https://render.com), and the **frontend** (Vite/React, static site) on
[Vercel](https://vercel.com). Both have a free tier sufficient for this project. Both steps below
require logging into your own account and connecting this GitHub repo — that part can't be done
from here, only prepared.

## 1. Backend on Render

1. Go to [render.com](https://dashboard.render.com), sign in (GitHub login is easiest), and
   click **New > Blueprint**.
2. Connect the `VaGlar/Greenhouse-Digital-Twin` repo. Render will detect `render.yaml` at the
   repo root and propose a service named `greenhouse-digital-twin-api` — accept it.
3. Leave `FRONTEND_ORIGINS` blank for now (it's optional — Vercel's own `*.vercel.app` domains
   are already allowed automatically, see step 4).
4. Deploy. First build takes a few minutes (installs `requirements.txt`). Once live, note the
   URL Render gives you — something like `https://greenhouse-digital-twin-api.onrender.com`.
5. Sanity check: open `<that URL>/health` in a browser — should return `{"status":"ok"}`.

**Free tier note**: Render's free web services spin down after 15 minutes of inactivity and take
~30-60s to wake back up on the next request — the frontend's first `/simulate` call after a quiet
period will just look slow once, not broken.

## 2. Frontend on Vercel

1. Go to [vercel.com](https://vercel.com/new), sign in (GitHub login is easiest), and import the
   same `VaGlar/Greenhouse-Digital-Twin` repo.
2. Vercel will ask for a **Root Directory** — set it to `frontend` (this repo is not a
   frontend-only repo, the Vite app lives in that subfolder). It should then auto-detect the
   Vite framework preset with no further config needed.
3. Before deploying, add an environment variable: **`VITE_API_BASE`** = the Render URL from step
   1.4 above (e.g. `https://greenhouse-digital-twin-api.onrender.com`, no trailing slash).
4. Deploy. Vercel gives you a URL like `https://greenhouse-digital-twin.vercel.app`.

## 3. Confirm the two are talking to each other

Open the Vercel URL, wait for the config to load (confirms the `/config` GET call reached the
Render backend), then run a short simulation (e.g. 10 days) to confirm `/simulate` (POST) works
end-to-end. If the config never loads, open the browser console — a CORS error there means
`FRONTEND_ORIGINS` on Render needs the exact Vercel URL added (comma-separated if more than one),
though this shouldn't be necessary since `*.vercel.app` is already allowed.

## After this

- **Every push to `main`** (or whatever branch each service is set to track) auto-redeploys both
  sides — no further manual steps.
- **Pull requests** get their own preview URLs on both Vercel and Render by default, useful for
  reviewing a change before merging.
- If a custom domain is added later, set it in Vercel's project settings and add it to
  `FRONTEND_ORIGINS` on Render (the `*.vercel.app` regex won't match a custom domain).
