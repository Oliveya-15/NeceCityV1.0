# NeceCity - AI-Powered Urban Infrastructure Monitoring and Decision-Support System

NeceCity helps a city find, verify and prioritise infrastructure problems (potholes, road damage,
garbage, waterlogging, damaged road signs, open drains). A user uploads a street photograph, a
YOLOv8n model proposes what it sees, a person confirms it, and the system saves the problem on a
map with a risk score so the most dangerous problems are repaired first.

**Live app:** https://nece-city.vercel.app  |  **API docs:** https://nececity-backend.onrender.com/docs

## The four pages

| Page | What it does |
|---|---|
| **Dashboard** | Totals, severity / status / type charts, health score, top priorities, recent critical problems |
| **City Map** | Every problem on a map; filter by type, severity and status; click a marker for details |
| **Report Problem** | Upload a photo, see the detections, confirm / reject / edit them, draw a missed region or add a problem manually |
| **Priority List** | Problems ranked by risk score; move each one through Detected, Verified, In Progress, Resolved |

## Tools used

| Part | Tools |
|---|---|
| Front end | React 18.3, Vite 5.4, React Router 6.26, Tailwind CSS 3.4, Leaflet 1.9 (react-leaflet 4.2), Recharts 2.12, lucide-react 0.446 (icons), Node.js 20 |
| Back end | Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Uvicorn 0.30 |
| Database | PostgreSQL 16 |
| Machine learning | YOLOv8n trained with Ultralytics 8.3.28; run in the app with ONNX Runtime 1.19 |
| Hosting (free) | Vercel (front end), Render (back end), Neon (database), GitHub |

## Folder structure

```
nececity/
|-- backend/              the API (Python / FastAPI)
|   |-- app/
|   |   |-- main.py       starts the app and connects the routes
|   |   |-- config.py     settings (read from environment variables)
|   |   |-- database.py   database connection
|   |   |-- models.py     database tables
|   |   |-- schemas.py    shape of the data the API sends / receives
|   |   |-- enums.py      fixed lists: problem types, severities, statuses
|   |   |-- risk.py       the risk score formula (weights are here)
|   |   |-- geo.py        haversine distance
|   |   |-- seed.py       creates the demo data
|   |   |-- routes/       the API endpoints (one file per topic)
|   |   |-- services/     the real work behind the endpoints
|   |   `-- ml/           photo checks, ONNX model, severity suggestion
|   |-- tests/            automated tests
|   |-- requirements.txt
|   `-- .env.example
|-- frontend/             the website (React)
|   `-- src/ pages/ components/ hooks/ services/ utils/
|-- ml/                   training the model (not needed to run the app)
|   |-- data/real_dataset/   photos + labels
|   |-- train.py, evaluate.py, export_onnx.py
|   `-- weights/          nececity_yolo.pt  (+ you add nececity_yolo.onnx)
|-- HOW_IT_WORKS.md       explanation of every part (read this before your viva)
`-- README.md
```

---

## 1. Run it on your computer

You need: **Python 3.11**, **Node.js 20**, **PostgreSQL 16** and **Git**. (No Docker needed.)

### 1.1 Database

Install PostgreSQL from https://www.postgresql.org/download/ and remember the password you set for the
`postgres` user. Then open **SQL Shell (psql)** (or pgAdmin) and run:

```sql
CREATE DATABASE nececity;
CREATE DATABASE nececity_test;
```

### 1.2 The model file

Put your exported model at **`ml/weights/nececity_yolo.onnx`**. If you do not have it, create it:

```
cd ml
pip install -r requirements.txt
python export_onnx.py
```

Without this file the app still starts, but the Report Problem page shows "model not available"
(you can still add problems manually).

### 1.3 Backend

Open a terminal in the `backend` folder:

```
python -m venv .venv
.venv\Scripts\activate            (Mac/Linux:  source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            (Mac/Linux:  cp .env.example .env)
```

Open `backend/.env` and put your PostgreSQL password in `DATABASE_URL`:

```
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/nececity
```

Create the tables and the demo data, then start the server:

```
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Check http://localhost:8000/docs - you should see the API documentation.
To wipe everything and start again: `python -m app.seed --reset`.

### 1.4 Frontend

Open a second terminal in the `frontend` folder:

```
npm install
copy .env.example .env            (Mac/Linux:  cp .env.example .env)
npm run dev
```

Open http://localhost:5173. Choose **Siliguri** or **Kolkata** in the city selector (the other cities are
marked "Demo" and have no data).

### 1.5 Run the tests

In the `backend` folder (virtual environment active), tell the tests which database to use and run them:

```
set TEST_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/nececity_test
pytest
```
(PowerShell: `$env:TEST_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/nececity_test"`)

The tests erase the test database every time, so the name must end with `_test` (the tests refuse to run otherwise).
Expected result: **51 passed**.

---

## 2. Deploy it for free (Vercel + Render + Neon)

Order: **database -> back end -> front end**. Push the project to GitHub first
(`ml/weights/nececity_yolo.onnx` must be included, and no `.env` files).

### 2.1 Database - Neon

1. Sign in at https://neon.tech and create a project (or use your existing one).
2. **If this Neon database already has tables from the older NeceCity version**, remove them first.
   Open **SQL Editor** and run:
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   ```
   (Or simply create a new Neon project - that is the cleanest.)
3. Click **Connect**, turn **Connection pooling OFF**, and copy the connection string. It looks like
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require`.
4. Change the beginning to `postgresql+psycopg2://` - that is your `DATABASE_URL`.
   No PostGIS or extension is needed.

### 2.2 Back end - Render

New > Web Service > connect your GitHub repository, then:

| Setting | Value |
|---|---|
| Root Directory | (leave empty) |
| Runtime | Python 3 |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `cd backend && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

Environment variables:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.11.9` |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | your Neon string from step 2.1 |
| `CORS_ORIGINS` | `["https://nece-city.vercel.app"]` (your Vercel address, as a JSON list) |

`MODEL_PATH` is not needed (the default already points to `ml/weights/nececity_yolo.onnx`).

**If you already deployed the older version:** open the existing Render service, change the **Build Command**
and **Start Command** to the ones above (the old build used `requirements-deploy.txt`, which no longer exists),
delete the old `LLM_*`, `MODEL_USE_TTA` and `RISK_WEIGHT_*` variables, update `DATABASE_URL` if you made a new
Neon database, and click **Manual Deploy > Deploy latest commit**.

When it is live, open `https://YOUR-SERVICE.onrender.com/api/v1/health` (should show `"status":"ok"`) and
`.../api/v1/ml/status` (should show `"model_available": true`).

### 2.3 Front end - Vercel

New Project > import the repository, then:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite (detected automatically) |
| Environment variable | `VITE_API_BASE_URL` = `https://YOUR-SERVICE.onrender.com/api/v1` |

Deploy. If you already have the project, just push to GitHub - Vercel redeploys by itself.
Finally make sure `CORS_ORIGINS` on Render contains your exact Vercel address, with no slash at the end.

### 2.4 Things to know about the free tiers

- Render's free service **sleeps after 15 minutes**; the first request afterwards takes about a minute.
- Photos uploaded on Render are **deleted when the service restarts** (the free disk is temporary). The
  problem records stay in the database; only the picture disappears.
- Neon's free database pauses when idle and wakes up on the next request.

---

## 3. Problems and fixes

| Problem | Reason / fix |
|---|---|
| Top bar says the model is unavailable | `ml/weights/nececity_yolo.onnx` is missing (or not committed to GitHub). See 1.2. |
| Browser console shows a CORS error | `CORS_ORIGINS` does not contain your exact front-end address. |
| `password authentication failed` | The password in `DATABASE_URL` is wrong. |
| Render build fails: file not found | Build Command must be `pip install -r backend/requirements.txt` with an empty Root Directory. |
| Errors mentioning old tables or columns on Neon | The database still has the old schema. Wipe it (step 2.1.2). |
| Front end shows "Can't reach the backend" | `VITE_API_BASE_URL` is wrong, or Render is still waking up. Wait a minute and refresh. |
| `pytest` refuses to run | The test database name must end with `_test`. |

## 4. Limitations (be open about these)

- The model was trained on a **small dataset (30 photos)**, so it is a working proof of the pipeline, not a
  production-grade detector. That is why a person must confirm every detection.
- The demo problems in Siliguri and Kolkata are **generated sample data**, marked `is_demo`.
- There is **no login**: anyone who opens the site can use it.
- The risk weights are chosen by judgement, not learned from data.
