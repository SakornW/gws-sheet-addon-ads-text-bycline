# Google Sheet Ads Text Generator Add-on

A Google Sheet add-on that generates compelling ad text for products listed in a spreadsheet. The add-on uses Google's Gemini AI (with its integrated Google Search tool) to create tailored ad copy. This add-on is built using HTTP endpoints (Alternate Runtimes) for Google Workspace.

## Project Overview

This add-on allows users to:
- Input product information in Google Sheets.
- Trigger ad generation via a Card Service UI.
- Specify the data range, header row, output column, and generation parameters (tone, length).
- Have generated ad text and reference data written directly back to their sheet.

Under the hood, the add-on:
- Receives requests from Google Workspace at specified HTTP endpoints.
- Obtains the Sheet ID from the event object.
- Uses the Google Sheets API (with user's OAuth token) to read header and row data.
- Infers column meanings from header names.
- Uses the Google Search tool within the Gemini API for contextual product information retrieval.
- Uses RAG (Retrieval-Augmented Generation) with Google Gemini to create compelling ad text and reference data.
- Writes the results directly back to the specified columns in the Google Sheet using the Sheets API.
- Stores product data and generation history in a PostgreSQL database.

## Architecture

- **Backend**: Python with FastAPI, serving HTTP endpoints for the Google Workspace Add-on.
- **Python Environment & Packaging**: `uv` with `pyproject.toml`.
- **Database**: PostgreSQL.
- **AI & Context Retrieval**: Google Gemini API (including its Google Search tool).
- **Google Sheet Integration**: Card Service UI (JSON defined by backend, rendered by Google) for input, direct data write-back via Sheets API.

## System Context Diagram

This diagram shows how the "GWS Sheet Add-on Ads Text" system interacts with external users and systems.

```mermaid
graph LR
    User[User via Google Sheets Add-on] -- Interacts --> GWSAddonSystem[GWS Sheet Add-on Ads Text System]
    GWSAddonSystem -- Reads/Writes Data --> GoogleSheetsAPI[Google Sheets API]
    GWSAddonSystem -- Requests Ad Generation --> AIService[AI Text Generation Service]
    GWSAddonSystem -- Stores/Retrieves User Data --> Database[Application Database]

    style User fill:#D6EAF8,stroke:#333,stroke-width:2px
    style GoogleSheetsAPI fill:#A9DFBF,stroke:#333,stroke-width:2px
    style AIService fill:#FADBD8,stroke:#333,stroke-width:2px
    style Database fill:#FCF3CF,stroke:#333,stroke-width:2px
    style GWSAddonSystem fill:#E8DAEF,stroke:#333,stroke-width:4px
```

**Explanation of Context Diagram:**

*   **User (via Google Sheets Add-on)**: The primary actor who uses the add-on within Google Sheets to generate ad text.
*   **GWS Sheet Add-on Ads Text System**: The core application we are analyzing.
*   **Google Sheets API**: The system interacts with this API to read input data from sheets and write the generated ad text back.
*   **AI Text Generation Service**: An external or internal service that the system calls to perform the actual ad text generation based on provided inputs and prompts.
*   **Application Database**: Used by the system to store user information, authentication details, and potentially other application-specific data.

## Architecture Overview Diagram

This diagram illustrates the internal components of the "GWS Sheet Add-on Ads Text System".

```mermaid
graph TD
    subgraph GWSAddonSystem [GWS Sheet Add-on Ads Text System]
        direction LR
        subgraph PresentationLayer [Presentation Layer - Google Workspace UI]
            direction TB
            GWSManifest["gsheet/manifest.json"]
            GWSCards["app/core/gws_cards/*_card.py (Homepage, Ad Generation Form)"]
        end

        subgraph APILayer [API Layer - FastAPI Backend]
            direction TB
            MainApp["app/main.py (FastAPI App)"]
            AuthRouter["app/api/auth.py (User Auth, Tokens)"]
            GWSRouter["app/api/gws_router.py (Add-on Event Handlers, Ad Logic)"]
            Config["app/core/config.py"]
            Security["app/core/security.py"]
        end

        subgraph ServiceLayer [Service Layer]
            direction TB
            AIServiceClient["app/services/ai_service.py (AI Model Interaction)"]
            Prompts["app/prompts/*_template.txt"]
        end

        subgraph DataAccessLayer [Data Access Layer]
            direction TB
            GoogleAPIClient["app/utils/google_api_clients.py (Sheets API Calls)"]
            SheetUtils["app/utils/sheets_utils.py (Sheet Data Helpers)"]
            DBSession["app/db/session.py"]
            CRUD["app/db/crud.py"]
            DBModels["app/db/models.py"]
        end

        PresentationLayer -- HTTP Requests --> APILayer
        APILayer -- Calls --> ServiceLayer
        ServiceLayer -- Uses --> Prompts
        APILayer -- Uses --> DataAccessLayer
        DataAccessLayer -- Interacts --> ExternalGoogleSheets["Google Sheets API"]
        DataAccessLayer -- Interacts --> ExternalDB["Application Database"]
        ServiceLayer -- Calls --> ExternalAIService["AI Text Generation Service"]
    end

    style PresentationLayer fill:#D6EAF8,stroke:#333,stroke-width:2px
    style APILayer fill:#A9DFBF,stroke:#333,stroke-width:2px
    style ServiceLayer fill:#FADBD8,stroke:#333,stroke-width:2px
    style DataAccessLayer fill:#FCF3CF,stroke:#333,stroke-width:2px
    style ExternalGoogleSheets fill:#A9DFBF,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style ExternalAIService fill:#FADBD8,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style ExternalDB fill:#FCF3CF,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

**Explanation of Architecture Overview:**

1.  **Presentation Layer (Google Workspace UI)**:
    *   Defined by `gsheet/manifest.json`, which configures the add-on.
    *   The UI elements (cards for homepage, ad generation form) are dynamically generated by Python scripts in `app/core/gws_cards/`. These cards are rendered within the Google Sheets environment.

2.  **API Layer (FastAPI Backend)**:
    *   The core of the backend, built with FastAPI (`app/main.py`).
    *   `app/api/auth.py`: Handles user registration, login, and access token management.
    *   `app/api/gws_router.py`: Contains crucial endpoints triggered by user interactions in the Google Sheets Add-on (e.g., opening the homepage, submitting the ad generation form). It orchestrates the ad generation process.
    *   `app/core/config.py` and `app/core/security.py` provide configuration and security utilities respectively.

3.  **Service Layer**:
    *   `app/services/ai_service.py`: This component is responsible for the business logic related to AI. It takes input, loads appropriate prompts (from `app/prompts/`), and interacts with an AI text generation service to produce ad copy.

4.  **Data Access Layer**:
    *   `app/utils/google_api_clients.py`: Contains functions to directly communicate with the Google Sheets API (e.g., to read data from selected ranges or write generated ads back).
    *   `app/utils/sheets_utils.py`: Provides helper functions for processing sheet data, like parsing A1 notation.
    *   `app/db/`: This sub-directory (session.py, crud.py, models.py) manages all database interactions, primarily for user data and authentication.

**Interactions:**

*   The **User** interacts with the **Presentation Layer** (Google Sheets Add-on UI).
*   The **Presentation Layer** sends HTTP requests to the **API Layer**.
*   The **API Layer** (specifically `gws_router.py`) processes these requests. For ad generation:
    *   It uses the **Data Access Layer** (`google_api_clients.py`) to fetch data from Google Sheets.
    *   It calls the **Service Layer** (`ai_service.py`) to generate ad text.
    *   The **Service Layer** interacts with an external **AI Text Generation Service**.
    *   Finally, the **API Layer** uses the **Data Access Layer** again to write the results back to Google Sheets.
*   The **API Layer** (`auth.py`) also uses the **Data Access Layer** (`app/db/*`) to manage user authentication against the **Application Database**.

The application is designed to be containerized using Docker, as indicated by the `Dockerfile` and `docker-compose.yml`.

## User Interaction Flow & Endpoints

1.  **Homepage (`/gws/homepage`):**
    *   User opens the add-on.
    *   A simple card is displayed with a "Generate Ads" button.

2.  **Generate Ads Form (`/gws/generateAdsForm`):**
    *   Triggered by the "Generate Ads" button on the homepage.
    *   Presents a form card with the following inputs:
        *   "Data Rows Range (e.g., Sheet1!A2:D100)" (Required)
        *   "Header Row Number (e.g., 1)" (Required)
        *   "Output Starting Column Letter (e.g., E):" (Required)
        *   "Tone:" (Optional, with a default)
        *   "Max Ad Length:" (Optional, with a default)
    *   A "Generate & Write Ads" button on this form calls the `/gws/generateAndWriteAds` endpoint.

3.  **Process and Write Ads (`/gws/generateAndWriteAds`):**
    *   Receives form inputs and the Sheet ID (from the event object).
    *   Reads header row and data rows from the sheet using Sheets API.
    *   For each data row, creates a dictionary mapping header names to cell values.
    *   Calls the AI service (`generate_batch_ads_with_search`) with this structured data.
    *   The AI service returns generated ad text and reference data (e.g., search queries used).
    *   Writes the ad text and reference data directly back to the sheet in columns starting from the "Output Starting Column Letter".
    *   Returns a success/failure notification card.

## Changelog

### Planning Phase 3 (Latest - Direct Write-back)
- [x] Refined user input to a single form for data range, header row, output column, and generation parameters.
- [x] Decided to infer column meanings from header names rather than explicit mapping.
- [x] Planned for direct write-back of results to the sheet, removing intermediate results card.
- [x] Confirmed Sheet ID is available in the event object for relevant triggers.
- [x] Resolved token verification issues (audience claim, service account email).
- [x] Migrated to the new `google-genai` SDK.
- [x] Implemented Sheets API calls to read header and data rows within `/gws/generateAndWriteAds`.
- [x] Parsed sheet data based on headers.
- [x] Updated `app/services/ai_service.py` to accept row data as `Dict[str, str]` and for its prompt to infer meaning from headers.
- [x] Updated `ai_service` to return reference/strategy data along with ad text.
- [x] Corrected `Tuple` import in `app/api/gws_router.py`.

### Previous Milestones
- [x] Switched to Google Workspace Add-on with HTTP Endpoints.
- [x] Adopted `uv` and `pyproject.toml`.
- [x] Decided to use Google Search tool within Gemini API.
- [x] Basic project structure, FastAPI setup, DB models, CRUD, Auth, Alembic.
- [x] `Dockerfile` and `docker-compose.yml` created.
- [x] Initial database migration applied.
- [x] `gsheet/manifest.json` for HTTP endpoints created and refined.

### Pending Tasks

#### Core Backend & API
- [x] Implement the `/gws/generateAdsForm` endpoint to return the detailed input card. (Assumed complete as per previous steps, card structure is defined)
- [x] Implement the `/gws/generateAndWriteAds` endpoint:
    - [x] Extract form inputs and Sheet ID.
    - [x] Implement Sheets API calls to read header and data rows.
    - [x] Parse sheet data based on headers.
    - [x] Update `app/services/ai_service.py` to accept row data as `Dict[str, str]` and for its prompt to infer meaning from headers. (Completed)
    - [x] Update `ai_service` to return reference/strategy data along with ad text. (Completed)
    - [x] Implement Sheets API calls to write ad text and reference data back to the sheet. (Completed for ad_text, reference data write-back can be a future enhancement if needed beyond notification)
    - [x] Return a success/failure notification card. (Implemented)
- [x] Update `gsheet/manifest.json` to include `https://www.googleapis.com/auth/spreadsheets` scope for write access. (This is crucial for the write-back functionality to work)

#### Google Workspace Add-on Configuration
- [x] Test the full end-to-end flow by deploying the backend and installing the add-on in Google Sheets.

#### Deployment & Testing
- [ ] Prepare deployment scripts/configuration (e.g., for EKS).
- [ ] Write unit and integration tests.

## Getting Started (with uv and pyproject.toml)

1.  **Install uv:**
    Follow the official instructions at [astral.sh/uv](https://astral.sh/uv).

2.  **Create and Activate Virtual Environment:**
    ```bash
    uv venv
    source .venv/bin/activate  # Linux/macOS
    # .venv\Scripts\activate  # Windows
    ```

3.  **Install Dependencies:**
    ```bash
    uv sync
    ```

4.  **Set up Environment Variables:**
    Copy `.env.example` to `.env` and fill in your details (DATABASE_URL, GEMINI_API_KEY, SECRET_KEY, GCP_OAUTH_CLIENT_ID, SERVICE_ACCOUNT_EMAIL).

5.  **Run Database (Docker Compose):**
    ```bash
    docker-compose up -d db
    ```

6.  **Run Database Migrations:**
    ```bash
    docker-compose run --rm app python -m alembic upgrade head
    ```

7.  **Run the Application (Development with Docker Compose):**
    ```bash
    docker-compose build app # Rebuild if code changes
    docker-compose up app
    ```
    The application will be available at `http://localhost:8000`. Use `ngrok http 8000` to get a public HTTPS URL for testing the add-on.

## License

*License information will be added here*
