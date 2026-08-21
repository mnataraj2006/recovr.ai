# Recovr.ai — System Architecture

This document outlines the detailed system architecture, directory layout, database schema, state machine, and development roadmap for **Recovr.ai**, an AI-powered payment and checkout recovery agent.

---

## 1. High-Level System Architecture

Recovr.ai uses a hybrid architecture that separates high-risk financial decisions and automated retries (handled by a deterministic rule and state engine) from cognitive, text-generation, and behavioral analysis tasks (handled by an LLM).

```mermaid
graph TD
    subgraph Client / UI
        UI[React Dashboard & Admin Console]
    end

    subgraph API Ingestion & Webhooks
        API[FastAPI Gateway]
        SIM[Checkout & Payment Simulator]
    end

    subgraph Storage Layer
        DB[(MongoDB Database)]
    end

    subgraph Core Recovery Loop
        D_ENG[Root Cause Diagnosis Engine]
        P_ENG[Recovery Policy FSM Engine]
        G_ENG[Guardrail Engine]
        SCHED[Exponential Backoff Scheduler]
    end

    subgraph AI Reasoning (Claude)
        LLM_DIAG[LLM Behavioral Diagnoser]
        LLM_MSG[LLM Template-Guarded Message Generator]
    end

    subgraph Messaging & Outbound
        MOCK_GW[Simulated Payment Gateway]
        NUDGE[Customer SMS/WhatsApp Notification Dispatcher]
    end

    UI <-->|REST API| API
    SIM -->|Simulated Webhooks| API
    API <-->|Read/Write| DB
    
    %% Engine Flow
    API -->|Process Checkout Event| D_ENG
    D_ENG -->|Structured Gateway Errors| P_ENG
    D_ENG -->|Ambiguous Abandons| LLM_DIAG
    LLM_DIAG -->|Diagnosis Result| P_ENG
    
    P_ENG -->|Propose Recovery Action| G_ENG
    G_ENG -->|Validate Action| DB
    
    G_ENG -- APPROVED --> SCHED
    G_ENG -- BLOCKED --> DB
    
    SCHED -->|Trigger Retry| MOCK_GW
    SCHED -->|Trigger Nudge| LLM_MSG
    LLM_MSG -->|Format Notification| NUDGE
    
    MOCK_GW & NUDGE -->|Update Status & Outcomes| API
```

---

## 2. Directory Structure

Recovr.ai is organized as a clean, modular monorepo:

```text
recovr-ai/
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app initialization
│   │   │
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py             # App environment configuration
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py           # Motor MongoDB client setup
│   │   │   └── base.py                 # Abstract database model helpers
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── customer.py             # Customer MongoDB document model
│   │   │   ├── checkout.py             # Checkout MongoDB document model
│   │   │   ├── transaction.py          # Transaction MongoDB document model
│   │   │   └── audit.py                # Audit log models
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── customer.py             # Pydantic input/output schemas
│   │   │   ├── checkout.py
│   │   │   ├── transaction.py
│   │   │   ├── recovery.py
│   │   │   └── metrics.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py         # FastAPI dependency injection
│   │   │   └── routes/
│   │   │       ├── checkouts.py        # Checkout ingestion endpoints
│   │   │       ├── payments.py         # Simulated gateway API
│   │   │       ├── recovery.py         # Recovery engine API
│   │   │       ├── metrics.py          # Metrics & analytics aggregation
│   │   │       ├── audit.py            # Audit log explorer
│   │   │       └── simulation.py       # Batch simulation triggers
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── recovery_service.py     # Main recovery process coordinator
│   │   │   └── simulation_service.py   # Synthesized batch execution
│   │   │
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis/
│   │   │   │   └── engine.py           # Rules -> LLM fallback diagnoser
│   │   │   ├── policy/
│   │   │   │   └── engine.py           # Configurable FSM policy matrix
│   │   │   ├── guardrails/
│   │   │   │   └── engine.py           # Multi-point check engine (limits, cooldowns)
│   │   │   ├── scheduler/
│   │   │   │   └── engine.py           # Jittered exponential backoff engine
│   │   │   └── metrics/
│   │   │       └── engine.py           # Aggregation & calculations
│   │   │
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── client.py               # Claude API caller setup
│   │   │   ├── diagnosis.py            # Contextual LLM analysis
│   │   │   └── messaging.py            # Personalized copy generator
│   │   │
│   │   └── audit/
│   │       ├── __init__.py
│   │       └── logger.py               # Append-only audit logger
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                 # Pytest fixtures and mock DB configs
│   │   ├── test_diagnosis.py
│   │   ├── test_policy.py
│   │   ├── test_guardrails.py
│   │   ├── test_recovery.py
│   │   └── test_metrics.py
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── StatCard.jsx            # Premium summary stat card
│   │   │   ├── RecoveryChart.jsx       # Chart overlays (Recharts)
│   │   │   ├── AuditTimeline.jsx       # Event-sourced log timeline
│   │   │   └── TransactionTable.jsx    # Drill-down transaction grid
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx           # Main stats & metrics
│   │   │   ├── TransactionDetail.jsx   # Root cause, guardrails, & logs
│   │   │   └── SimulationManager.jsx   # Synthetic batch controllers
│   │   ├── services/
│   │   │   └── api.js                  # Axios client wrappers
│   │   ├── hooks/
│   │   │   └── useInterval.js
│   │   ├── utils/
│   │   │   └── formatters.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css                   # Custom global visual tokens
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── .env.example
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── recovery-policy.md
│
├── scripts/
│   └── seed_data.py                    # Static database bootstrap
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 3. MongoDB Data Model & Schema

We avoid storing all transaction states in one giant document. Instead, we use dedicated, normalized collections with structured entity references.

### Collections & Indexes

1. **`customers`**
   * Fields: `id`, `name`, `email`, `phone`, `created_at`
   * Indexes: `email` (Unique)

2. **`checkouts`**
   * Fields: `id`, `customer_id`, `cart_value` (₹), `items` (List), `checkout_duration_seconds`, `device_info` (Object), `status`, `created_at`
   * Indexes: `customer_id`, `status`

3. **`transactions`**
   * Fields: `id`, `checkout_id`, `customer_id`, `amount` (₹), `status`, `payment_method`, `root_cause_id`, `last_attempt_id`, `created_at`, `updated_at`
   * Indexes: `checkout_id` (Unique), `customer_id`, `status`, `created_at`

4. **`payment_attempts`**
   * Fields: `id`, `transaction_id`, `attempt_number`, `gateway_reference`, `payment_method`, `status` (Success/Failed/Timeout), `gateway_error_code`, `gateway_error_message`, `created_at`
   * Indexes: `transaction_id`, `status`

5. **`diagnoses`**
   * Fields: `id`, `transaction_id`, `root_cause` (Enum), `confidence` (0.0-1.0), `source` (RULE_ENGINE / LLM_FALLBACK), `rule_triggered` (String, nullable), `reasoning` (String), `created_at`
   * Indexes: `transaction_id` (Unique), `root_cause`

6. **`recovery_actions`**
   * Fields: `id`, `transaction_id`, `action_type` (RETRY_PAYMENT / NUDGE_CUSTOMER), `channel` (SMS / WHATSAPP / API_RETRY), `scheduled_for`, `status` (PENDING / EXECUTING / SUCCESS / FAILED / BYPASSED), `payload` (Object, e.g., message template details), `created_at`
   * Indexes: `transaction_id`, `status`, `scheduled_for`

7. **`guardrail_decisions`**
   * Fields: `id`, `transaction_id`, `action_id`, `allowed` (Boolean), `checks_run` (List of objects detailing check name, input, result), `reason`, `created_at`
   * Indexes: `transaction_id`, `action_id`

8. **`recovery_outcomes`**
   * Fields: `id`, `transaction_id`, `recovered` (Boolean), `recovery_method` (RETRY / MANUAL_LINK / INCENTIVE), `recovered_at`, `amount_recovered` (₹), `total_cost` (₹, cost of LLM queries + sms notifications)
   * Indexes: `transaction_id` (Unique), `recovered`

9. **`audit_events`**
   * Fields: `id`, `transaction_id`, `event_type` (Enum), `timestamp`, `actor` (SYSTEM / AGENT / USER / CUSTOMER), `source` (e.g. "WebhookHandler", "PolicyEngine"), `reason` (String), `metadata` (JSON Object)
   * Indexes: `transaction_id`, `event_type`, `timestamp`

### Entity Relationships

```text
[Customer] (1) ───< (Many) [Checkout]
                       │
                       └── (1:1) [Transaction]
                                    │
                                    ├───< (Many) [Payment Attempt]
                                    ├───(1:1) [Diagnosis]
                                    ├───< (Many) [Recovery Action]
                                    │                 │
                                    │                 └───(1:1) [Guardrail Decision]
                                    ├───(1:1) [Recovery Outcome]
                                    └───< (Many) [Audit Event]
```

---

## 4. Transaction State Machine

The transaction state machine is managed centrally inside `backend/app/models/transaction.py` or a core helper class to ensure validation rules are always respected and illegal transitions throw clean validation errors.

```text
                  ┌──────────────────────────────────────────────┐
                  │                 CREATED                      │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │           CHECKOUT_INITIATED                 │
                  └──────┬────────────────────────────────┬──────┘
                         │                                │
                         ▼ (Payment Started)              ▼ (Cart abandoned / timeout)
                  ┌──────────────────────┐        ┌──────────────────────┐
                  │  PAYMENT_ATTEMPTED   │        │  CHECKOUT_ABANDONED  │
                  └──────┬───────────┬───┘        └──────────┬───────────┘
                         │           │                       │
     (Gateway Success)   │           │ (Gateway Fail)        │
            ┌────────────┘           └───────────┐           │
            ▼                                    ▼           ▼
┌──────────────────────┐                 ┌──────────────────────┐
│      SUCCESS         │                 │      DIAGNOSING      │
└──────────┬───────────┘                 └──────────┬───────────┘
           │                                        │
           ▼                                        ▼
┌──────────────────────┐                 ┌──────────────────────┐
│     RECOVERED        │                 │      DIAGNOSED       │
└──────────────────────┘                 └──────────┬───────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────┐
                                         │   ACTION_PROPOSED    │
                                         └──────────┬───────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────┐
                                         │   GUARDRAIL_CHECK    │
                                         └──────┬───────────┬───┘
                                                │           │
                                     (Approved) │           │ (Blocked)
                                                ▼           ▼
                                         ┌──────────┐   ┌──────────────────────┐
                                         │ APPROVED │   │    UNRECOVERABLE     │
                                         └────┬─────┘   └──────────────────────┘
                                              │
                                              ▼
                                         ┌──────────┐
                                         │ EXECUTED │
                                         └────┬─────┘
                                              │
                                     ┌────────┴────────┐
                                     ▼                 ▼
                                  (Success)         (Fail)
                                     ▼                 ▼
                            ┌────────────────┐   ┌──────────────┐
                            │   RECOVERED    │   │RETRY/ESCALATE│
                            └────────────────┘   └──────┬───────┘
                                                        │
                                                        ▼ (Max attempts hit)
                                                 ┌──────────────┐
                                                 │UNRECOVERABLE │
                                                 └──────────────┘
```

### Transition Validation Rules

1. Any terminal state (`RECOVERED`, `UNRECOVERABLE`) is locked.
2. A transition to `DIAGNOSING` requires a preceding `PAYMENT_ATTEMPTED` (failed status) or `CHECKOUT_ABANDONED`.
3. An action cannot move to `EXECUTED` without first moving through `ACTION_PROPOSED` $\rightarrow$ `GUARDRAIL_CHECK` $\rightarrow$ `APPROVED`.
4. If `GUARDRAIL_CHECK` fails, state MUST transition directly to `UNRECOVERABLE` or `RETRY/ESCALATE` (depending on the check type).

---

## 5. Development Milestones

We will implement Recovr.ai in 6 incremental milestones to guarantee stability, thorough test coverage, and clear progress.

### Milestone 1: Foundation & Database Layer
* **Objective:** Establish the directory structure, configuration settings, MongoDB connection utilities, and core Pydantic models.
* **Deliverables:** Setup of `main.py`, settings, base model configurations, and unit tests validating database connectivity.

### Milestone 2: Payment Simulator & Webhook Ingestion
* **Objective:** Create the simulated Razorpay-style payment gateway and API endpoints to initiate checkouts and process payments.
* **Deliverables:** `/payments/create`, `/payments/attempt`, `/webhooks/payment` routes, and simulated payment outcomes (Timeout, Insufficient Funds, Success).

### Milestone 3: Diagnosis & Policy Engines
* **Objective:** Build the hybrid diagnosis engine (rules lookup + LLM fallback for cart abandons) and the configurable policy FSM.
* **Deliverables:** Decision trees, Claude integration helper, and policy routing module. Unit tests for error mappings and LLM fallback mockups.

### Milestone 4: Guardrail Engine & Scheduler
* **Objective:** Write the multi-point Guardrail verify class and the exponential backoff scheduler.
* **Deliverables:** Protection checks (cooldown, retry caps, duplicate protections), state transitions, and asynchronous-style scheduling simulator.

### Milestone 5: Metrics, Audit Logger, & Batch Simulation
* **Objective:** Implement the metrics calculation logic, structured event-source audit logging, and the batch runner.
* **Deliverables:** `/simulation/run` for running a batch (10 to 50 transactions), `/metrics/*` routes, and unit tests verifying ROI calculations.

### Milestone 6: UI Dashboard & Integration
* **Objective:** Build the React Vite dashboard with Recharts, transaction drill-downs, audit timelines, and the real-time simulation controller.
* **Deliverables:** Premium Dark/Glassmorphic visual UI, live log feed, and end-to-end integration verification.

---

## 6. Testing Strategy

We will use **pytest** to write modular, robust tests matching each engine block:

1. **Unit Tests:**
   * Test `engines/diagnosis` using mock API calls to Claude (via `pytest-mock` or custom fixtures) and static checkouts.
   * Test `engines/policy` with input vectors covering all 7 standard root causes to ensure correct FSM states and outputs.
   * Test `engines/guardrails` verifying that action props trigger blocks appropriately (e.g. limit hit, cooldown violated).
   * Test `engines/metrics` directly by passing mock database sets and asserting computed values.

2. **Integration Test:**
   * Execute a full simulated transaction:
     `Checkout Ingested` $\rightarrow$ `Gateway Fail (Timeout)` $\rightarrow$ `Diagnose (Timeout)` $\rightarrow$ `Policy Selected (Retry)` $\rightarrow$ `Guardrail Check (Passed)` $\rightarrow$ `Execute Retry` $\rightarrow$ `Gateway Success` $\rightarrow$ `Assert Status is RECOVERED` $\rightarrow$ `Assert Audit Logs & Metrics incremented`.

---

## 7. Local Development Instructions

To spin up the workspace locally:

### Prerequisites
* Python 3.12+ installed
* MongoDB Server running locally on `mongodb://localhost:27017` (or MongoDB Atlas connection string)
* Node.js v18+ (for frontend)

### Backend Setup
1. Navigate to `/backend`:
   ```bash
   cd backend
   ```
2. Copy environment sample:
   ```bash
   copy .env.example .env
   ```
3. Open `.env` and provide your MongoDB connection string and `ANTHROPIC_API_KEY`.
4. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # PowerShell
   # or source venv/bin/activate  # Unix
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to `/frontend`:
   ```bash
   cd ../frontend
   ```
2. Install packages:
   ```bash
   npm install
   ```
3. Copy environment sample:
   ```bash
   copy .env.example .env
   ```
4. Run the React local dev server:
   ```bash
   npm run dev
   ```
