# Walkthrough — Recovr.ai

This document provides a comprehensive summary of all 6 completed development milestones of **Recovr.ai**, files created/modified, and instructions on running the system.

---

## Milestone 1: Project Foundation & Database Layer (Completed)
Established database structures and the core validation state machine.
* **Configurations Created:**
  * `backend/requirements.txt` — Python packages manifest.
  * `backend/.env.example` — Config template.
  * `backend/app/config/settings.py` — Config validation models.
* **Database Layer:**
  * `backend/app/db/connection.py` — MongoDB driver client setup.
  * `backend/app/models/customer.py` — Customer schemas.
  * `backend/app/models/checkout.py` — Checkout session schemas.
  * `backend/app/models/transaction.py` — State machine validator mapping 14 distinct transaction states.

---

## Milestone 2: Payment Simulator & Webhook Ingestion (Completed)
Implemented entrypoints to mimic payment gateway behaviors and checkouts abandonment.
* **Core Services Added:**
  * `backend/app/audit/logger.py` — Structured log dispatch to MongoDB.
  * `backend/app/services/recovery_service.py` — Core recovery loop orchestrator.
* **API Endpoints Implemented (mounted under `/api/v1`):**
  * `backend/app/api/routes/payments.py` — Simulator for creating payment intents and forcing specific failures.
  * `backend/app/api/routes/checkouts.py` — Routes to initiate checkout sessions, track cart details, and record manual checkout abandonment.
  * `backend/app/api/routes/recovery.py` — Ingestion endpoint to catch failed payment callback webhooks.

---

## Milestone 3: Diagnosis & Policy Engines (Completed)
Implemented the core engines that diagnose drop-off reasons and decide the recovery action.
* **AI Client & Prompts:**
  * `backend/app/ai/client.py` — Asynchronous Anthropic client initializer.
  * `backend/app/ai/diagnosis.py` — Structured Claude prompt and JSON validation helper using Pydantic.
* **Diagnosis & FSM Policy Engines:**
  * `backend/app/engines/diagnosis/engine.py` — Classifies failures deterministically via gateway codes and delegates cart abandonments to Claude.
  * `backend/app/engines/policy/engine.py` — Policy matrix FSM mapping diagnoses to recovery actions (Auto-retry or Customer Nudge).

---

## Milestone 4: Guardrail Engine & Scheduler (Completed)
Built safety and scheduling engines to validate proposed actions and automatically execute retries using exponential backoff.
* **Guardrail Engine:**
  * `backend/app/engines/guardrails/engine.py` — Enforces 7 safety guardrails: Already Completed check, Retry attempt limit (max 2), Nudge limit, 5-minute Cooldown window, and Incentive cap.
* **Retry Scheduler:**
  * `backend/app/engines/scheduler/engine.py` — Calculates exponential backoff: `wait = min(60s, 10s * 2^attempt) + jitter` and schedules async tasks to run the retry.

---

## Milestone 5: Metrics, Audit Logger, & Batch Simulation (Completed)
Developed analytics, audit log streams, and cohort simulators.
* **Metrics Route:**
  * `backend/app/api/routes/metrics.py` — Calculates total revenue at risk, recovered revenue, net savings, recovery rate, recovery cost, and ROI.
* **Audit Trail Feed:**
  * `backend/app/api/routes/audit.py` — Exposes chronological streams `/api/v1/audit-events` and `/api/v1/transactions/{id}/audit`.
* **Cohort Simulation Engine:**
  * `backend/app/simulation/runner.py` — Asynchronously runs a 5-customer cohort testing gateway timeouts, declines, and abandonments, computing cohort metrics.
  * `backend/app/api/routes/simulation.py` — Endpoints to trigger and fetch simulation history.

---

## Milestone 6: UI Dashboard & Frontend Integration (Completed)
Created a glassmorphic React dashboard displaying transactions, charts, and chronological timeline feeds.
* **Frontend App:**
  * Scaffolding React + TypeScript project inside `frontend/`.
  * `frontend/src/App.tsx` — Main dashboard UI with KPI counters, Recharts failure categorization bars, simulation triggers, transaction explorer, and expandable chronological timeline feeds with guardrail checks.
  * `frontend/src/index.css` — Custom glassmorphism styling layout.
* **FastAPI Mount:**
  * `backend/app/main.py` updated to serve static assets from `frontend/dist` automatically in production mode.

---

## Verification & Test Execution Results
All **33 unit and integration tests passed successfully** against the local MongoDB instance:
```text
tests\test_database.py ...                                               [  9%]
tests\test_diagnosis_policy.py ..                                        [ 15%]
tests\test_guardrails_scheduler.py ........                              [ 39%]
tests\test_ingestion.py ..                                               [ 45%]
tests\test_metrics_simulation.py ...                                     [ 54%]
tests\test_state_machine.py ....                                         [ 66%]
tests\test_verification_scenarios.py ...........                         [100%]

====================== 33 passed, 20 warnings in 12.93s =======================
```

---

## Instructions to Run Locally

### 1. Run the Backend & Frontend (Local Development)
Start the FastAPI development server:
```bash
# In backend/ directory
uvicorn app.main:app --reload
```

Start the Vite React development server:
```bash
# In frontend/ directory
npm run dev
```
Open `http://localhost:5173` to interact with the dashboard.

### 2. Run the Single-Process Production Build
Compile the React code and run the unified server:
```bash
# In frontend/ directory
npm run build

# In backend/ directory
uvicorn app.main:app
```
Open `http://localhost:8000` to interact with the static-mounted production dashboard.
