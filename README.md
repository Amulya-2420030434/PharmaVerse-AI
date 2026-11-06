# PharmaVerse AI
### Intelligent Pharmaceutical Supply Chain Traceability & Anti-Counterfeit Platform

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-19-61DAFB)
![Vite](https://img.shields.io/badge/Vite-Frontend-646CFF)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![ Hyperledger Fabric](https://img.shields.io/badge/Hyperledger%20Fabric-Blockchain-2F3134)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML%20Inference-F7931E)
![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)

---

## 1. Project Title
**PharmaVerse AI: Intelligent Pharmaceutical Supply Chain Traceability & Anti-Counterfeit Platform**

---

## 2. Course & Domain
- **Course & Domain:** Service-Oriented Architecture (SOA) & Microservices
- **Institution:** K L H (Deemed to be) University (KLH University)
- **Department:** Department of Computer Science and Engineering & Information Technology (CSE & CSIT)
- **Academic Year:** 2026 – 2027
- **Authors:**
  - S. Harini
  - T.K. Amulya
  - Y. Nihitha
  - A. Anitha

---

## Table of Contents
1. [Project Title](#1-project-title)
2. [Course & Domain](#2-course--domain)
3. [Project Overview](#3-project-overview)
4. [Problem Statement](#4-problem-statement)
5. [Objectives](#5-objectives)
6. [Existing System and Limitations](#6-existing-system-and-limitations)
7. [Proposed System](#7-proposed-system)
8. [System Architecture](#8-system-architecture)
9. [Technologies Used](#9-technologies-used)
10. [Microservices and Responsibilities](#10-microservices-and-responsibilities)
11. [Backend Architecture](#11-backend-architecture)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Blockchain Integration](#13-blockchain-integration)
14. [Data Management](#14-data-management)
15. [AI/ML Components](#15-aiml-components)
16. [Simulator](#16-simulator)
17. [API Documentation](#17-api-documentation)
18. [Authentication and Authorization](#18-authentication-and-authorization)
19. [Project Workflow](#19-project-workflow)
20. [Installation and Setup](#20-installation-and-setup)
21. [Prerequisites](#21-prerequisites)
22. [Environment Variables](#22-environment-variables)
23. [Running the Project](#23-running-the-project)
24. [Testing and Verification](#24-testing-and-verification)
25. [Project Directory Structure](#25-project-directory-structure)
26. [Troubleshooting](#26-troubleshooting)
27. [Future Enhancements](#27-future-enhancements)
28. [Authors and Academic Credits](#28-authors-and-academic-credits)
29. [License and Copyright](#29-license-and-copyright)

---

## 3. Project Overview
PharmaVerse AI is an academic pharmaceutical supply-chain monitoring and traceability prototype built with Service-Oriented Architecture (SOA) principles. It supports manufacturer, logistics, distributor, pharmacy, and regulator workflows.

The platform links software-generated QR and RFID identifiers to database batch records, processes software-simulated or submitted telemetry, supports selected Hyperledger Fabric audit writes, and includes a heuristic contextual risk engine and optional Random Forest inference. These integrations do not imply physical RFID readers, physical sensors, production deployment, or live performance benchmarking.

---

## 4. Problem Statement
Global pharmaceutical supply chains face critical structural vulnerabilities:
1. **Proliferation of Counterfeit Drugs:** Fraudulent medicines infiltrate distribution channels due to weak single-identifier packaging and forgeable paper documentation.
2. **Cold-Chain Environmental Compromise:** Vaccines and biologics undergo unmonitored temperature and humidity excursions during transit, degrading potency without visible exterior package damage.
3. **Information Silos & Opaque Custody Transfers:** Traditional logistics systems maintain fragmented internal databases, making custody accountability difficult to reconstruct across organizational borders.
4. **Delayed Regulatory Enforcement:** Public health agencies lack real-time visibility into suspicious diversion, illegal handoffs, or batch tampering until after compromised medicines reach patients.

---

## 5. Objectives
1. Provide dual QR and RFID serialization tied deterministically to manufacturing batches and pharmaceutical formulations.
2. Implement role-based custody lifecycle tracking from manufacturer dispatch to retail pharmacy dispensing.
3. Process simulated or submitted environmental telemetry and detect temperature excursions or route deviations.
4. Deliver statistical and heuristic anomaly detection using a trained scikit-learn Random Forest classifier.
5. Support selected Hyperledger Fabric ledger operations for custody and audit records.
6. Enforce strict role-based access control (RBAC), multi-factor email verification, and administrative account approval workflows.

---

## 6. Existing System and Limitations
Traditional pharmaceutical tracking platforms rely on:
- **Centralized Siloed Databases:** High vulnerability to single-point-of-failure, internal data tampering, and proprietary vendor lock-in.
- **Single-Factor 1D Barcodes:** Barcodes are easily photographed, cloned, and duplicated across fraudulent packaging.
- **Post-Delivery Compliance Audits:** Temperature breaches are only identified upon manual inspection days after arrival, resulting in waste and patient safety hazards.
- **Lack of Multi-Enterprise Cryptographic Trust:** Participants in the supply chain do not share a single source of verifiable truth.

---

## 7. Proposed System
PharmaVerse AI addresses these limitations through a loosely coupled Service-Oriented Architecture:
- **Digital Identity Verification:** Software-linked QR and RFID identifiers resolve to batch records and can be compared with supplied observations. No physical RFID hardware is required or included.
- **Telemetry Processing:** The software IoT simulator and API inputs supply readings evaluated against drug-specific storage parameters; this is not continuous physical monitoring.
- **Hybrid Data Responsibilities:** PostgreSQL is the operational database. Explicitly selected events can be written to Hyperledger Fabric; an AI risk-analysis request itself does not submit a Fabric transaction.
- **Fabric availability:** When the gateway is disabled or unreachable, ledger operations report unavailable. The AI analysis response reports `NOT_SUBMITTED` because it does not attempt a ledger write; no verified fallback ledger is implied.

---

## 8. System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Presentation Layer"]
        UI[React 19 + Vite SPA]
        Scanner[Webcam QR Scanner / Manual Entry]
    end

    subgraph Gateway ["Service Routing & Security"]
        Router[FastAPI Application Gateway / REST API]
        Auth[JWT & RBAC Security Engine]
        ConfigGuard[Production Safety Guard]
    end

    subgraph Services ["Core SOA Microservices"]
        DrugSvc[Drug & Formulary Service]
        BatchSvc[Batch Management Service]
        SerialSvc[QR / RFID Serialization Service]
        VerifySvc[Dual Verification Engine]
        ShipSvc[Shipment & Custody Service]
        SimSvc[Software IoT Simulator / Telemetry API]
        AISvc[Contextual Risk Engine & Optional ML Inference]
        AuditSvc[Audit Trail Service]
        AdminSvc[User Approval & Admin Service]
    end

    subgraph DataLayer ["Persistence & External Layers"]
        DB[(PostgreSQL Database)]
        MLArtifact[Random Forest Joblib Model]
        FDA[openFDA Public API Gateway]
        FabricGW[Node.js Fabric Gateway :8090]
        FabricNet[[Hyperledger Fabric v2.5 Peer Network]]
    end

    UI --> Router
    Scanner --> Router
    Router --> Auth
    Auth --> ConfigGuard
    Router --> DrugSvc & BatchSvc & SerialSvc & VerifySvc & ShipSvc & SimSvc & AISvc & AuditSvc & AdminSvc

    DrugSvc & BatchSvc & SerialSvc & ShipSvc & AuditSvc & AdminSvc --> DB
    DrugSvc -.-> FDA
    SimSvc --> AISvc
    AISvc --> DB
    AISvc --> MLArtifact
    VerifySvc --> DB
    VerifySvc -.-> FabricGW
    ShipSvc -.-> FabricGW
    FabricGW -.-> FabricNet
```

---

## 9. Technologies Used
- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic v2, psycopg3.
- **Frontend:** React 19, Vite, Tailwind CSS, Lucide React, Axios, Recharts, `@zxing/browser`, `qrcode.react`.
- **Database:** PostgreSQL (with Supabase Session and Transaction Pooler support).
- **Machine Learning:** scikit-learn (Random Forest Classifier), NumPy, Pandas, Joblib.
- **Distributed Ledger:** Hyperledger Fabric v2.5+, Node.js Fabric Gateway (`@grpc/grpc-js`, `@hyperledger/fabric-gateway`), JavaScript Chaincode (`fabric-contract-api`).
- **External Integration:** U.S. FDA openFDA Public Regulatory APIs (NDC Directory and Enforcement reports).

---

## 10. Microservices and Responsibilities

| Service | Endpoint Prefix | Core Responsibilities |
|---|---|---|
| **Authentication & Identity Service** | `/api/auth` | JWT issuance, email/password sign-in, one-time email verification and reset links, Google identity verification, and email OTP 2FA. |
| **Admin & Governance Service** | `/api/admin` | Registration approval/rejection workflows, user status management, system KPI metrics. |
| **Drug Formulary Service** | `/api/drugs` | Master formulary catalog, temperature/humidity storage criteria, openFDA integration. |
| **Batch Management Service** | `/api/batches` | Manufacturing batch creation, expiration tracking, unit allocation. |
| **Serialization Service** | `/api/qr`, `/api/rfid` | Deterministic QR code generation, RFID tag provisioning, format validation. |
| **Verification Service** | `/api/verification` | Multi-attribute cross-verification (QR + RFID + Batch + Ledger custody check). |
| **Shipment & Tracking Service** | `/api/shipments` | Transit route creation, custody transfer updates, timestamped geolocation event logging. |
| **Telemetry & Simulation Service** | `/api/simulation` | Autonomous simulation of GPS transit corridors, ambient temperature probes, and humidity excursions. |
| **AI & Predictive Risk Service** | `/api/ai`, `/api/ml` | Heuristic correlation engine, feature extraction, Random Forest fraud classification. |
| **Audit Service** | `/api/audit` | Read-only chronological audit log retrieval for regulators and compliance officers. |
| **Blockchain Bridge Service** | Node.js Gateway (:8090) | Translates REST requests to gRPC Fabric transactions (`chaincode/pharmaverse`). |

---

## 11. Backend Architecture
The backend is structured around a modular layered pattern:
- **`app/api/routes/`**: Contains modular FastAPI routers handling request validation and HTTP status responses.
- **`app/models/`**: Declarative SQLAlchemy models (`User`, `Drug`, `Batch`, `Shipment`, `QRRecord`, `RFIDRecord`, `EmailOTP`, `AuthToken`, `ShipmentTrackingEvent`).
- **`app/schemas/`**: Pydantic models enforcing schema contracts and redacting passwords from validation error responses.
- **`app/services/`**: Encapsulates external integrations (`email_service.py`, `google_auth_service.py`, `fda_reference.py`, `ai_adapter.py`).
- **`app/database/connection.py`**: Configured with `pool_pre_ping=True` and `prepare_threshold=None` for connection poolers (PgBouncer/Supavisor).
- **`app/core/config.py`**: Enforces strict production configuration guards (rejecting localhost databases and short JWT keys when `DEBUG=false`).

---

## 12. Frontend Architecture
The frontend is a single-page web application (SPA) created with React 19 and Vite:
- **`src/pages/`**: View components for all supply chain roles (`Login`, `Register`, `Dashboard`, `AdminDashboard`, `Drugs`, `Batches`, `Shipments`, `Verification`, `Blockchain`, `AI`, `Simulation`).
- **`src/components/common/`**: Reusable navigation bars, data tables, protected route wrappers, and interactive webcam barcode scanners.
- **`src/components/charts/`**: Responsive operational and risk charts powered by Recharts (`RiskChart.jsx`, `ShipmentChart.jsx`).
- **`src/utils/`**: Utilities for role access matrices (`roles.js`), error sanitizers (`error.js`), and QR payload parsers (`qrPayload.js`).

---

## 13. Blockchain Integration
PharmaVerse AI integrates Hyperledger Fabric for immutable, non-repudiable audit trails.

### Smart Contract (`chaincode/pharmaverse/`)
- The chaincode registers drugs and batches, assigns digital identities, records shipment/custody changes, verifies identity, and records selected IoT events and AI alerts.
- `getBatchHistory` returns batch-key history together with linked selected IoT, AI-alert, and ownership-transfer records.

### Gateway Service (`blockchain/gateway/`)
A Node.js gateway connects to Fabric peers over gRPC and authenticates backend requests using `X-PharmaVerse-Service-Secret`. When the network is offline or disabled (`FABRIC_ENABLED=false`), Fabric-dependent operations return an unavailable result; PostgreSQL remains the operational data store. No live network performance claim is made by the local test suite.

---

## 14. Data Management
- **Primary Operational Database:** PostgreSQL stores all operational entities, relationships, foreign keys, and indexes.
- **Schema Migrations:** Managed through Alembic. The migration history is continuous and linear up to `20261104_auth_links_and_2fa`.
- **Pre-trained ML Model:** Stored in `data/models/pharmaverse_fraud_model.joblib` with metadata in `data/models/model_metadata.json`.
- **Offline Reference Data:** Cached FDA directory in `data/reference/openfda_ndc.json` ensuring offline operation during external API downtime.

---

## 15. AI/ML Components
The platform uses a deterministic contextual heuristic risk engine and provides separate optional scikit-learn model inference:
- Correlation is limited to the assessed batch and the inclusive 60-minute backward-looking window; future events and other batches are excluded.
- The six binary factors are identity (20), expiry (5), environmental (20), route (20), delay (15), and ownership (10). Repeated observations contribute evidence but do not repeat a factor's base weight.
- Configured distinct-factor interactions add 10 points for environmental + route and 10 for route + delay. The final heuristic score is bounded to 0–100; explanations list factor evidence IDs.
- **Model Architecture:** Random Forest Classifier (`data/models/pharmaverse_fraud_model.joblib`).
- **Input Features (Feature Vector):**
  - Temperature excursion duration and delta (°C outside specified drug stability window).
  - Humidity excursion magnitude (% relative humidity excursion).
  - Geolocation deviation from designated freight route (km).
  - Transit dwell time anomalies (hours delayed against scheduled ETA).
  - Verification attribute discrepancies (QR / RFID mismatch flags).
  - Custody handoff irregularities (unauthorized custody transfers).
- **Output Metrics:**
  - Optional model probability and label, when a compatible model artifact is available. This is separate from the bounded heuristic score.
  - Evidence-linked heuristic risk category and review recommendations.

---

## 16. Simulator
The backend software simulator (`backend/app/simulation/`) generates event data for nine scenarios. It does not represent physical sensor hardware:
1. `normal`: Standard transit with compliant temperatures and on-schedule transit.
2. `temperature_excursion`: Critical temperature breaches exceeding cold-chain bounds.
3. `humidity_excursion`: High humidity spikes indicating packaging vulnerability.
4. `route_deviation`: GPS route deviation from approved transit waypoints.
5. `delayed_shipment`: Prolonged transit delays exceeding safety buffers.
6. `unauthorized_transfer`: Custody handoff to an unregistered supply chain actor.
7. `qr_mismatch`: Detection of duplicated or invalid QR payloads.
8. `rfid_mismatch`: A simulated RFID observation differs from the expected batch identifier.
9. `combined_high_risk`: Multiple correlated anomalies produce a high contextual risk score; this score is not a calibrated counterfeit probability.

---

## 17. API Documentation
When running the backend, interactive OpenAPI/Swagger documentation is available at:
`http://127.0.0.1:8000/docs`

Key API Route Groups:
- **Auth:** `POST /api/auth/login`, `POST /api/auth/email-verification/send`, `POST /api/auth/email-verification/confirm`, `POST /api/auth/register/email`, `POST /api/auth/google/login`, `POST /api/auth/google/verify`, `POST /api/auth/register/google`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`, `POST /api/auth/2fa/verify`, `PATCH /api/auth/2fa`
- **Admin:** `GET /api/admin/dashboard/summary`, `GET /api/admin/registration-requests`, `POST /api/admin/registration-requests/{id}/approve`, `POST /api/admin/registration-requests/{id}/reject`
- **Drugs:** `GET /api/drugs`, `POST /api/drugs`, `GET /api/drugs/{id}`
- **Batches:** `GET /api/batches`, `POST /api/batches`, `GET /api/batches/{id}`
- **Verification:** `POST /api/verification/verify`, `POST /api/verification/scan`
- **Shipments:** `GET /api/shipments`, `POST /api/shipments`, `POST /api/shipments/{id}/events`
- **Simulation:** `GET /api/simulation/status`, `POST /api/simulation/start`, `POST /api/simulation/stop`, `POST /api/simulation/scenario`
- **AI & ML:** `POST /api/ai/analyze`, `GET /api/ml/status`, `POST /api/ml/predict`
- **Blockchain:** `GET /api/blockchain/status`, `GET /api/blockchain/history/{id}`
- **Audit:** `GET /api/audit/logs`, `GET /api/audit/logs/{id}`
- **System:** `GET /api/health`

---

## 18. Authentication and Authorization
- **Email Registration:** A cryptographically random, single-use email link is verified before profile submission. Public roles are `PHARMACY`, `MANUFACTURER`, `DISTRIBUTOR`, and `TRANSPORTER`; registrations remain `PENDING` until admin approval.
- **Google Sign-In and Registration:** The backend verifies Google's ID token, including issuer, audience, verified email, and unique subject. It never links a Google identity to an existing account by matching email. New Google users select a public role and remain `PENDING` for approval.
- **Sign-In and 2FA:** Password login returns a JWT only for an active, approved account. Users who enable email 2FA must also provide a short-lived, single-use email OTP; Google sign-in observes the same 2FA gate.
- **Password Recovery:** Reset links are random, hashed in the database, single-use, and time limited. Responses avoid confirming whether an email address has an account.
- **Settings and Authorization:** Authenticated users can enable or disable email 2FA in Settings. API dependencies enforce authentication and existing role-based access rules; pending/rejected accounts cannot use protected APIs.
- **First-Admin Bootstrap:** Secure CLI command (`backend/scripts/bootstrap_admin.py`) for initializing the founding administrator without public exposure.

---

## 19. Project Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Administrator
    actor Mfr as Manufacturer
    actor Trans as Transporter
    actor Pharm as Pharmacy
    actor Reg as Regulator

    Note over Admin: 1. Setup & Governance
    Admin->>Admin: Bootstrap founding admin via CLI
    Mfr->>Admin: Register account (PENDING)
    Admin->>Mfr: Approve registration

    Note over Mfr: 2. Drug & Batch Registration
    Mfr->>Mfr: Register Drug (storage criteria)
    Mfr->>Mfr: Manufacture Batch & generate serialized QR/RFID records

    Note over Mfr,Trans: 3. Dispatch & Custody Transfer
    Mfr->>Trans: Create Shipment & transfer custody
    Trans->>Trans: Ingest IoT environmental readings (GPS, temp, humidity)

    Note over Trans,Pharm: 4. Receipt & Dual Verification
    Trans->>Pharm: Deliver shipment
    Pharm->>Pharm: Scan QR and read RFID tag
    Pharm->>Pharm: Verification Service checks local DB and Fabric Ledger

    Note over Reg: 5. Oversight & Audit
    Reg->>Reg: Review AI anomaly risk scores & audit trail logs
```

---

## 20. Installation and Setup

### Step 1: Clone Repository
```powershell
git clone https://github.com/Harinisoma28/PharmaVerse-AI.git
cd PharmaVerse-AI
```

### Step 2: Configure Environment Files
```powershell
Copy-Item .env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

### Step 3: Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_demo_data.py
cd ..
```

### Step 4: Frontend Setup
```powershell
cd frontend
npm.cmd install
cd ..
```

---

## 21. Prerequisites
- **Python 3.11+** (for FastAPI backend and ML inference)
- **Node.js 18+ & npm** (for Vite frontend and Fabric gateway)
- **PostgreSQL 14+** (local server or Supabase PostgreSQL instance)
- **Git** (for version control)
- **Docker & Docker Compose** *(Optional, for running local Hyperledger Fabric network)*

---

## 22. Environment Variables

### Root Template (`.env.example`)
A comprehensive template is maintained at the repository root [`pharmaverse-ai/.env.example`](.env.example).

### Backend (`backend/.env`)
| Variable | Description | Default / Example |
|---|---|---|
| `APP_NAME` | Service display name | `PharmaVerse AI` |
| `DEBUG` | Development mode toggle | `true` (use `false` in production) |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://postgres:postgres@localhost:5432/pharmaverse` |
| `JWT_SECRET` | Secret key for JWT signing | 32+ character random string |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Access token lifespan | `60` |
| `CORS_ORIGINS` | Permitted browser origins | `http://localhost:5173` |
| `SMTP_HOST` | Gmail SMTP host for verification links and OTP | `smtp.gmail.com` |
| `SMTP_PORT` | Outbound SMTP port | `587` |
| `SMTP_USER` | Gmail account used for SMTP authentication | Gmail address |
| `SMTP_PASSWORD` | Gmail app password (not the account password) | Secret |
| `SMTP_FROM_EMAIL` | Optional sender address; defaults to `SMTP_USER` | Gmail address |
| `FRONTEND_BASE_URL` | Base URL used in verification and reset links | `http://localhost:5173` |
| `AUTH_LINK_TTL_MINUTES` | Verification/reset link lifetime | `30` |
| `GOOGLE_CLIENT_ID` | Google OAuth web client ID; configure backend and frontend | Google Cloud OAuth client ID |
| `FABRIC_ENABLED` | Toggle Hyperledger Fabric | `false` |
| `FABRIC_GATEWAY_URL` | Gateway microservice URL | `http://127.0.0.1:8090` |
| `FABRIC_GATEWAY_SECRET` | Shared secret header | Secure random string |
| `FDA_API_TIMEOUT_SECONDS` | Outbound openFDA HTTP timeout | `8.0` |
| `FDA_CACHE_TTL_SECONDS` | Outbound openFDA cache TTL | `3600.0` |

### Frontend (`frontend/.env`)
| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend REST API endpoint | `http://localhost:8000/api` |
| `VITE_GOOGLE_CLIENT_ID` | Google Identity Services web client ID | Same ID as `GOOGLE_CLIENT_ID` |

---

## 23. Running the Project

Start the application using separate PowerShell terminals:

### Terminal 1: Backend API
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at: `http://127.0.0.1:8000/docs`

### Terminal 2: Frontend Web Client
```powershell
cd frontend
npm.cmd run dev
```
Web Application will be available at: `http://localhost:5173`

### Terminal 3 (Optional): Hyperledger Fabric Gateway
```powershell
cd blockchain/gateway
node server.js
```

---

## 24. Testing and Verification

### Backend Automated Test Suite
```powershell
cd backend
python -m pytest -q
```
*Current test suite: 220 passed unit, security, and integration tests.*

### Frontend Unit & E2E Verification
```powershell
cd frontend
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

### Standalone Simulator Verification
```powershell
python simulator/cli.py --list
python simulator/cli.py --scenario normal
```

---

## 25. Project Directory Structure

```text
PharmaVerse-AI/
├── .env.example                        # Root environment configuration template
├── .gitignore                          # Git ignore specification
├── README.md                           # Single authoritative project documentation
├── LICENSE                             # Proprietary All Rights Reserved license
│
├── backend/                            # Python FastAPI REST microservice
│   ├── alembic/                        # Database migration scripts
│   │   ├── versions/                   # Migration versions (up to 20261031_auth_approval_workflow)
│   │   └── env.py                      # Alembic migration environment
│   ├── app/                            # Application package
│   │   ├── ai/                         # Anomaly detector, correlation engine, and risk scoring
│   │   ├── api/routes/                 # REST API route handlers
│   │   ├── blockchain/                 # Hyperledger Fabric gateway client
│   │   ├── core/                       # Security, roles, and production configuration guards
│   │   ├── database/                   # SQLAlchemy connection and session management
│   │   ├── ml/                         # Machine learning model loading and feature extraction
│   │   ├── models/                     # SQLAlchemy 2.0 ORM database models
│   │   ├── schemas/                    # Pydantic request and response schemas
│   │   ├── services/                   # Email, Google OAuth, FDA reference services
│   │   ├── simulation/                 # IoT sensor excursion simulator
│   │   └── main.py                     # FastAPI application factory and exception handlers
│   ├── scripts/                        # Utility scripts (bootstrap_admin.py, seed_demo_data.py)
│   ├── tests/                          # Automated unit and integration tests
│   ├── requirements.txt                # Python dependencies
│   ├── alembic.ini                     # Alembic configuration
│   └── .env.example                    # Backend environment configuration template
│
├── frontend/                           # React 19 + Vite single-page application
│   ├── public/                         # Static web assets
│   ├── src/                            # Application source
│   │   ├── assets/                     # Images and branding
│   │   ├── components/                 # Reusable UI widgets and charts
│   │   ├── context/                    # React Context (AuthContext)
│   │   ├── layouts/                    # Main application layouts
│   │   ├── pages/                      # Role-based views (Dashboard, Verification, Register, etc.)
│   │   ├── services/                   # Axios API service client (api.js, authService.js)
│   │   ├── utils/                      # Helper utilities (roles, QR payload parser, error sanitizer)
│   │   ├── App.jsx                     # Router and protected route definitions
│   │   └── main.jsx                    # React DOM entrypoint
│   ├── package.json                    # Frontend dependencies and npm scripts
│   └── .env.example                    # Frontend environment configuration template
│
├── blockchain/                         # Hyperledger Fabric integration
│   ├── chaincode/pharmaverse/          # Node.js smart contract (fabric-contract-api)
│   ├── gateway/                        # Express.js REST-to-gRPC gateway microservice
│   └── crypto/                         # MSP and TLS cryptographic configurations
│
├── data/                               # Data artifacts and models
│   ├── models/                         # Pre-trained Random Forest model (joblib)
│   ├── reference/                      # Offline openFDA NDC directory reference JSON
│   ├── fixtures/                       # Test fixtures and vectors
│   ├── manifests/                      # Serialization manifests
│   └── metrics/                        # Model training metrics and classification reports
│
├── scripts/                            # Standalone ML training and evaluation scripts
│   ├── datasets/                       # Dataset generation scripts
│   ├── train/                          # Model training pipelines
│   └── evaluate/                       # Model evaluation benchmarks
│
├── simulator/                          # Legacy simulator entry points and metadata
│   ├── scenarios/                      # Legacy scenario metadata
│   └── cli.py                          # Legacy command-line telemetry runner
│
└── docs/                               # Academic and technical documentation references
```

---

## 26. Troubleshooting

### 1. Database Connection Errors (`Connection refused` or `pg_hba.conf` rejection)
- Ensure PostgreSQL service is running: `Get-Service -Name postgresql*` in PowerShell.
- Verify that credentials in `backend/.env` match your local PostgreSQL user and password.
- If using Supabase or cloud PostgreSQL, verify the URL starts with `postgresql+psycopg://` and uses port `5432` (session) or `6543` (transaction pooler).

### 2. Frontend CORS or Connection Refused
- Check that the backend is running on `http://127.0.0.1:8000`.
- Verify `frontend/.env` contains `VITE_API_BASE_URL=http://localhost:8000/api`.
- Ensure `CORS_ORIGINS` in `backend/.env` includes `http://localhost:5173`.

### 3. Production Configuration Guard Rejection
- When `DEBUG=false` in `backend/.env`, the backend strictly requires a remote database host (rejecting `localhost`) and a `JWT_SECRET` of at least 32 characters.
- For local development, set `DEBUG=true` in `backend/.env`.

### 4. Admin Bootstrap Duplicate Refusal
- Running `python scripts/bootstrap_admin.py` when an admin already exists will safely refuse creation and return exit code 1 to prevent unauthorized takeover. Use the admin dashboard to manage additional administrators.

---

## 27. Future Enhancements
1. **Telemetry persistence and replay:** Store simulator/API events for historical analysis and repeatable evaluation.
2. **Decentralized Identifiers (DIDs):** Evaluate W3C Verifiable Credentials for cross-border customs clearance.
3. **Mobile Client:** Native React Native digital identity scanning client for warehouse and delivery teams.
4. **Federated Model Learning:** Evaluate privacy-preserving distributed machine learning across pharmaceutical manufacturing networks.

---

## 28. Authors and Academic Credits

- **Course:** Service-Oriented Architecture (SOA) & Microservices
- **Department:** Department of Computer Science and Engineering & Information Technology (CSE & CSIT)
- **Institution:** K L H (Deemed to be) University (KLH University)
- **Project Authors:**
  - S. Harini
  - T.K. Amulya
  - Y. Nihitha
  - A. Anitha

---

## 29. License and Copyright

PROPRIETARY SOFTWARE LICENSE — ALL RIGHTS RESERVED

Copyright © 2026–2027 KLH University, CSE & CSIT Department. All Rights Reserved.

**Project:** PharmaVerse AI<br>
**Course & Domain:** Service-Oriented Architecture (SOA) & Microservices<br>
**Authors:** S. Harini, T.K. Amulya, Y. Nihitha, A. Anitha

No permission is granted to use, copy, modify, adapt, distribute, publish, sublicense, or commercially exploit this software, in whole or in part, without prior written authorization from the copyright holder, except where permitted by applicable law.

Access to this repository does not constitute a license or grant of any intellectual property rights. Refer to the root [`LICENSE`](LICENSE) file for complete details.

---

**PharmaVerse AI — Intelligent Traceability. Transparent Supply Chains. Safer Pharmaceutical Distribution.**
