# Sophía Study Platform

A two-role study platform with **Sophía design language**, FastAPI backend, Firebase Auth + Firestore (content), and Firebase Data Connect / Cloud SQL (user profiles).

---

## Quick Start

### 1. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com) → New Project
2. Enable **Authentication** → Email/Password
3. Enable **Firestore** → Start in production mode
4. Enable **Firebase Data Connect** → Create a Cloud SQL for PostgreSQL instance
5. Go to Project Settings → Service Accounts → **Generate new private key** → save as `backend/serviceAccountKey.json`
6. Go to Project Settings → Your apps → Add Web App → copy the config object

### 2. Backend Setup

```bash
cd backend

# Copy env template
copy .env.example .env
# Edit .env — fill in ADMIN_SIGNUP_KEY and DATABASE_URL

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --port 8000
```

Swagger docs available at: http://localhost:8000/docs

### 3. Frontend Setup

Edit `frontend/js/auth.js` — replace the `firebaseConfig` placeholder with your actual values from Firebase Console.

Then serve the frontend. Easiest option — **VS Code Live Server** (right-click `index.html` → Open with Live Server).

Or use Python:
```bash
cd frontend
python -m http.server 5500
```

Open: http://localhost:5500

---

## Environment Variables (backend/.env)

| Variable | Description |
|---|---|
| `ADMIN_SIGNUP_KEY` | Secret key required to create admin accounts |
| `FIREBASE_CREDENTIALS_PATH` | Path to your `serviceAccountKey.json` |
| `CORS_ORIGIN` | Frontend origin for CORS (default: `*`) |

---

## Project Structure

```
ap/
├── backend/                  FastAPI server
│   ├── main.py               App entry point
│   ├── config.py             Env var loader
│   ├── database.py           SQLAlchemy (Cloud SQL)
│   ├── firebase_admin_setup.py  Firebase Auth + Firestore
│   ├── dependencies.py       Auth + role guards
│   ├── models/
│   │   ├── sql_models.py     User table (PostgreSQL)
│   │   └── schemas.py        All Pydantic schemas
│   ├── routers/              One file per route group
│   ├── services/
│   │   ├── scoring.py        Attempt scoring + leaderboard
│   │   └── timer.py          Server-side time validation
│   └── requirements.txt
│
└── frontend/                 Vanilla HTML/CSS/JS
    ├── index.html            Sophía landing page
    ├── css/
    │   ├── sophía.css       Design tokens, shapes, grid
    │   ├── sidebar.css       Sidebar navigation
    │   └── components.css    Buttons, cards, forms, modals
    ├── js/
    │   ├── auth.js           Firebase Auth SDK + guards
    │   ├── api.js            Fetch wrapper + token attach
    │   ├── theme.js          Dark/light toggle
    │   ├── sidebar.js        Sidebar renderer + scroll reveal
    │   └── sophía.js        Geometric SVG renderer
    └── admin/                Admin-only pages
```

---

## Data Architecture

Everything is in **Firestore** — no SQL, no Data Connect.

| Collection | Purpose |
|---|---|
| `users/{uid}` | User profiles (name, username, email, role, theme_pref) |
| `topics/{id}` | Topics |
| `notes/{id}` | Notes (Markdown content) |
| `questions/{id}` | Question bank |
| `tests/{id}` | Tests (question IDs, timer, thresholds) |
| `attempts/{id}` | Test attempts (answers, scores) |
| `leaderboard/{uid}` | Leaderboard entries (totalNormalizedScore, rank) |

The **Firebase UID** (from Firebase Auth) is the document ID in `users/`. This links the Auth identity to the Firestore profile without any SQL join.

---

## Security Notes

- All protected routes require a Firebase ID token (`Authorization: Bearer <token>`)
- Role is verified server-side from Cloud SQL — never trusted from the frontend
- `correctAnswer` is stripped from test data before sending to users
- `startedAt` is stored server-side — client clock manipulation is rejected
- Admin signup key is an env var — never stored in DB or sent to frontend

---

## Deployment (GitHub + Render)

The project is structured to deploy automatically using **Render Blueprints** defined in `render.yaml`. This deploys the frontend as a static site and the backend as a Python web service.

### Step 1: Push code to GitHub

1. Initialize git (if not already done):
   ```bash
   git init
   ```
2. Commit your code:
   ```bash
   git add .
   git commit -m "Configure deployment scripts and settings"
   ```
3. Add the remote and push to your repository:
   ```bash
   git remote add origin https://github.com/Nitish080706/aptitude_platform.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy on Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository (`aptitude_platform`).
4. Under the Blueprint configuration:
   - Render will detect the `render.yaml` file and automatically define the **backend** and **frontend** services.
   - You will be prompted to enter values for the following environment variables:
     - **`ADMIN_SIGNUP_KEY`**: Your secret key for creating admin accounts.
     - **`FIREBASE_CREDENTIALS_JSON`**: The content of your Firebase service account JSON key. You can paste the raw JSON string directly, or encode it as Base64.
       - *To encode it as Base64 on Windows PowerShell:*
         ```powershell
         [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("backend/serviceAccountKey.json"))
         ```
5. Click **Apply**. Render will start deploying both services.

### Step 3: Link Frontend and Backend

Once the deployment completes:
1. Copy the URL of your deployed backend service (e.g. `https://aptitude-platform-backend.onrender.com`).
2. Update the `RENDER_BACKEND_URL` in [frontend/js/config.js](file:///n:/ap/frontend/js/config.js) to match your backend URL.
3. Copy the URL of your deployed frontend service (e.g. `https://aptitude-platform-frontend.onrender.com`).
4. Update the `CORS_ORIGINS` environment variable in your Backend service settings on Render to match your frontend URL.
5. Commit and push the changes:
   ```bash
   git add frontend/js/config.js
   git commit -m "Update production backend URL"
   git push
   ```
   Render will automatically redeploy the frontend with the correct settings!

