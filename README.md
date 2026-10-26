# AI Grant & Scholarship Finder

A student-facing scholarship search project with a React + Vite frontend and a Flask recommendation API. The frontend submits a student profile and optional search filters; Flask ranks eligible scholarships and returns up to ten matches by default.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer, with npm

## Run the backend

From the project root in PowerShell:

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
``

The first startup may download the NLTK resources used by the recommender. Keep the backend terminal running. By default, the API is available at `http://127.0.0.1:5000`.
The interactive Flask debugger is off by default. To enable it for local development only, set `$env:FLASK_DEBUG = "1"` before running `python app.py`.

## Run the frontend

Open a second terminal at the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://127.0.0.1:5173`.

## Port configuration

The frontend defaults to `http://127.0.0.1:5000/recommend`. If port 5000 is already in use, start Flask on another port:

```powershell
$env:PORT = "5001"
python app.py
```

Then create `frontend/.env.local` with:

```text
VITE_API_URL=http://127.0.0.1:5001/recommend
```

Restart the Vite server after changing its environment file.

## Recommendation details

The frontend sends a readable `query`, structured `profile`, and optional `filters` to `POST /recommend`. The backend filters clear mismatches for education level, gender, category, region, course area, special eligibility, income, and explicit age or marks limits. It then ranks eligible records using TF-IDF cosine similarity, with a profile-fit adjustment when matching structured profile details are available. Advanced search supports keywords, provider type, dataset-backed study-area and education-level filters, deadline state, and ranking by relevance or soonest deadline. `top_n` is configurable from 1 to 50. Requests containing only the legacy `query` value are still supported.

`GET /dashboard` returns the dataset total, deadline-state counts, the five nearest upcoming deadlines with their application and guidelines links, and the scholarship website directory. Scholarship records are maintained in `backend/scholarships.csv`; directory links and descriptions are maintained separately in `backend/scholarship_websites.csv`. Deadline states are calculated from the scholarship dataset's application start and deadline dates; "closing soon" means the deadline is within 14 days. The student profile is the initial page. All displayed profile fields are required before recommendations can be requested; special eligibility is not collected in the form. Recommendations are based on the completed profile, with optional advanced filters for keywords, provider, education level, deadline, or ranking. Selecting a dropdown filter immediately refreshes matches when the profile is complete; keyword searches are applied when the form is submitted. Course / branch is chosen once in the profile, without a second study-area picker. The website directory is loaded from the backend dataset. The optional home dashboard remains available from the navigation and displays deadline metrics, application links, and saved scholarships. Dashboard connection errors include a retry action.

Students can save or remove recommendation cards from a personal shortlist. The shortlist is stored in browser local storage on the current device and shown on the home dashboard; it is not synced to an account or another browser.

Scholarship records are maintained in `backend/scholarships.csv`; this project does not sync scholarship records or deadlines live with external portals. The profile page's external website links open the live portal pages, but the displayed recommendations and deadline information are only as current as the dataset. Confirm current rules, deadlines, and application availability on each provider's site. The displayed personalized match percentage combines text similarity and available profile matches; it is not a guarantee of eligibility or funding.

The dataset includes Post-Matric SC and ST scholarship entries with a maximum annual family income of INR 250,000. Income at the limit is allowed; higher income filters out those entries. Cards link to the National Scholarship Portal for applications and to the relevant ministry page for scheme details. State-level implementation rules may vary, so confirm them before applying.

## Run backend tests

From the project root in PowerShell:

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
```
