<div align="center">

<img src="public/logo.png" alt="NeceCity" width="320"/>

### AI-assisted urban infrastructure monitoring & decision-support system
**Detect → verify → score → prioritise → track, all in one place**

[![License: MIT](https://img.shields.io/badge/License-MIT-FD6001?style=flat-square)](#-license)
![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20Tailwind-031D46?style=flat-square&logo=react&logoColor=white)
![Backend](https://img.shields.io/badge/Backend-FastAPI-031D46?style=flat-square&logo=fastapi&logoColor=white)
![Database](https://img.shields.io/badge/Database-PostgreSQL%20(Neon)-031D46?style=flat-square&logo=postgresql&logoColor=white)
![ML](https://img.shields.io/badge/Vision-YOLOv8%20%2B%20ONNX%20Runtime-031D46?style=flat-square&logo=onnx&logoColor=white)
![Maps](https://img.shields.io/badge/Maps-Leaflet%20%2B%20OpenStreetMap-031D46?style=flat-square&logo=leaflet&logoColor=white)
![Deployed](https://img.shields.io/badge/Deployed-Vercel%20%7C%20Render%20%7C%20Neon-031D46?style=flat-square&logo=vercel&logoColor=white)

**[🌐 Live App](https://nececityv1-0.vercel.app) · [⚙️ API Docs](https://nececityv1-0-backend.onrender.com/docs) · [📦 Repository](https://github.com/Oliveya-15/NeceCityV1.0)**

</div>

<br/>

> ⚠️ **NeceCity is an academic project, not an official municipal system.** The detection model was trained on a small dataset, so every detection must be confirmed by a person. The problems shown for Siliguri and Kolkata are **generated demo data**, not real records.

<br/>

## 📑 Table of Contents

- [🎯 The Problem](#-the-problem)
- [✨ What NeceCity Does](#-what-nececity-does)
- [📸 Screenshots](#-screenshots)
- [📷 How Detection Works](#-how-detection-works)
- [⚖️ The Explainable Risk Score](#️-the-explainable-risk-score)
- [🗺️ Duplicates, Distance & Lifecycle](#️-duplicates-distance--lifecycle)
- [🧠 The Detection Model](#-the-detection-model)
- [🧱 Architecture & Workflow](#-architecture--workflow)
- [🧰 Tech Stack](#-tech-stack)
- [🌍 Free Deployment Setup](#-free-deployment-setup)
- [🔗 Live Demo](#-live-demo)
- [⚡ Getting Started](#-getting-started)
- [🔧 Environment Variables](#-environment-variables)
- [🔌 API Overview](#-api-overview)
- [📁 Project Structure](#-project-structure)
- [🧪 Testing](#-testing)
- [⚠️ Honest Limitations](#️-honest-limitations)
- [🧭 Roadmap](#-roadmap)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

<br/>

---

## 🎯 The Problem

| | |
|---|---|
| **Reactive maintenance** | Potholes, garbage, waterlogging and open drains are usually noticed only after citizens complain or an accident happens, so repairs follow the loudest complaint instead of the biggest danger. |
| **No way to compare** | A pothole on a quiet lane and a pothole on a highway look the same on a complaint list. There is no repeatable, explainable way to say which should be repaired first. |
| **Duplicate reports** | The same problem is reported many times, which hides how long it has actually been ignored. |
| **Blind spots** | Without a map and simple statistics, clusters of problems and neglected areas stay invisible. |

**NeceCity's answer:** upload a street photograph, let a YOLOv8n model propose what it sees, confirm it as a person, and get a saved problem on a live map with an explainable risk score, a ranked priority list and a tracked path from *Detected* to *Resolved*.

<br/>

---

## ✨ What NeceCity Does

<p align="center"><img src="public/screenshot-dashboard.png" alt="NeceCity Dashboard" width="820"/></p>
<p align="center"><sub><strong>Dashboard</strong>: city health, breakdowns and the highest-priority problems at a glance</sub></p>

- 📊 **Dashboard:** totals, severity, status and type charts, an infrastructure health score and the top priorities of the selected city.
- 🗺️ **City Map:** every problem on an interactive Leaflet map, filtered by **type, severity and status**, with a detail panel (photo, confidence, risk reasons) for any marker.
- 📷 **Report Problem:** upload a street photo, see the detections as boxes with confidence values and a suggested severity, then **confirm, reject or edit** each one. Missed something? **Draw a box yourself** or **add the problem manually**. Pick the location with GPS or on a map.
- 📋 **Priority List:** problems ranked by an **explainable risk score**, with a recommended action, and one-click status changes through the lifecycle *Detected → Verified → In Progress → Resolved*.
- 🏙️ **Multi-city:** every city is a database row. Siliguri and Kolkata contain demo data; the other cities in the selector are tagged **Demo** so nobody mistakes an empty city for real data.
- 🧑‍⚖️ **Human in control:** nothing the model predicts becomes a stored problem until a person confirms it.
- 🟢 **Always-visible model status:** a badge in the top bar shows whether the model is loaded, on every page.
- 🛟 **Graceful degradation:** if the model file is missing the app still works, and problems can be added manually.
- 📱 **Responsive:** the whole app works on phones, so problems can be reported from the field.

<br/>

---

## 📸 Screenshots

<table>
<tr>
<td width="50%"><img src="public/screenshot-city-map.png" alt="City Map"/><p align="center"><sub><strong>City Map</strong>: filtered, colour-coded problems on a live map</sub></p></td>
<td width="50%"><img src="public/screenshot-report-problem.png" alt="Report Problem"/><p align="center"><sub><strong>Report Problem</strong>: detections with confidence, reviewed by a person</sub></p></td>
</tr>
<tr>
<td width="50%"><img src="public/screenshot-priority-list.png" alt="Priority List"/><p align="center"><sub><strong>Priority List</strong>: risk-ranked queue with status actions</sub></p></td>
<td width="50%" align="center"><img src="public/screenshot-mobile.png" alt="Report Problem on mobile" width="260"/><p align="center"><sub><strong>Mobile</strong>: reporting from a phone</sub></p></td>
</tr>
</table>

<br/>

---

## 📷 How Detection Works

<p align="center"><img src="public/workflow-diagram.png" alt="From photo to priority workflow" width="820"/></p>

Every uploaded photo walks the same pipeline, and a person always has the last word:

| # | Stage | What happens |
|---|---|---|
| 1 | **Validate** | File type (JPEG, PNG or WebP), size (up to 8 MB), image integrity and dimensions (64 to 8000 px per side) are checked with Pillow before anything is saved. |
| 2 | **Detect** | The project's own YOLOv8n model, exported to ONNX, runs on the server and finds up to 10 boxes of six classes: `pothole`, `road_damage`, `garbage`, `waterlogging`, `damaged_road_sign`, `open_drain`. |
| 3 | **Flag uncertainty** | Boxes below a minimum confidence are hidden. Boxes under 35 % are still shown but drawn dashed and marked **low confidence**, instead of being silently trusted. |
| 4 | **Suggest severity** | A simple documented rule (type weight and relative box size) pre-fills a severity. It is **not** a second AI model, and the reviewer can always change it. |
| 5 | **Human review** | The reviewer **confirms, rejects or edits** each detection, draws a region the model missed, or adds a problem manually. |
| 6 | **Save or merge** | A confirmed detection becomes a **Problem**. If an unresolved problem of the same type is within **30 m**, its recurrence count increases instead of creating a duplicate. |
| 7 | **Score** | The risk engine calculates the explainable score and a recommended action. |

**Severity suggestion:** `severity score = 0.6 × type weight + 0.4 × box size`, where box size is the box area as a fraction of the photo times 6 (maximum 1). A score of 0.75 or more is *critical*, 0.55 *high*, 0.35 *medium*, otherwise *low*.

<br/>

---

## ⚖️ The Explainable Risk Score

Priority is never a hidden number. Each problem gets a **0 to 100 score** from four weighted factors, saved together with plain-language reasons.

```
score = 100 × ( 0.40 × severity + 0.25 × recurrence + 0.20 × density + 0.15 × road importance )
```

| Factor | Weight | How the 0 to 1 value is made |
|---|---|---|
| **Severity** | 0.40 | low 0.25 · medium 0.50 · high 0.75 · critical 1.00 |
| **Recurrence** | 0.25 | times the problem was reported ÷ 5 (maximum 1) |
| **Density** | 0.20 | other unresolved problems within **150 m** ÷ 6 (maximum 1) |
| **Road importance** | 0.15 | local 0.30 · arterial 0.70 · highway 1.00 |

| Score | Recommended action |
|---|---|
| **80 and above** | Immediate action, repair within 24 to 48 hours |
| **60 to 79** | High priority, repair within 7 days |
| **40 to 59** | Moderate priority, next routine cycle (within 30 days) |
| **Below 40** | Low priority, monitor |

**Worked example:** a *high* severity problem, reported 3 times, with 2 others nearby, on an *arterial* road gives `30.0 + 15.0 + 6.7 + 10.5 = 62.2`, which means *high priority*. The reasons shown on the page ("Recurring issue - detected 3 times at this location") are generated by the same function, so the explanation always matches the number.

The weights live in **one file** (`backend/app/risk.py`), are checked to add up to 1 at start-up, and are easy to tune. They are chosen by judgement, not learned from data.

<br/>

---

## 🗺️ Duplicates, Distance & Lifecycle

| Topic | How it works |
|---|---|
| **Distance** | Measured in metres with the **haversine formula** on latitude and longitude. The database first keeps only problems inside a small square around the point, then the exact distance of each one is calculated. No GIS extension is needed. |
| **Duplicate merge** | An unresolved problem of the **same type** within **30 m** is treated as the same problem: its recurrence count goes up, the higher severity is kept, and the risk score is recalculated. |
| **Density** | The number of other unresolved problems within **150 m** feeds the risk score. |
| **Lifecycle** | `Detected → Verified → In Progress → Resolved`, one step at a time. A jump such as *Detected → Resolved* is rejected by the API. A problem confirmed by a person starts as *Verified*. |
| **Health score** | The Dashboard starts at 100 and subtracts a penalty for every open problem (low 5, medium 15, high 30, critical 50, averaged and scaled by how many are open). 80+ is *Good*, 60+ *Fair*, 40+ *Poor*, otherwise *Critical*. |

<br/>

---

## 🧠 The Detection Model

| | |
|---|---|
| **Architecture** | YOLOv8n (nano), trained with Ultralytics 8.3.28 |
| **Method** | Transfer learning: started from COCO-pretrained weights and trained further on our own labelled photos |
| **Production format** | ONNX, run with ONNX Runtime (no PyTorch on the server, so it fits a 512 MB free tier) |
| **Input / output** | 640 × 640 input, output tensor of shape 1 × 10 × 8400 (4 box values + 6 class scores for 8400 candidates) |

**Training data** (`ml/data/real_dataset`): 30 hand-labelled photos (24 for training, 6 for validation) with 65 boxes.

| Class | Photos | Boxes |
|---|---|---|
| pothole | 7 | 21 |
| road_damage | 10 | 11 |
| garbage | 9 | 10 |
| waterlogging | 5 | 7 |
| damaged_road_sign | 6 | 11 |
| open_drain | 5 | 5 |

**On the server**, for every photo `onnx_runtime.py` does four things: *letterbox* the photo to 640 × 640 without stretching, run the model, *decode* the raw output into boxes, and apply *non-maximum suppression* (IoU 0.45) to remove duplicate boxes. Boxes are returned as fractions (0 to 1) of the original photo so the browser can draw them at any size.

**Train it yourself:** open `ml/NeceCity_Training_Colab.ipynb` in Google Colab (free GPU) or follow [`ml/README.md`](ml/README.md). Run `python evaluate.py` to get precision, recall and mAP for your trained model. With only six validation photos, those numbers are indicative, not conclusive.

> 💡 The biggest improvement comes from **more labelled photos** (100+ per class) and **"negative" photos** (clean roads, trees, plants) so the model learns what *not* to flag.

<br/>

---

## 🧱 Architecture & Workflow

<p align="center"><img src="public/architecture-diagram.png" alt="System architecture" width="820"/></p>

NeceCity is a **modular monolith**: one backend process, one database and one frontend build, with every concern in its own folder so any part can be read, tested or replaced on its own.

| Layer | Responsibility |
|---|---|
| `routes/` | Thin HTTP handlers: receive the request, return JSON |
| `services/` | The real work: save photos, run the model, merge duplicates, change status, build the city summary |
| `ml/` (backend) | Photo checks, ONNX model runner, severity suggestion, detector that loads the model once |
| `risk.py` · `geo.py` | The risk formula and the haversine distance, kept free of web and database code so they are easy to test |
| `models.py` · `schemas.py` | Database tables and the exact shape of API requests and responses |
| `frontend/src/` | React pages, shared components, a city context and **one** API client (`services/api.js`) |

**Design principles:**

- **No fake AI.** Every confidence value is real model output, every score comes from a documented formula, and when something is unavailable the app says so.
- **Human review.** The model suggests; a person decides.
- **Graceful degradation.** A missing model file never crashes the app.
- **Free-tier realism.** ONNX Runtime and a small dependency list keep the backend light.

<br/>

---

## 🧰 Tech Stack

<table>
<tr><th>Layer</th><th>Technology</th></tr>
<tr><td>Frontend</td><td>React 18.3 · Vite 5.4 · React Router 6.26 · Tailwind CSS 3.4 · Leaflet 1.9 with react-leaflet 4.2 · Recharts 2.12 · lucide-react (icons) · Node.js 20</td></tr>
<tr><td>Backend</td><td>Python 3.11 · FastAPI 0.115 · SQLAlchemy 2.0 · Pydantic · Uvicorn 0.30</td></tr>
<tr><td>Database</td><td>PostgreSQL 16 (Neon in production)</td></tr>
<tr><td>Computer Vision</td><td>YOLOv8n (Ultralytics 8.3.28) for training · ONNX Runtime 1.19 for inference · Pillow · NumPy</td></tr>
<tr><td>Maps</td><td>Leaflet with OpenStreetMap tiles</td></tr>
<tr><td>Testing</td><td>pytest against a real PostgreSQL test database</td></tr>
<tr><td>Deployment</td><td>Vercel (frontend) · Render (backend) · Neon (database) · GitHub</td></tr>
</table>

**No paid service is required anywhere in this stack.** The database, hosting, maps and model inference all run free.

<br/>

---

## 🌍 Free Deployment Setup

| Part | Host | Why |
|---|---|---|
| Frontend | **Vercel** | Free static hosting, auto-deploys from GitHub, SPA rewrite rule in `vercel.json` |
| Backend | **Render** (free web service, 512 MB) | Runs FastAPI straight from the repository |
| Database | **Neon** (free PostgreSQL) | Render's free Postgres expires after 30 days, Neon's free tier does not |

**Key engineering decisions:**

- **ONNX instead of PyTorch.** The training stack needs far more than 512 MB of memory just to import. The trained model is exported once to ONNX and served with ONNX Runtime, which fits the free tier.
- **Tables are created automatically** when the backend starts, and the seed script adds the demo data only if the database is empty.
- **Secrets stay out of Git.** `.env` files are ignored; production values are set as environment variables on Render and Vercel.

### Step-by-step

Deploy in this order: **database → backend → frontend → fix CORS**. Before you start, check that `ml/weights/nececity_yolo.onnx` is in the repository and that no `.env` file is.

**1. Database (Neon)**

1. Create a project at https://console.neon.tech (Postgres 16).
2. Click **Connect**, switch **Connection pooling OFF** and copy the connection string.
3. Change the beginning to `postgresql+psycopg2://` and remove `&channel_binding=require` if present. This is your `DATABASE_URL`.

**2. Backend (Render)** · New + → Web Service → select the repository:

| Setting | Value |
|---|---|
| Root Directory | *(empty)* |
| Runtime | Python 3 |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `cd backend && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

Environment variables: `PYTHON_VERSION=3.11.9`, `ENVIRONMENT=production`, `DATABASE_URL=<your Neon string>`, `CORS_ORIGINS=["http://localhost:5173"]` (temporary).
Check `/api/v1/health` and `/api/v1/ml/status` (it must show `"model_available": true`).

**3. Frontend (Vercel)** · Add New → Project → select the repository:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite |
| Environment variable | `VITE_API_BASE_URL=https://<your-render-service>.onrender.com/api/v1` |

**4. Connect them.** In Render, change `CORS_ORIGINS` to your exact Vercel address as a JSON list, for example `["https://nececityv1-0.vercel.app"]` (no slash at the end), and save.

> ⏳ The backend is on Render's free tier, so the first request after about 15 minutes of inactivity can take up to a minute to wake up. Photos uploaded on the live site are removed when the free service restarts, while the problem records stay in the database. That is infrastructure, not a bug.

<br/>

---

## 🔗 Live Demo

| | |
|---|---|
| 🌐 **App** | [nececityv1-0.vercel.app](https://nececityv1-0.vercel.app) |
| ⚙️ **API docs** | [nececityv1-0-backend.onrender.com/docs](https://nececityv1-0-backend.onrender.com/docs) |
| 📦 **Source** | [github.com/Oliveya-15/NeceCityV1.0](https://github.com/Oliveya-15/NeceCityV1.0) |

> 🏙️ Choose **Siliguri** or **Kolkata** in the city selector; they contain demo data. The other cities are tagged **Demo** and are empty. No account is needed.

<br/>

---

## ⚡ Getting Started

**Requirements:** Python 3.11, Node.js 20, PostgreSQL 16 and Git. No Docker is needed.

### 1. Clone

```bash
git clone https://github.com/Oliveya-15/NeceCityV1.0.git
cd NeceCityV1.0
```

### 2. Database

Install PostgreSQL, remember the password of the `postgres` user and create two databases (the second is only for tests):

```sql
CREATE DATABASE nececity;
CREATE DATABASE nececity_test;
```

### 3. Model file

Put your exported model at `ml/weights/nececity_yolo.onnx` (see [The Detection Model](#-the-detection-model) to train and export it). Without it the app still runs, but the top bar shows "Model not trained" and only manual entry works.

### 4. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS / Linux: cp .env.example .env
```

Open `backend/.env` and put your PostgreSQL password into `DATABASE_URL`, then create the demo data and start the server:

```bash
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs to see the API. To wipe everything and start again, run `python -m app.seed --reset`.

### 5. Frontend

In a second terminal:

```bash
cd frontend
npm install
copy .env.example .env            # macOS / Linux: cp .env.example .env
npm run dev
```

Open http://localhost:5173.

<br/>

---

## 🔧 Environment Variables

**Backend** (`backend/.env`, or Render's Environment tab)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection (`postgresql+psycopg2://...`). For Neon add `?sslmode=require`. |
| `CORS_ORIGINS` | JSON list of website addresses allowed to call the API |
| `MODEL_PATH` | Path to the ONNX model, relative to `backend/` (default `../ml/weights/nececity_yolo.onnx`) |
| `MODEL_MIN_CONFIDENCE` | Boxes below this confidence are hidden (default `0.10`) |
| `MODEL_CONFIDENCE_THRESHOLD` | Boxes below this are marked "low confidence" (default `0.35`) |
| `MODEL_IOU_THRESHOLD` | Overlap limit used to remove duplicate boxes (default `0.45`) |
| `MODEL_MAX_DETECTIONS` | Maximum boxes per photo (default `10`) |
| `MAX_UPLOAD_SIZE_MB` | Upload size limit (default `8`) |
| `ENVIRONMENT` | `development` or `production` |

**Frontend** (`frontend/.env`, or Vercel's Environment Variables)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend address ending in `/api/v1` |

Every backend variable is documented in `backend/.env.example`. **No secrets are committed.**

<br/>

---

## 🔌 API Overview

Interactive documentation is generated by FastAPI at `/docs`. All routes are under `/api/v1`.

| Method and path | Purpose |
|---|---|
| `GET /cities` · `GET /cities/{id}/summary` | City list and the Dashboard numbers |
| `GET /map/problems` | Problems for the map, filtered by type, severity and status |
| `GET /problems` · `GET /problems/{id}` | Paginated list and full detail with the risk score |
| `POST /problems/manual` | Add a problem without the model |
| `PATCH /problems/{id}/status` | Move a problem one step along the lifecycle |
| `POST /analyze/image` | Upload a photo and run the detector |
| `POST /detections/{id}/verify` | Confirm or reject a detection |
| `POST /detections/user-region` | Add a box the user drew |
| `GET /priorities` | Problems ordered by risk score |
| `GET /ml/status` · `GET /health` | Model status and health check |

<br/>

---

## 📁 Project Structure

```
NeceCityV1.0/
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── main.py           starts the app, connects the routes
│   │   ├── config.py         settings from environment variables
│   │   ├── database.py       database engine and sessions
│   │   ├── models.py         database tables
│   │   ├── schemas.py        API request / response shapes
│   │   ├── enums.py          problem types, severities, statuses
│   │   ├── risk.py           the risk formula (weights live here)
│   │   ├── geo.py            haversine distance
│   │   ├── seed.py           demo data generator
│   │   ├── routes/           one file per topic
│   │   ├── services/         city, problem and detection logic
│   │   └── ml/               photo checks, ONNX runner, severity suggestion
│   ├── tests/                automated tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 React application
│   └── src/ pages/ components/ hooks/ services/ utils/
├── ml/                       model training (not needed to run the app)
│   ├── data/real_dataset/    labelled photos
│   ├── train.py  evaluate.py  export_onnx.py  prepare_dataset.py
│   ├── NeceCity_Training_Colab.ipynb
│   └── weights/              nececity_yolo.pt and nececity_yolo.onnx
├── public/                   README images
├── HOW_IT_WORKS.md           file-by-file explanation of the whole project
└── README.md
```

<br/>

---

## 🧪 Testing

The backend has **50+ automated tests** that run against a real PostgreSQL test database, so queries and merging behave exactly as in production.

| Area | What is checked |
|---|---|
| Risk score | Weights add up to 1, minimum and maximum scores, reasons, components add up to the score |
| Distance | Haversine accuracy and the bounding box |
| ML helpers | Severity suggestion, photo validation, box decoding, non-maximum suppression, detector without a model file |
| API | Duplicate merge within 30 m, status order (409 on a jump), priorities sorted by risk, map filters, upload and review flow |

```bash
cd backend
set TEST_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/nececity_test
pytest
```

(PowerShell: `$env:TEST_DATABASE_URL="..."`.) The tests erase the test database every time, so its name must end with `_test`, otherwise they refuse to run.

<br/>

---

## ⚠️ Honest Limitations

- **Small training set.** The model learned from 30 photos, so it is a working proof of the pipeline, not a production detector. It can miss problems and produce false alarms (for example plants flagged as garbage). That is exactly why a person must confirm every detection.
- **Demo data is generated.** The problems in Siliguri and Kolkata are sample data marked `is_demo`.
- **No login.** Anyone who opens the site can use it.
- **Risk weights are hand-picked,** not learned from real maintenance outcomes.
- **Temporary photo storage on the free host.** Uploaded photos disappear when Render restarts; the database records stay.
- **Cold starts.** The free backend sleeps when idle and takes up to a minute to wake.

<br/>

---

## 🧭 Roadmap

- [ ] Authentication and roles (citizen, reviewer, municipal officer)
- [ ] A larger labelled dataset, including negative photos, and a re-trained model
- [ ] Real data for more cities
- [ ] Permanent photo storage (object storage)
- [ ] Assign problems to municipal departments, with notifications
- [ ] Video and dashcam analysis
- [ ] Instance segmentation for the real size of a defect
- [ ] Predictive risk: where problems are likely to appear next

<br/>

---

## 📄 License

Released under the [MIT License](LICENSE). Use and adapt it freely for learning and portfolios.

<br/>

## 🙏 Acknowledgments

- **Ultralytics** for YOLOv8, and the **ONNX Runtime** team
- **OpenStreetMap** contributors and **Leaflet** for the maps
- **FastAPI**, **SQLAlchemy**, **React**, **Vite**, **Tailwind CSS**, **PostgreSQL** and the wider open-source community
- **Prof. Surojit Roy**, our project guide, and the Department of MCA, Techno Main, Salt Lake

<br/>

<div align="center">

**Designed, built, trained and deployed end to end on free-tier infrastructure.**

<sub>NeceCity V1.0 · Oliveya Choudhury & Akanksha Jaiswal · 2026</sub>

</div>
