# Recovr.ai — API Specifications

This document outlines the REST API contracts, path structures, payload constraints, and error codes for the Recovr.ai backend. All API requests and responses use the application/json MIME-type.

---

## Global Error Responses

Standard structured error format returned for Client Errors (4xx) and Server Errors (5xx):

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable explanation of what went wrong.",
    "details": {}
  }
}
```

Common Error Codes:
* `RESOURCE_NOT_FOUND` (404): The requested transaction, customer, or checkout does not exist.
* `INVALID_STATE_TRANSITION` (400): The transaction state machine rule was violated.
* `VALIDATION_ERROR` (422): Provided JSON does not conform to Pydantic schemas.
* `GUARDRAIL_BLOCKED` (403): The recovery action was rejected by safety rules.

---

## 1. Checkouts API

### Initiate Checkout
* **Endpoint:** `POST /api/v1/checkouts`
* **Description:** Initiates a new shopping session for a customer and returns a checkout token.
* **Request Body:**
  ```json
  {
    "customer": {
      "name": "Jane Doe",
      "email": "jane.doe@example.com",
      "phone": "+919876543210"
    },
    "cart_value": 2999.00,
    "items": [
      {
        "sku": "SKU-PREMIUM-SUB",
        "name": "Recovr Annual Plan",
        "price": 2999.00,
        "quantity": 1
      }
    ],
    "device_info": {
      "ip": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "platform": "Android"
    }
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "success": true,
    "checkout_id": "chk_98fa789bcde",
    "transaction_id": "txn_89ab32cde12",
    "status": "CHECKOUT_INITIATED",
    "created_at": "2026-08-21T05:00:00Z"
  }
  ```

### Abandon Checkout (Manual/Timeout)
* **Endpoint:** `POST /api/v1/checkouts/{id}/abandon`
* **Description:** Fired when a customer closes the browser, remains inactive for a specific timeout, or manually cancels without attempting a payment.
* **Request Body:**
  ```json
  {
    "checkout_duration_seconds": 182,
    "last_viewed_step": "payment_selection",
    "selected_payment_method": "gpay"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "transaction_id": "txn_89ab32cde12",
    "status": "CHECKOUT_ABANDONED",
    "abandoned_at": "2026-08-21T05:03:02Z"
  }
  ```

---

## 2. Payments API (Simulated Gateway)

These endpoints simulate direct actions against a payment gateway (e.g. Razorpay).

### Create Payment Intent
* **Endpoint:** `POST /api/v1/payments/create`
* **Request Body:**
  ```json
  {
    "transaction_id": "txn_89ab32cde12",
    "payment_method": "upi",
    "upi_provider": "gpay"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "payment_id": "pay_u8982312bca",
    "status": "created"
  }
  ```

### Attempt Payment
* **Endpoint:** `POST /api/v1/payments/attempt`
* **Description:** Simulates the authorization attempt of a payment. It will return a gateway outcome based on test triggers.
* **Request Body:**
  ```json
  {
    "payment_id": "pay_u8982312bca",
    "simulated_outcome": "GATEWAY_TIMEOUT" 
  }
  ```
  *(Simulated outcomes include: `SUCCESS`, `INSUFFICIENT_FUNDS`, `GATEWAY_TIMEOUT`, `OTP_FAILURE`, `NETWORK_ERROR`, `PAYMENT_CANCELLED`)*
* **Response (200 OK):**
  ```json
  {
    "success": false,
    "payment_id": "pay_u8982312bca",
    "status": "failed",
    "error": {
      "code": "BAD_REQUEST_ERROR",
      "reason": "gateway_timeout",
      "description": "Gateway connection timed out before bank response received."
    }
  }
  ```

### Webhook Handler
* **Endpoint:** `POST /api/v1/webhooks/payment`
* **Description:** Ingests events asynchronously from the gateway simulator. This trigger spawns the core recovery loop.
* **Request Body:**
  ```json
  {
    "event": "payment.failed",
    "payload": {
      "payment": {
        "id": "pay_u8982312bca",
        "entity": "payment",
        "amount": 299900,
        "currency": "INR",
        "status": "failed",
        "order_id": "order_stk39910a",
        "error_code": "GATEWAY_TIMEOUT",
        "error_description": "Connection to card network timed out."
      }
    }
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "received": true,
    "transaction_id": "txn_89ab32cde12",
    "recovery_state": "DIAGNOSING"
  }
  ```

---

## 3. Transactions & Audit API

### Get Transaction Details
* **Endpoint:** `GET /api/v1/transactions/{id}`
* **Response (200 OK):**
  ```json
  {
    "id": "txn_89ab32cde12",
    "checkout_id": "chk_98fa789bcde",
    "amount": 2999.00,
    "status": "DIAGNOSED",
    "customer": {
      "name": "Jane Doe",
      "email": "jane.doe@example.com"
    },
    "diagnosis": {
      "root_cause": "GATEWAY_TIMEOUT",
      "confidence": 1.0,
      "source": "RULE_ENGINE"
    },
    "attempts_count": 1,
    "created_at": "2026-08-21T05:00:00Z"
  }
  ```

### List Transactions
* **Endpoint:** `GET /api/v1/transactions`
* **Query Parameters:** `status` (Optional), `limit` (Default: 20), `offset` (Default: 0)
* **Response (200 OK):**
  ```json
  {
    "transactions": [
      {
        "id": "txn_89ab32cde12",
        "amount": 2999.00,
        "status": "RECOVERED",
        "root_cause": "GATEWAY_TIMEOUT",
        "created_at": "2026-08-21T05:00:00Z"
      }
    ],
    "total": 128
  }
  ```

### Get Audit Timeline
* **Endpoint:** `GET /api/v1/audit/{transaction_id}`
* **Response (200 OK):**
  ```json
  {
    "transaction_id": "txn_89ab32cde12",
    "timeline": [
      {
        "timestamp": "2026-08-21T05:00:00Z",
        "event_type": "CHECKOUT_CREATED",
        "actor": "CUSTOMER",
        "reason": "Customer initiated checkout flow",
        "metadata": { "cart_value": 2999.0 }
      },
      {
        "timestamp": "2026-08-21T05:01:00Z",
        "event_type": "PAYMENT_FAILED",
        "actor": "SYSTEM",
        "reason": "Payment attempt failed with GATEWAY_TIMEOUT",
        "metadata": { "gateway_code": "GATEWAY_TIMEOUT" }
      },
      {
        "timestamp": "2026-08-21T05:01:02Z",
        "event_type": "DIAGNOSIS_CREATED",
        "actor": "AGENT",
        "reason": "Classified failure via rule table mapping.",
        "metadata": { "root_cause": "GATEWAY_TIMEOUT", "source": "RULE_ENGINE" }
      }
    ]
  }
  ```

---

## 4. Recovery & Decision API

### Trigger Recovery Loop (Sync / Async execution override)
* **Endpoint:** `POST /api/v1/recovery/{transaction_id}/run`
* **Description:** Manually forces execution of the recovery engines for testing purposes.
* **Response (200 OK):**
  ```json
  {
    "transaction_id": "txn_89ab32cde12",
    "action_proposed": {
      "type": "RETRY_PAYMENT",
      "channel": "API_RETRY"
    },
    "guardrail_decision": {
      "allowed": true,
      "reason": "All checks passed. Cooldown is satisfied. Under retry threshold."
    },
    "execution_status": "PENDING"
  }
  ```

---

## 5. Simulation & Batch Ingestion API

### Generate Synthetic Dataset
* **Endpoint:** `POST /api/v1/simulation/generate`
* **Description:** Seeds the local database with a configurable batch of failed payments and checkouts.
* **Request Body:**
  ```json
  {
    "batch_size": 50,
    "seed": 42,
    "failure_distribution": {
      "GATEWAY_TIMEOUT": 0.2,
      "INSUFFICIENT_FUNDS": 0.3,
      "OTP_FAILURE": 0.1,
      "PAYMENT_CANCELLED": 0.2,
      "ABANDONED": 0.2
    }
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "generated_count": 50,
    "revenue_at_risk": 142850.00
  }
  ```

### Run Active Simulation
* **Endpoint:** `POST /api/v1/simulation/run`
* **Description:** Kicks off the recovery engines for all currently pending at-risk transactions.
* **Response (202 Accepted):**
  ```json
  {
    "status": "running",
    "total_batch_size": 50,
    "running_in_background": true
  }
  ```

---

## 6. Metrics API

### Aggregated Performance Summary
* **Endpoint:** `GET /api/v1/metrics/summary`
* **Response (200 OK):**
  ```json
  {
    "total_transactions": 150,
    "at_risk_transactions": 50,
    "recovered_transactions": 38,
    "unrecoverable_transactions": 12,
    "recovery_rate": 76.0,
    "revenue_at_risk": 150000.00,
    "revenue_recovered": 114000.00,
    "recovery_by_cause": {
      "GATEWAY_TIMEOUT": { "at_risk": 10, "recovered": 9, "rate": 90.0 },
      "INSUFFICIENT_FUNDS": { "at_risk": 15, "recovered": 8, "rate": 53.3 },
      "ABANDONED": { "at_risk": 10, "recovered": 6, "rate": 60.0 }
    },
    "recovery_by_action": {
      "RETRY_PAYMENT": { "triggered": 18, "success": 16, "rate": 88.8 },
      "NUDGE_CUSTOMER": { "triggered": 32, "success": 22, "rate": 68.75 }
    }
  }
  ```
