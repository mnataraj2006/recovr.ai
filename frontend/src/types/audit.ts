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
  action_id: string;
  allowed: boolean;
  reason: string;
  checks_run: Array<{ name: string; passed: boolean }>;
  created_at: string;
}

export interface TransactionAudit {
  transaction_id: string;
  audit_events: AuditEvent[];
  guardrail_decisions: GuardrailDecision[];
}
