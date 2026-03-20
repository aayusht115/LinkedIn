# LinkedIn AI Features Prototype

A full-stack prototype simulating LinkedIn's hiring platform with AI-powered features for candidates and recruiters. Built for the DPM (Data Product Management) course — Term 3.

---

## Features

| Feature | Who | How |
|---|---|---|
| Recruiter Score | Candidate | ML model (LinearRegression) scores a recruiter by response time, hire rate, rating, and cancellations |
| Job Fit Score | Candidate | Keyword matching between your skills and job requirements |
| Interview Scheduling | Recruiter | Schedule interviews with auto-generated meeting links, stored in SQLite |
| Post Summarization | Recruiter | Qwen2.5-0.5B LLM condenses any LinkedIn post into one sentence |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> Note: `torch` and `transformers` are large packages (~2 GB). The LLM model (~1 GB) downloads automatically on the first `/summarize` request.

### 2. Run the server

```bash
python app.py
```

By default the server starts in production mode (debug off). To enable debug/auto-reload during development:

```bash
FLASK_DEBUG=true python app.py
```

### 3. Open the app

| URL | Page |
|---|---|
| http://127.0.0.1:5000/ | Candidate UI |
| http://127.0.0.1:5000/candidate | Candidate UI |
| http://127.0.0.1:5000/recruiter | Recruiter UI |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FLASK_DEBUG` | `false` | Set to `true` to enable debug mode and auto-reload |
| `ALLOWED_ORIGIN` | `http://127.0.0.1:5000` | CORS allowed origin (set to your deployed domain in production) |

---

## API Reference

### `POST /schedule`
Schedule an interview.

**Body:**
```json
{ "candidate": "Alice", "recruiter": "Bob", "time": "2026-04-01T10:00", "job_id": "optional" }
```

**Returns:** The created interview record (201).

---

### `GET /interviews?page=1&per_page=20`
List all interviews with pagination.

**Returns:**
```json
{ "interviews": [...], "page": 1, "per_page": 20, "total": 42, "pages": 3 }
```

---

### `GET /interviews/<id>`
Fetch a single interview by ID. Returns 404 if not found.

---

### `GET /recruiter_score/<recruiter_id>`
Get an ML-based quality score for a recruiter.

Known IDs: `rec_shopify_001`, `rec_stripe_002`, `rec_deepmind_003`, `rec_amazon_006`, `rec_openai_011` (and more in `data/recruiter_data.csv`). Unknown IDs return a score based on dataset average.

**Returns:** `{ "score": 88.5 }`

---

### `POST /summarize`
Summarize a LinkedIn post using the Qwen2.5 LLM.

**Body:** `{ "text": "your post content here" }`

**Returns:** `{ "summary": "One-sentence summary." }`

> The model loads on the first request (~30-60 seconds). Subsequent requests are fast.

---

## Project Structure

```
codebase/
├── app.py                  # Flask server and routes
├── database.py             # SQLite CRUD + schema
├── interview_scheduler.py  # Interview creation logic
├── recruiter_score.py      # ML scoring (LinearRegression)
├── summarizer.py           # LLM summarization (lazy-loaded)
├── templates/
│   ├── candidate_ui.html   # Candidate-facing UI
│   └── recruiter_ui.html   # Recruiter-facing UI
├── data/
│   └── recruiter_data.csv  # Training data for ML model
├── interviews.db           # SQLite database (auto-created)
└── requirements.txt
```
