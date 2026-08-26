export interface AuditEvent {
  id: string;
  event_type: string;
  actor: string;
  source: string;
  reason: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface GuardrailDecision {
  id: string;
  action_id?: string;
  allowed?: boolean;
  blocked_reason?: string;
  reason?: string;
  checks_run?: Array<{ name: string; passed: boolean }>;
  created_at?: string;
}

export interface TransactionDetails {
  id: string;
  checkout_id?: string;
  customer_id?: string;
  amount: number;
  status: string;
  payment_method?: string;
  failure_reason?: string;
  recovered_amount?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CustomerDetails {
  id: string;
  name?: string;
  email?: string;
  phone?: string;
}

export interface DiagnosisDetails {
  id: string;
  classification: string;
  confidence?: number;
  diagnosis_source?: string;
  signals?: string[];
  reasoning?: string;
  created_at?: string;
}

export interface RecoveryActionDetails {
  id: string;
  policy: string;
  action_type: string;
  max_retries?: number;
  current_attempt?: number;
  backoff_seconds?: number;
  max_nudges?: number;
  reasoning?: string;
  created_at?: string;
}

export interface PaymentAttemptDetails {
  id: string;
  attempt_number: number;
  status: string;
  failure_reason?: string;
  created_at?: string;
}

export interface TransactionAudit {
  transaction_id: string;
  transaction?: TransactionDetails | null;
  customer?: CustomerDetails | null;
  diagnosis?: DiagnosisDetails | null;
  recovery_action?: RecoveryActionDetails | null;
  payment_attempts?: PaymentAttemptDetails[];
  audit_events: AuditEvent[];
  guardrail_decisions: GuardrailDecision[];
}
