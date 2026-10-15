# FAS WUSL Timetable Downloader & Parser

A lightweight Python tool that automatically discovers and downloads the latest valid academic timetables for Levels 1, 2, 3, and 4 from the Faculty of Applied Sciences, Wayamba University of Sri Lanka ([FAS WUSL Timetables](https://fas.wyb.ac.lk/timetables/)), parses the PDF timetable grids into structured JSON sessions, tracks download metadata in a local manifest, and synchronizes timetable metadata with MongoDB Atlas.

## Features

- **Independent Level Discovery**: Evaluates Levels 1, 2, 3, and 4 independently across individual revision notices and multi-level batch notices.
- **In-Memory PDF Inspection**: Uses `pymupdf` to inspect the first-page text of each candidate PDF, accurately extracting academic level, academic year, semester, and revision rank without guessing from ambiguous filenames.
- **Cohesive Term Selection**: Guarantees that selected timetables belong to the newest active academic term (year and semester) and picks the most recent revision for each level.
- **Coordinate-Aware PDF Timetable Parser**:
  - Detects timetable grid boundaries and header columns (Monday–Friday).
  - Normalizes time slots to 24-hour `HH:MM` format.
  - Automatically excludes headers, lunch rows/cells, and lecturer lists on subsequent pages.
  - Splits multi-session cells into individual records.
  - Extracts subject codes, session types (`Lecture`, `Tutorial`, `Practical`), practical groups (`Gp. I`, `Gp. II`, etc.), and classroom locations (`LR- 07`, `MH`, `Mini Auditorium`, etc.).
  - Flags non-standard or ambiguous subject codes with `NEEDS_REVIEW` validation status.
  - Exports clean structured JSON files to `data/parsed/level-{level}.json`.
- **Automated Daily Production Worker**: Discovers new or revised timetables from the official website every 24 hours, computes SHA-256 digests in memory, validates parsed candidate sessions, and updates MongoDB Atlas.
- **Fail-Safe & Idempotent Synchronization**: If SHA-256 hashes match stored records, skips unnecessary database writes; if a PDF fails validation, previous working timetable records remain intact.
- **Guaranteed Temporary Artifact Cleanup**: Downloads candidate PDFs only into isolated temporary workspaces (`tempfile.TemporaryDirectory`) and deletes all files after processing, retaining zero permanent PDFs.
- **GitHub Actions Scheduled Worker**: Runs automatically via GitHub Actions cron schedule (`0 0 * * *` UTC) with concurrency control, secret masking, and failure alerting.
- **Vercel Full-Stack Compatibility**: Deploys the student-facing React frontend and read-only FastAPI API as a single unified service via Vercel serverless function routing.
- **Flexible CLI Options**: Supports `--worker` for production runs, `--dry-run` to preview selections, `--parse-only` to parse existing PDFs without downloading, and `--skip-mongodb` to run without database connectivity.

---

## Ubuntu Setup

### 1. Prerequisites

Ensure Python 3 (3.10+), `venv`, and `pip` are installed on your Ubuntu system:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 2. Virtual Environment & Dependency Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Environment Configuration

Configure your environment variables in the project root's `.env` file (refer to `.env.example`):

```bash
cp .env.example .env
```

Set the following variables in `.env`:

```env
# MongoDB Atlas Connection URI
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-address>/fas_timetable?retryWrites=true&w=majority

# Target Database name (defaults to 'fas_timetable' if omitted)
MONGODB_DATABASE=fas_timetable
```

> **Security Note**: Never commit `.env` to version control. The `.gitignore` file already excludes `.env` and local environment files.

### MongoDB Atlas Requirements

1. **Network Access**: Add your server or client IP address (or `0.0.0.0/0` with proper authentication) to the Atlas Network Access IP Access List.
2. **Database User Permissions**: Ensure the database user has `readWrite` permissions on the `fas_timetable` database.

---

## Usage

### 1. Production Timetable Worker (`worker.py` or `--worker`)

Executes the automated production worker: checks the official timetable page, computes SHA-256 hashes in memory, compares with MongoDB Atlas metadata, downloads changed PDFs into an isolated temporary workspace, validates sessions, synchronizes metadata and sessions to MongoDB, and deletes all temporary files:

```bash
# Run production worker
python worker.py
# Or: python -m src.worker
# Or: python downloader.py --worker

# Dry run: preview changes without writing to MongoDB
python worker.py --dry-run

# Force re-sync even if source hashes match
python worker.py --force

# Inspect specific levels
python worker.py --levels 1 2
```

### 2. Manual Run (Download to Disk + Parse + Manifest + MongoDB Sync)

Discovers the latest timetables, downloads PDFs into `downloads/`, parses the timetable sessions into `data/parsed/`, writes `metadata/manifest.json`, and synchronizes metadata with MongoDB Atlas:

```bash
python downloader.py
```

### 2. Parse Existing PDFs Only (`--parse-only`)

Parses the already downloaded PDFs in `downloads/` and exports structured session JSON files into `data/parsed/` without making network calls or connecting to MongoDB:

```bash
python downloader.py --parse-only
```

### 3. Dry Run (Preview Selections Only)

Inspects the website and candidate PDFs in memory without saving files, updating `manifest.json`, or contacting MongoDB:

```bash
python downloader.py --dry-run
```

### 4. Synchronize Parsed Sessions to MongoDB (`--sync-parsed-to-mongodb`)

Synchronizes the generated JSON files in `data/parsed/` directly into the `timetable_sessions` collection in MongoDB Atlas:

```bash
# Preview synchronization without making any database writes
python downloader.py --sync-parsed-to-mongodb --dry-run

# Perform live synchronization
python downloader.py --sync-parsed-to-mongodb
```

### 5. Skip MongoDB Synchronization

Performs discovery, local PDF downloads, parsing, and manifest generation, but skips connecting to MongoDB Atlas (useful for offline work or local testing without credentials):

```bash
python downloader.py --skip-mongodb
```

### 6. CLI Options

```text
usage: downloader.py [-h] [--parse-only] [--sync-parsed-to-mongodb]
                     [--dry-run] [--skip-mongodb]
                     [--output-dir OUTPUT_DIR] [--manifest MANIFEST]
                     [--parsed-dir PARSED_DIR] [--url URL]
                     [--max-pages MAX_PAGES] [-v]

options:
  -h, --help            Show this help message and exit
  --parse-only          Parse existing downloaded PDFs and export JSON without downloading or connecting to MongoDB
  --sync-parsed-to-mongodb
                        Synchronize existing parsed JSON session files from data/parsed/ to MongoDB Atlas
  --dry-run             Inspect notices and select candidates without downloading files or modifying manifest/database
  --skip-mongodb        Perform normal local download and manifest update, but skip MongoDB synchronization
  --output-dir OUTPUT_DIR
                        Directory to save downloaded PDF files (default: downloads)
  --manifest MANIFEST   Path for manifest.json (default: metadata/manifest.json)
  --parsed-dir PARSED_DIR
                        Directory to export parsed JSON files (default: data/parsed)
  --url URL             Base timetable listing page URL
  --max-pages MAX_PAGES Maximum pagination pages to crawl (default: 5)
  -v, --verbose         Enable debug logging
```

---

## Parsed Timetable Output Schema (`data/parsed/`)

Each level produces a structured JSON document:

```json
{
  "level": 1,
  "academic_year": "2024/2025",
  "semester": "Semester I",
  "revision": "Revised 02",
  "source_pdf": "level-1_2026-10-05.pdf",
  "source_sha256": "94061dc7442c115a05340835561bd164ea4024bea4226e85943c027c1e0003b7",
  "extraction_timestamp": "2026-10-15T21:06:30.039474+05:30",
  "sessions": [
    {
      "day": "Monday",
      "start_time": "08:30",
      "end_time": "09:30",
      "subject_code": "IMGT 1112",
      "session_type": "Lecture",
      "group": null,
      "location": "LR- 07",
      "raw_cell_text": "IMGT 1112 (L)\nLR- 07\nCMIS 1131 (P)\nGp. ll",
      "validation_status": "VALID",
      "warnings": []
    },
    {
      "day": "Monday",
      "start_time": "08:30",
      "end_time": "09:30",
      "subject_code": "CMIS 1131",
      "session_type": "Practical",
      "group": "Gp. ll",
      "location": null,
      "raw_cell_text": "IMGT 1112 (L)\nLR- 07\nCMIS 1131 (P)\nGp. ll",
      "validation_status": "VALID",
      "warnings": []
    }
  ],
  "warnings": [],
  "records_needing_review": 4,
  "total_sessions": 44
}
```

---

## Production Automation Workflow (GitHub Actions + MongoDB Atlas + Vercel)

The system provides fully automated, hands-off timetable synchronization running daily in GitHub Actions, backed by MongoDB Atlas and served through Vercel.

### Architecture Overview

```mermaid
flowchart TD
    Cron["Daily GitHub Actions Scheduler (00:00 UTC)"] --> Worker["Production Timetable Worker (src/worker.py)"]
    Manual["Manual Dispatch (workflow_dispatch)"] --> Worker
    Worker --> Scrape["Scrape Official Notices (fas.wyb.ac.lk)"]
    Scrape --> Inspect["Inspect PDF Bytes in Memory"]
    Inspect --> Select["Select Best Candidate per Level"]
    Select --> Compare{"SHA-256 matches Atlas?"}
    Compare -- "Yes (Unchanged)" --> Skip["Skip Level (0 DB Writes)"]
    Compare -- "No (New/Revised)" --> Temp["Download PDF to Isolated tempfile.TemporaryDirectory"]
    Temp --> Parse["Coordinate-Aware Timetable Grid Parser"]
    Parse --> Validate{"Candidate Validation Checks"}
    Validate -- "Fails" --> Revert["Reject Level (Old Atlas Data Preserved)"]
    Validate -- "Passes" --> SyncSess["Scoped Sync to timetable_sessions (Delete stale for level/term only)"]
    SyncSess --> SyncMeta["Update timetables metadata with new SHA-256"]
    SyncMeta --> Cleanup["Guaranteed Cleanup of All Temporary PDFs"]
    Revert --> Cleanup
    Skip --> Summary["Print Non-Sensitive Summary & Exit Status"]
    Cleanup --> Summary
    Atlas[("MongoDB Atlas")] <--> Worker
    Vercel["Vercel (Hosting)"] --> React["React + Vite Frontend (frontend/dist)"]
    Vercel --> Serverless["FastAPI Serverless Function (api/index.py)"]
    Serverless <--> Atlas
```

### Key Workflow Guarantees

1. **Automated Daily Trigger**: GitHub Actions runs the worker daily at `00:00 UTC` (`05:30 IST / Sri Lanka Time`) via `.github/workflows/timetable-sync.yml`.
2. **Change Detection via SHA-256**: The worker inspects candidate PDF bytes in memory and calculates SHA-256 checksums before touching the database. Unchanged timetables result in zero database writes and zero file downloads.
3. **Isolated Temporary Workspaces**: When a timetable changes, its PDF is written into an isolated `tempfile.TemporaryDirectory`. When processing completes (whether successful or on error), all temporary PDFs are completely removed from disk. No original timetable PDFs are ever retained permanently, committed to Git, or uploaded as workflow artifacts.
4. **Pre-Sync Validation Guard**: Candidate sessions undergo rigorous validation before production data is modified:
   - Minimum session count verification.
   - Required fields (`day`, `start_time`, `end_time`, `raw_cell_text`, `validation_status`).
   - Valid 24-hour time ranges (`start_time < end_time`, non-zero unparseable slots).
   - Weekday validity (Monday–Friday).
   - Duplicate slot conflict prevention.
5. **Atomic & Independent Level Processing**: Levels 1–4 are evaluated independently. If one level's PDF fails parsing or validation, its old working records in MongoDB Atlas remain untouched, while valid levels synchronize cleanly.
6. **Scoped Stale Session Pruning**: Obsolete timetable sessions are deleted only for the specific changed level and academic term matching `sourcePdfHash != new_hash`. Records for other levels or prior terms are never purged.

---

## GitHub Actions Configuration

### 1. Workflow Details (`.github/workflows/timetable-sync.yml`)
- **Schedule**: Cron `0 0 * * *` (UTC). Note that GitHub scheduled workflows may run with a slight delay depending on GitHub runner load.
- **Concurrency**: `group: timetable-sync, cancel-in-progress: false` ensures multiple runs never execute concurrently.
- **Job Timeout**: 15 minutes.
- **Permissions**: Minimal `contents: read`.

### 2. Manual Execution (`workflow_dispatch`)
To trigger the workflow manually without waiting for the daily cron:
- In your GitHub repository, navigate to **Actions** -> **FAS WUSL Daily Timetable Sync**.
- Click **Run workflow**.
- Optional inputs:
  - `force`: Force re-parsing and re-synchronizing even if SHA-256 matches.
  - `dry_run`: Preview change detection without modifying MongoDB Atlas.

Or via GitHub CLI:
```bash
gh workflow run timetable-sync.yml -f force=false -f dry_run=false
```

### 3. Required GitHub Repository Secrets & Variables

Configure these under **Settings** -> **Secrets and variables** -> **Actions**:

| Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `MONGODB_URI` | **Secret** | MongoDB Atlas connection string with readWrite permissions | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | **Variable** (Optional) | Target database name (defaults to `fas_timetable`) | `fas_timetable` |

---

## Vercel Deployment Setup

Vercel hosts the student-facing application and the compatible read-only FastAPI service as a single unified service deployed from the repository root.

### 1. Deployment Architecture

- **Deployment Root**: Repository Root (`./`). Both frontend assets and backend serverless endpoints must be deployed together from the repository root.
- **Frontend**: React + Vite static bundle built into `frontend/dist/` via `npm run build --prefix frontend`.
- **Backend API**: FastAPI ASGI application hosted as a Vercel Python Serverless Function via `api/index.py` (and root `index.py`).
- **Routing**: `vercel.json` routes all `/api/(.*)` and `/api` requests to `/api/index.py`, while rewriting all non-API paths to `/index.html` for client-side SPA routing (`/` and `/developers`).
- **Artifact Protection**: `.vercelignore` guarantees that local `.env` files, temporary PDFs in `downloads/`, Python test files, and local build artifacts are excluded from the deployment.

### 2. Exact Vercel Dashboard Project Settings

Configure these settings under **Project Settings** -> **General** on the Vercel Dashboard:

| Setting | Value | Notes |
| :--- | :--- | :--- |
| **Root Directory** | `./` (or leave empty) | **CRITICAL**: Do **NOT** set to `frontend`. Setting `frontend` isolates the build from `api/index.py` and `requirements.txt`. |
| **Framework Preset** | `Vite` (or `Other`) | Managed cleanly via `vercel.json`. |
| **Build Command** | `npm run build --prefix frontend` | If toggle is enabled, or leave toggle disabled to use `vercel.json`. |
| **Install Command** | `npm install --prefix frontend` | If toggle is enabled, or leave toggle disabled to use `vercel.json`. |
| **Output Directory** | `frontend/dist` | Points Vercel's edge network to the Vite production bundle. |

### 3. Root Cause Analysis: `frontend/frontend/package.json` Error

If the build log displays:
```text
npm error path /vercel/path0/frontend/frontend/package.json
ENOENT: no such file or directory, open '/vercel/path0/frontend/frontend/package.json'
Command "npm run build --prefix frontend" exited with 254
```
**Cause**: The Vercel Dashboard's **Root Directory** was set to `frontend`. When Vercel changed its working directory to `/vercel/path0/frontend`, executing `npm run build --prefix frontend` caused npm to look inside `/vercel/path0/frontend/frontend/package.json`.
**Solution**:
1. In Vercel Project Settings -> **General**, reset **Root Directory** to `./` (root).
2. The repository includes a root `package.json` and a root-aware `vercel.json` with explicit `installCommand` and `buildCommand`.

### 4. Required Vercel Environment Variables

Set these in the **Vercel Project Settings** -> **Environment Variables**:

| Variable | Environment | Description |
| :--- | :--- | :--- |
| `MONGODB_URI` | Production, Preview, Development | MongoDB Atlas connection URI for the read-only API. |
| `MONGODB_DATABASE` | Production, Preview, Development | Target database name (`fas_timetable`). |
| `CORS_ORIGINS` | Production, Preview | Optional comma-separated list of allowed origins. Defaults to matching all `*.vercel.app` domains. |
| `VITE_API_BASE_URL` | Production (Optional) | Public API base URL. Omit or leave empty when API and frontend share the same Vercel deployment. |

> **Security Warning**: Never expose `MONGODB_URI` in any `VITE_` variable or client-facing config. `VITE_` variables are bundled directly into public client JavaScript.

### 5. Verification After Deployment

Once deployed on Vercel, verify all layers:
1. **Frontend App**: Visit `https://<your-project>.vercel.app/` — verify student timetable grid and filters load.
2. **Developer Documentation**: Visit `https://<your-project>.vercel.app/developers` directly and refresh — verify no 404 error occurs and copyable Base URL displays `https://<your-project>.vercel.app/api`.
3. **API Health**: Visit `https://<your-project>.vercel.app/api/health` — should return `{"status": "ok", "database": "connected"}`.
4. **API Timetables**: Visit `https://<your-project>.vercel.app/api/timetables` — returns metadata array.
5. **Level 2 Sessions**: Visit `https://<your-project>.vercel.app/api/timetables/2/sessions` — returns session list.

---

## MongoDB Schema & Collections

- **Database**: `fas_timetable` (configured via `MONGODB_DATABASE`)

### 1. `timetables` Collection (Metadata)
Stores timetable-level metadata per academic term and level:
- **Unique Compound Index**:
  ```javascript
  db.timetables.createIndex(
    { level: 1, academicYear: 1, semester: 1 },
    { unique: true, name: "idx_level_academicYear_semester" }
  )
  ```
- **Document Fields**: `level`, `academicYear`, `semester`, `revision`, `publicationDate`, `sourcePdfUrl`, `noticeUrl`, `noticeTitle`, `downloadTimestamp`, `localPath`, `fileSize`, `sha256`, `updatedAt`.

### 2. `timetable_sessions` Collection (Parsed Sessions)
Stores atomic timetable sessions extracted from the coordinate-aware PDF grid:
- **Compound Unique Slot Index** (prevents duplicate session slots across runs):
  ```javascript
  db.timetable_sessions.createIndex(
    {
      level: 1,
      academicYear: 1,
      semester: 1,
      day: 1,
      startTime: 1,
      subjectCode: 1,
      group: 1
    },
    { unique: true, name: "idx_session_unique_slot" }
  )
  ```
- **Secondary Indexes**:
  ```javascript
  // Lookup by parent timetable ID
  db.timetable_sessions.createIndex({ timetableId: 1 }, { name: "idx_session_timetableId" })

  // Query sessions by academic period
  db.timetable_sessions.createIndex(
    { level: 1, academicYear: 1, semester: 1 },
    { name: "idx_session_level_term" }
  )
  ```
- **Document Fields**:
  - `timetableId`: ObjectId / reference string linking to the parent `timetables` record.
  - `level`: Academic level (1–4).
  - `academicYear`: e.g. `"2024/2025"`.
  - `semester`: e.g. `"Semester I"`.
  - `day`: Weekday name (`Monday` through `Friday`).
  - `startTime`: 24-hour normalized start time (`HH:MM`).
  - `endTime`: 24-hour normalized end time (`HH:MM`).
  - `subjectCode`: Extracted course code (e.g. `"CMIS 1113"` or `"ELPC 1+10"`).
  - `sessionType`: `"Lecture"`, `"Tutorial"`, `"Practical"`, or `null`.
  - `group`: Practical group identifier (e.g. `"Gp. I"`, `"Gp. ll"`), or `null`.
  - `location`: Lecture room or laboratory (e.g. `"LR- 07"`, `"ELTN Lab"`, `"Mini Auditorium"`).
  - `rawCellText`: Exact text extracted from the PDF cell for debugging and provenance.
  - `validationStatus`: `"VALID"` or `"NEEDS_REVIEW"`.
  - `warnings`: Array of parser warning messages explaining why a record was flagged.
  - `sourcePdfHash`: SHA-256 hash of the source PDF.
  - `updatedAt`: ISO 8601 timestamp of last synchronization.

---

## Student-Facing Web Application & Backend API

A complete full-stack web interface designed for university students and faculty, featuring a read-only FastAPI service and a responsive React + Vite + Tailwind CSS single-page application.

### Architecture & Features
- **Read-Only FastAPI Backend**: Serves verified timetable metadata and session records with CORS support and parameter validation. Reuses the existing MongoDB repository without exposing credentials or write operations.
- **Responsive React Frontend**:
  - **Level Selector**: Quick switching between Level 1, Level 2, Level 3, and Level 4.
  - **Dynamic Term Selection**: Academic Year and Semester dropdowns populated from database records.
  - **Weekly Grid View**: Monday–Friday timetable layout with time slots and color-coded session type badges.
  - **Mobile Daily View**: Responsive timeline view organized by time slots for each day.
  - **Search & Filter**: Real-time filtering by subject code prefix/keyword and session type (`Lecture`, `Practical`, `Tutorial`).
  - **Session Provenance Modal**: Click any session to inspect classroom location, practical group, raw cell text from PDF, and full verification notes.
  - **Visible NEEDS_REVIEW Indicator**: Never silently marks ambiguous entries as confirmed; visibly alerts users to non-standard course codes or missing annotations with detailed diagnostic notes.

---

## Starting the Application on Ubuntu

### 1. Start the Backend API

From the project root:

```bash
# Activate virtual environment
source .venv/bin/activate

# Start FastAPI server on port 8000
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be accessible at:
- **API Base URL**: `http://localhost:8000/api`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

### 2. Start the Frontend (Development)

From the project root:

```bash
cd frontend

# Install Node dependencies (first time only)
npm install

# Start Vite development server
npm run dev
```

The application will be live at `http://localhost:5173`.

### 3. Build the Frontend (Production)

```bash
cd frontend
npm run build
```

Production static assets will be generated in `frontend/dist/`.

---

## Backend API Specification

All endpoints are strictly read-only and return standardized JSON responses:

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | None | API & MongoDB Atlas connectivity status. |
| `GET` | `/api/timetables` | `level` (optional, 1–4) | List available timetables with publication & revision metadata. |
| `GET` | `/api/timetables/{level}/sessions` | `academicYear`, `semester`, `day`, `subjectCode` | Retrieve teaching sessions. Defaults to newest term if omitted. |
| `GET` | `/api/timetables/{level}/status` | `academicYear`, `semester` | Summary counts of `VALID` vs `NEEDS_REVIEW` sessions. |

---

## Project Structure

```text
fas-timetable-downloader/
├── .github/
│   └── workflows/
│       └── timetable-sync.yml   # Daily 24h GitHub Actions automation workflow
├── api/
│   └── index.py                 # Vercel Serverless Function entry point
├── src/
│   ├── api.py                   # FastAPI read-only web service with CORS
│   ├── cli.py                   # Command-line interface orchestrator
│   ├── config.py                # System constants and collection names
│   ├── downloader.py            # PDF download engine and SHA-256 calculator
│   ├── models.py                # Candidate and manifest Pydantic models
│   ├── mongodb_repository.py    # PyMongo Atlas repository (metadata & sessions)
│   ├── parser_models.py         # Session and timetable Pydantic models
│   ├── pdf_inspector.py         # In-memory PDF text analyzer
│   ├── scraper.py               # Notice scraper and HTML pagination parser
│   ├── selector.py              # Multi-level revision selection algorithm
│   ├── timetable_parser.py      # Coordinate-aware PDF grid parser
│   └── worker.py                # Safe production automation worker
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx           # University header & Atlas status badge
│   │   │   ├── FilterControls.jsx   # Level tabs, term selectors & search bar
│   │   │   ├── StatusSummary.jsx    # Revision badge & review metric counters
│   │   │   ├── WeeklyGrid.jsx       # Monday–Friday timetable matrix & lunch row
│   │   │   ├── DailyView.jsx        # Mobile-friendly chronological day timeline
│   │   │   ├── SessionCard.jsx      # Atomic session tile with type colors & badges
│   │   │   └── SessionModal.jsx     # Detailed provenance modal & raw text viewer
│   │   ├── services/
│   │   │   └── api.js               # Frontend HTTP API client
│   │   ├── App.jsx                  # Main application orchestrator
│   │   └── App.test.jsx             # Frontend Vitest test suite
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── tests/
│   ├── test_api.py                  # FastAPI endpoint unit tests
│   ├── test_manifest.py             # Manifest calculation tests
│   ├── test_mongodb_repository.py   # Mongo repository & sessions sync tests
│   ├── test_pdf_inspector.py        # PDF header inspection tests
│   ├── test_pdf_parser.py           # Parser & regression tests
│   ├── test_scraper.py              # HTML scraper & date parsing tests
│   ├── test_selector.py             # Selection algorithm tests
│   └── test_worker.py               # Worker & validation unit tests
├── data/parsed/                     # Local JSON exports per level
├── downloads/                       # Downloaded PDF timetables (manual runs only)
├── metadata/manifest.json           # File tracking manifest
├── .env                             # MongoDB Atlas credentials (never committed)
├── .env.example                     # Environment template
├── .vercelignore                    # Vercel deployment exclusions
├── downloader.py                    # Root CLI entry point
├── worker.py                        # Root production worker entry point
├── vercel.json                      # Vercel build & routing configuration
├── requirements.txt                 # Python dependencies
└── README.md                        # Documentation
```

---

## Troubleshooting & Workflow Logs

### 1. Inspecting GitHub Actions Execution
- Navigate to the **Actions** tab in GitHub and click the latest workflow run.
- Select the `Sync Timetables to MongoDB Atlas` job to view the console output.
- The step prints a structured summary table detailing:
  - Discovered target term
  - Levels checked
  - Unchanged levels (skipped without writes)
  - Synchronized levels with session counts and breakdown
  - Any failed levels with actionable diagnostic messages
  - Confirmation of temporary workspace cleanup

### 2. Common Scenarios & Resolutions
- **Database Connection Failure (`MongoRepositoryError`)**:
  - Verify that `MONGODB_URI` is correctly defined in GitHub repository secrets and Vercel environment variables.
  - Verify that your MongoDB Atlas IP Access List permits connections from GitHub Actions and Vercel (e.g. `0.0.0.0/0` with strong authentication).
- **Validation Failure (`Validation failed`)**:
  - If a university notice contains a corrupt table or 0 sessions, the worker rejects the candidate before writing to the database. Previous working timetable data for that level remains intact.
- **Workflow Status Codes**:
  - Exit code `0`: All levels are up-to-date or successfully synchronized.
  - Exit code `1`: One or more levels failed validation/parsing, or no notices were found on the website.
  - Exit code `2`: MongoDB Atlas connection failure.

---

## Running Automated Tests

### 1. Python Backend & Worker Tests (77 Tests)

Run the full Python test suite (covers scraper, PDF inspector, selection algorithm, manifest, coordinate-aware parser, regression cases, MongoDB Atlas repository, FastAPI endpoints, worker change detection, and validation guard):

```bash
python -m unittest discover -s tests -v
```

### 2. Frontend Vitest Tests (14 Tests)

Run the frontend test suite (covers loading states, API error and retry states, session rendering, unverified badge indicators, Friday lunch session visibility, empty search states, Developer API documentation page, copy actions, and client-side routing):

```bash
cd frontend
npm test
```

Or from repository root:
```bash
npm test
```
