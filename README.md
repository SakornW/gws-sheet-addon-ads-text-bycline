# Google Sheet Ads Text Generator Add-on

A Google Sheet add-on that generates compelling ad text for products listed in a spreadsheet. The add-on uses Google's Gemini AI (with its integrated Google Search tool) to create tailored ad copy for Facebook. This add-on is built using HTTP endpoints (Alternate Runtimes) for Google Workspace.

## Project Overview

This add-on allows users to:
- Input product information in Google Sheets (name, description, specifications, CTA link)
- Generate ad text for selected products via a Card Service UI
- Customize generation parameters (tone, length)
- Preview and apply generated text back to the sheet

Under the hood, the add-on:
- Receives requests from Google Workspace at specified HTTP endpoints.
- Uses the Google Search tool within the Gemini API for contextual product information retrieval.
- Uses RAG (Retrieval-Augmented Generation) with Google Gemini to create compelling ad text.
- Stores product data and generation history in PostgreSQL.

## Architecture

- **Backend**: Python with FastAPI, serving HTTP endpoints for the Google Workspace Add-on.
- **Python Environment & Packaging**: `uv` with `pyproject.toml`.
- **Database**: PostgreSQL.
- **AI & Context Retrieval**: Google Gemini API (including its Google Search tool).
- **Google Sheet Integration**: Card Service UI (JSON defined by backend, rendered by Google).

## Changelog

### Planning Phase 2 (Latest)
- [x] Switched to Google Workspace Add-on with HTTP Endpoints (Alternate Runtimes).
- [x] Adopted `uv` for Python environment and package management.
- [x] Adopted `pyproject.toml` for dependency specification.
- [x] Decided to use Google Search tool within Gemini API for web context retrieval (replacing custom web scraping).

### Initial Setup (Previous Plan - Adapted)
- [x] Created basic project directory structure.
- [x] Set up Python package structure with proper `__init__.py` files.
- [x] Created FastAPI application setup (`app/main.py`).
- [x] Implemented configuration module (`app/core/config.py`), updated for `pydantic-settings`.
- [x] Set up security utilities (`app/core/security.py`).
- [x] Defined database models (`app/db/models.py`).
- [x] Implemented database session management (`app/db/session.py`).
- [x] Created CRUD operations (`app/db/crud.py`).
- [x] Implemented authentication endpoints (`app/api/auth.py`).
- [x] Created ad generation endpoints (`app/api/gws_router.py`), replacing `app/api/endpoints.py`.
- [x] Refactored `app/services/ai_service.py` to use Gemini's Google Search tool.
- [x] Removed `app/services/scraper_service.py`.
- [x] Set up Alembic for database migrations.
- [x] Created `Dockerfile` and `docker-compose.yml`.
- [x] Created `.env.example`.
- [x] Created `gsheet/manifest.json` for HTTP endpoints.
- [x] Successfully applied initial database migration.

### Pending Tasks

#### Core Backend & API
- [ ] Implement necessary OAuth 2.0 flow for backend communication if required by Google APIs.
- [ ] Refine Card Service JSON responses in `app/api/gws_router.py` to handle user input and display results effectively.
- [ ] Determine how to obtain sheet data in `app/api/gws_router.py`'s `/executeGenerateAds` endpoint (inspect request payload, client-side calls, or multi-step card process).

#### Google Workspace Add-on Configuration
- [ ] Test the add-on by deploying the backend and installing the add-on in Google Sheets.

#### Deployment
- [ ] Prepare deployment scripts/configuration for EKS.

#### Testing
- [ ] Write unit tests for backend logic.
- [ ] Implement integration tests for API endpoints (especially Card Service responses).
- [ ] Manually test the add-on within Google Sheets.

## Getting Started (with uv and pyproject.toml)

1.  **Install uv:**
    Follow the official instructions at [astral.sh/uv](https://astral.sh/uv) or use:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
    (For Windows, refer to the official `uv` documentation for installation.)

2.  **Create and Activate Virtual Environment:**
    Navigate to the project root directory.
    ```bash
    uv venv
    source .venv/bin/activate  # Linux/macOS
    # .venv\Scripts\activate  # Windows
    ```

3.  **Install Dependencies:**
    (Once `pyproject.toml` is created and populated)
    ```bash
    uv sync
    ```

4.  **Set up Environment Variables:**
    Copy `.env.example` to `.env` and fill in your details (DATABASE_URL, GEMINI_API_KEY, SECRET_KEY, GCP_OAUTH_CLIENT_ID etc.).
    The `DATABASE_URL` in `.env` should point to `postgresql://postgres:postgres@db:5432/adstext` when using Docker Compose, or `postgresql://postgres:postgres@localhost:5432/adstext` if running PostgreSQL locally for Alembic commands outside Docker.

5.  **Run Database (Docker Compose):**
    Ensure Docker Desktop is running.
    ```bash
    docker-compose up -d db
    ```
    Wait for the database to initialize (30-60 seconds).

6.  **Run Database Migrations:**
    ```bash
    # Ensure your .env file has DATABASE_URL pointing to localhost:5432 for this step if running outside docker,
    # OR run inside the app container:
    docker-compose run --rm app python -m alembic upgrade head
    ```

7.  **Run the Application (Development with Docker Compose):**
    ```bash
    docker-compose up app
    ```
    The application will be available at `http://localhost:8000`.

    Alternatively, to run directly with `uv` (after installing dependencies and ensuring DB is running):
    ```bash
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

## License

*License information will be added here*
