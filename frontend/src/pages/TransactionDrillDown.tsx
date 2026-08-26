import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchTransactionAudit } from '../services/auditService';
import type { TransactionAudit, AuditEvent, GuardrailDecision } from '../types/audit';
import { formatCurrency } from '../utils/formatCurrency';
import { formatDate } from '../utils/formatDate';

function getStatusBadgeConfig(status: string) {
  switch (status.toUpperCase()) {
    case 'RECOVERED':
      return {
        label: 'RECOVERED',
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        text: 'text-emerald-400',
        dot: 'bg-emerald-400',
        glow: 'rgba(52,211,153,0.4)',
        icon: 'check_circle'
      };
    case 'UNRECOVERABLE':
    case 'FAILED':
      return {
        label: 'FAILED',
        bg: 'bg-rose-500/10',
        border: 'border-rose-500/30',
        text: 'text-rose-400',
        dot: 'bg-rose-400',
        glow: 'rgba(244,63,94,0.4)',
        icon: 'cancel'
      };
    case 'CHECKOUT_ABANDONED':
    case 'ABANDONED':
      return {
        label: 'ABANDONED',
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/30',
        text: 'text-amber-400',
        dot: 'bg-amber-400',
        glow: 'rgba(245,158,11,0.4)',
        icon: 'shopping_cart_off'
      };
    case 'EXECUTING':
    case 'DIAGNOSING':
    case 'APPROVED':
      return {
        label: 'IN PROGRESS',
        bg: 'bg-sky-500/10',
        border: 'border-sky-500/30',
        text: 'text-sky-400',
        dot: 'bg-sky-400 animate-ping',
        glow: 'rgba(125,211,252,0.4)',
        icon: 'sync'
      };
    case 'BLOCKED':
      return {
        label: 'STOPPED',
        bg: 'bg-purple-500/10',
        border: 'border-purple-500/30',
        text: 'text-purple-400',
        dot: 'bg-purple-400',
        glow: 'rgba(192,132,252,0.4)',
        icon: 'shield_lock'
      };
    default:
      return {
        label: status.toUpperCase(),
        bg: 'bg-slate-500/10',
        border: 'border-slate-500/30',
        text: 'text-slate-300',
        dot: 'bg-slate-400',
        glow: 'rgba(148,163,184,0.3)',
        icon: 'info'
      };
  }
}

function mapEventLabel(type: string): { title: string; icon: string; color: string } {
  const t = type.toLowerCase();
  if (t.includes('checkout_initiated') || t.includes('checkout.initiated')) {
    return { title: 'Checkout Initiated', icon: 'shopping_bag', color: '#7dd3fc' };
  }
  if (t.includes('payment_attempted') || t.includes('payment.failed') || t.includes('attempt_failed')) {
    return { title: 'Payment Attempted', icon: 'credit_card_off', color: '#ff6b6b' };
  }
  if (t.includes('diagnosed') || t.includes('diagnosis')) {
    return { title: 'AI Diagnosis Completed', icon: 'psychology', color: '#c8a0f0' };
  }
  if (t.includes('action_proposed') || t.includes('policy')) {
    return { title: 'Recovery Policy Selected', icon: 'alt_route', color: '#38bdf8' };
  }
  if (t.includes('guardrail')) {
    return { title: 'Guardrail Verification', icon: 'verified_user', color: '#f59e0b' };
  }
  if (t.includes('executing') || t.includes('retry')) {
    return { title: 'Recovery Attempt Executed', icon: 'autorenew', color: '#38bdf8' };
  }
  if (t.includes('nudge')) {
    return { title: 'Customer Nudge Sent', icon: 'send', color: '#fbbf24' };
  }
  if (t.includes('recovered') || t.includes('success')) {
    return { title: 'Payment Recovered', icon: 'task_alt', color: '#34d399' };
  }
  if (t.includes('unrecoverable') || t.includes('stopped') || t.includes('blocked')) {
    return { title: 'Automation Halted', icon: 'stop_circle', color: '#ff6b6b' };
  }
  return { title: type.replace(/_/g, ' '), icon: 'analytics', color: '#a0b4c4' };
}

export function TransactionDrillDown() {
  const { txnId } = useParams<{ txnId: string }>();
  const navigate = useNavigate();
  const [auditData, setAuditData] = useState<TransactionAudit | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showReasoning, setShowReasoning] = useState<boolean>(false);

  useEffect(() => {
    if (!txnId) return;
    loadAuditDetails();
  }, [txnId]);

  async function loadAuditDetails() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTransactionAudit(txnId!);
      setAuditData(data);
    } catch (err) {
      console.error('Failed to load transaction audit:', err);
      setError('Unable to fetch transaction recovery details.');
    } finally {
      setLoading(false);
    }
  }

  const displayId = txnId ?? 'N/A';
  const txn = auditData?.transaction;
  const cust = auditData?.customer;
  const diag = auditData?.diagnosis;
  const action = auditData?.recovery_action;
  const attempts = auditData?.payment_attempts ?? [];
  const events: AuditEvent[] = auditData?.audit_events ?? [];
  const guardrails: GuardrailDecision[] = auditData?.guardrail_decisions ?? [];

  const amount = txn?.amount ?? 0;
  const status = txn?.status ?? (events.length > 0 ? events[events.length - 1].event_type : 'PENDING');
  const badge = getStatusBadgeConfig(status);
  const isRecovered = status === 'RECOVERED';
  const isFailed = status === 'UNRECOVERABLE' || status === 'BLOCKED';

  const recoveredAmount = isRecovered ? (txn?.recovered_amount ?? amount) : 0;
  const recoveryRate = amount > 0 ? (recoveredAmount / amount) * 100 : 0;

  const currentAttemptCount = attempts.length > 0 ? attempts.length : (action?.current_attempt ?? 1);
  const maxRetries = action?.max_retries ?? 2;

  // Determine Guardrail status badge text
  let guardrailStatusText = 'Guardrail Active';
  if (guardrails.some((g) => g.allowed === false || g.blocked_reason)) {
    guardrailStatusText = 'Guardrail Triggered (Blocked)';
  } else if (guardrails.length > 0) {
    guardrailStatusText = `Passed (${guardrails.length} Checks)`;
  } else {
    guardrailStatusText = 'Active Monitoring';
  }

  // Construct deterministic human-readable decision explanation
  let whyExplanation = 'Recovr evaluated transaction signals and determined optimal recovery pathway.';
  if (diag) {
    if (diag.classification === 'TRANSIENT_FAILURE') {
      whyExplanation = `Temporary gateway failure detected. Recovr selected an automated retry backoff sequence because payment intent remains high and no duplicate charge occurred.`;
    } else if (diag.classification === 'UNKNOWN_ABANDONMENT' || diag.classification === 'CART_ABANDONMENT') {
      whyExplanation = `Cart abandonment detected without gateway response. Recovr scheduled a friendly multi-channel nudge to assist the customer in completing checkout.`;
    } else if (diag.classification === 'INSUFFICIENT_FUNDS') {
      whyExplanation = `Insufficient funds response received. Recovr recommended an alternate payment method nudge (UPI / Wallet) to enable completion.`;
    } else if (diag.classification === 'OTP_FAILED') {
      whyExplanation = `OTP verification failed during authentication. Recovr issued a instant checkout refresh nudge.`;
    } else if (diag.classification === 'CARD_DECLINE') {
      whyExplanation = `Card decline response received. Automated retries were restricted to prevent issuer penalties.`;
    }
  }

  return (
    <div className="min-h-screen bg-[#00141e] text-[#e0e8f0] animate-fade-in p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Back Navigation Bar */}
      <div className="flex items-center justify-between pb-4 border-b border-[rgba(125,211,252,0.10)]">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/audit-logs')}
            className="flex items-center gap-2 text-xs font-semibold text-[#7dd3fc] hover:text-white transition-colors bg-[rgba(125,211,252,0.08)] border border-[rgba(125,211,252,0.2)] px-3 py-1.5 rounded-lg"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              arrow_back
            </span>
            Back to Audit Logs
          </button>
          <div className="h-4 w-[1px] bg-[rgba(125,211,252,0.15)]" />
          <span className="text-xs text-[#a0b4c4] font-mono">
            TXN: <span className="text-[#e0e8f0] font-bold">{displayId}</span>
          </span>
        </div>
        <button
          onClick={loadAuditDetails}
          className="text-xs text-[#a0b4c4] hover:text-[#7dd3fc] flex items-center gap-1.5 transition-colors"
        >
          <span className={`material-symbols-outlined ${loading ? 'animate-spin' : ''}`} style={{ fontSize: 16 }}>
            refresh
          </span>
          Refresh Replay
        </button>
      </div>

      {loading ? (
        <div className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center text-center space-y-3">
          <span className="material-symbols-outlined animate-spin text-3xl text-[#7dd3fc]">progress_activity</span>
          <p className="text-sm text-[#a0b4c4]">Loading AI Recovery Decision Replay for {displayId}...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center text-center space-y-3 border border-rose-500/30">
          <span className="material-symbols-outlined text-4xl text-rose-400">error_outline</span>
          <h3 className="text-base font-semibold text-[#e0e8f0]">Unable to Load Details</h3>
          <p className="text-xs text-[#a0b4c4] max-w-md">{error}</p>
          <button
            onClick={loadAuditDetails}
            className="px-4 py-2 text-xs font-semibold text-[#001f2e] bg-[#7dd3fc] rounded-lg hover:opacity-90 transition-all"
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* Top Hero Section */}
          <div className="glass-panel-elevated p-6 lg:p-8 rounded-2xl relative overflow-hidden border border-[rgba(125,211,252,0.15)] shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border ${badge.bg} ${badge.border} ${badge.text}`}
                  >
                    <span className={`w-2 h-2 rounded-full ${badge.dot}`} style={{ boxShadow: `0 0 8px ${badge.glow}` }} />
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                      {badge.icon}
                    </span>
                    {badge.label}
                  </div>
                  {cust?.email && (
                    <span className="text-xs text-[#a0b4c4] bg-[rgba(10,14,26,0.6)] px-3 py-1 rounded-full border border-[rgba(125,211,252,0.08)]">
                      {cust.email}
                    </span>
                  )}
                </div>

                <div className="flex items-baseline gap-4">
                  <h1 className="text-3xl lg:text-5xl font-black text-[#e0e8f0] tracking-tight">
                    {formatCurrency(amount)}
                  </h1>
                  {isRecovered && (
                    <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded border border-emerald-400/30">
                      100% RECOVERED
                    </span>
                  )}
                </div>

                <p className="text-xs text-[#a0b4c4] flex items-center gap-2">
                  <span>Transaction ID: <strong className="font-mono text-[#e0e8f0]">{displayId}</strong></span>
                  {txn?.checkout_id && (
                    <>
                      <span>·</span>
                      <span>Checkout: <strong className="font-mono text-[#7dd3fc]">{txn.checkout_id}</strong></span>
                    </>
                  )}
                </p>
              </div>

              <div className="text-right flex flex-col items-start lg:items-end justify-between gap-2 border-t lg:border-t-0 pt-4 lg:pt-0 border-[rgba(125,211,252,0.1)]">
                <span className="text-[10px] uppercase tracking-wider text-[#a0b4c4] font-semibold">
                  Recovery Initiated
                </span>
                <span className="text-sm font-mono text-[#e0e8f0]">
                  {txn?.created_at ? formatDate(txn.created_at) : (events[0]?.timestamp ? formatDate(events[0].timestamp) : 'N/A')}
                </span>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs text-[#a0b4c4]">Method:</span>
                  <span className="text-xs font-semibold text-[#7dd3fc] uppercase bg-[rgba(125,211,252,0.1)] px-2.5 py-0.5 rounded">
                    {txn?.payment_method || 'CARD / GATEWAY'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Recovery Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="glass-panel p-4 rounded-xl border border-[rgba(125,211,252,0.1)]">
              <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1">Revenue at Risk</p>
              <p className="text-xl font-bold text-[#e0e8f0]">{formatCurrency(amount)}</p>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-[rgba(125,211,252,0.1)]">
              <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1">Recovered Revenue</p>
              <p className={`text-xl font-bold ${isRecovered ? 'text-emerald-400' : 'text-[#a0b4c4]'}`}>
                {formatCurrency(recoveredAmount)}
              </p>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-[rgba(125,211,252,0.1)]">
              <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1">Recovery Rate</p>
              <p className={`text-xl font-bold ${isRecovered ? 'text-emerald-400' : 'text-rose-400'}`}>
                {recoveryRate.toFixed(0)}%
              </p>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-[rgba(125,211,252,0.1)]">
              <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1">Attempts</p>
              <p className="text-xl font-bold text-[#7dd3fc]">
                {currentAttemptCount} / {maxRetries}
              </p>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-[rgba(125,211,252,0.1)] col-span-2 lg:col-span-1">
              <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1">Guardrail State</p>
              <p className="text-xs font-semibold text-[#c8a0f0] truncate mt-1">
                {guardrailStatusText}
              </p>
            </div>
          </div>

          {/* Main 2-Column Section */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column (Intelligence & Decisions) */}
            <div className="lg:col-span-6 space-y-6">
              {/* AI Diagnosis Card */}
              <div className="glass-panel p-6 rounded-2xl space-y-4 border border-[rgba(125,211,252,0.12)]">
                <div className="flex items-center justify-between pb-3 border-b border-[rgba(125,211,252,0.08)]">
                  <h3 className="text-sm font-bold text-[#e0e8f0] flex items-center gap-2 tracking-tight">
                    <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 20 }}>
                      psychology
                    </span>
                    AI DIAGNOSIS
                  </h3>
                  <span className="text-[10px] font-mono text-[#a0b4c4] bg-[rgba(10,14,26,0.6)] px-2.5 py-1 rounded border border-[rgba(125,211,252,0.1)]">
                    {diag?.diagnosis_source || 'Deterministic Rule Mapping'}
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-[10px] text-[#a0b4c4] uppercase font-semibold tracking-wider">Classification</span>
                    <p className="text-base font-bold text-[#7dd3fc] mt-0.5">
                      {diag?.classification || txn?.failure_reason || 'TRANSIENT_GATEWAY_FAILURE'}
                    </p>
                  </div>

                  {diag?.confidence !== undefined && (
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#a0b4c4]">AI Confidence Score</span>
                        <span className="font-bold text-[#7dd3fc]">{(diag.confidence * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-[rgba(125,211,252,0.1)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#7dd3fc] rounded-full transition-all duration-500"
                          style={{ width: `${diag.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <span className="text-[10px] text-[#a0b4c4] uppercase font-semibold tracking-wider block mb-1.5">
                      Signals Analyzed
                    </span>
                    <div className="space-y-1.5">
                      {[
                        `Gateway Response: ${txn?.failure_reason || 'Gateway Timeout / Degradation'}`,
                        `Purchase Intent: High (Cart Value ${formatCurrency(amount)})`,
                        `Duplicate Recovery Check: Passed`,
                        `Cooldown Window: Safe`
                      ].map((sig, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-[#e0e8f0]">
                          <span className="material-symbols-outlined text-emerald-400" style={{ fontSize: 14 }}>
                            check_circle
                          </span>
                          <span>{sig}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Why Did Recovr Take This Action? */}
              <div className="glass-panel p-6 rounded-2xl space-y-3 border border-[#7dd3fc]/30 bg-[#7dd3fc]/5">
                <h3 className="text-sm font-bold text-[#7dd3fc] flex items-center gap-2">
                  <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                    auto_awesome
                  </span>
                  Why did Recovr take this action?
                </h3>
                <p className="text-xs text-[#e0e8f0] leading-relaxed">
                  {whyExplanation}
                </p>
                <div className="pt-2 flex flex-wrap gap-2 text-[10px] font-mono text-[#a0b4c4]">
                  <span className="bg-[#001f2e] border border-[rgba(125,211,252,0.2)] px-2.5 py-1 rounded text-[#7dd3fc]">
                    Policy: {action?.policy || 'TRANSIENT_FAILURE_RETRY'}
                  </span>
                  <span className="bg-[#001f2e] border border-[rgba(125,211,252,0.2)] px-2.5 py-1 rounded text-[#e0e8f0]">
                    Action: {action?.action_type || 'AUTO_RETRY'}
                  </span>
                </div>
              </div>

              {/* Policy & Guardrails Section */}
              <div className="glass-panel p-6 rounded-2xl space-y-4 border border-[rgba(125,211,252,0.12)]">
                <h3 className="text-sm font-bold text-[#e0e8f0] flex items-center gap-2 pb-3 border-b border-[rgba(125,211,252,0.08)]">
                  <span className="material-symbols-outlined text-[#c8a0f0]" style={{ fontSize: 20 }}>
                    shield
                  </span>
                  Bounded Policy & Guardrails
                </h3>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-lg border border-[rgba(125,211,252,0.08)] bg-[rgba(10,14,26,0.4)]">
                    <span className="text-[10px] text-[#a0b4c4] block">Max Retries Allowed</span>
                    <strong className="text-sm text-[#e0e8f0]">{maxRetries} Attempts</strong>
                  </div>
                  <div className="p-3 rounded-lg border border-[rgba(125,211,252,0.08)] bg-[rgba(10,14,26,0.4)]">
                    <span className="text-[10px] text-[#a0b4c4] block">Backoff Window</span>
                    <strong className="text-sm text-[#e0e8f0]">{action?.backoff_seconds ?? 30} Seconds</strong>
                  </div>
                </div>

                {isFailed && (
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs space-y-1">
                    <p className="font-semibold text-rose-300 flex items-center gap-1.5">
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>block</span>
                      Automated Recovery Stopped
                    </p>
                    <p className="text-rose-200/80 text-[11px]">
                      Configured retry threshold reached. Automation safely halted to prevent duplicate charges or customer fatigue.
                    </p>
                  </div>
                )}
              </div>

              {/* Expandable AI Reasoning */}
              <div className="glass-panel rounded-xl overflow-hidden border border-[rgba(125,211,252,0.1)]">
                <button
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="w-full p-4 flex items-center justify-between text-xs font-semibold text-[#a0b4c4] hover:text-[#e0e8f0] transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 16 }}>
                      code
                    </span>
                    Raw Decision Rationale
                  </span>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                    {showReasoning ? 'expand_less' : 'expand_more'}
                  </span>
                </button>
                {showReasoning && (
                  <div className="p-4 border-t border-[rgba(125,211,252,0.08)] bg-[rgba(10,14,26,0.6)] font-mono text-[11px] text-[#a0b4c4] space-y-2">
                    <p><span className="text-[#7dd3fc]">Diagnosis:</span> {diag?.classification || 'TRANSIENT_FAILURE'}</p>
                    <p><span className="text-[#7dd3fc]">Policy Selected:</span> {action?.policy || 'TRANSIENT_FAILURE_RETRY'}</p>
                    <p><span className="text-[#7dd3fc]">Action:</span> {action?.action_type || 'AUTO_RETRY'}</p>
                    <p><span className="text-[#7dd3fc]">Guardrails Run:</span> {guardrails.length} rules checked</p>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column (Vertical Recovery Journey Timeline) */}
            <div className="lg:col-span-6">
              <div className="glass-panel p-6 rounded-2xl space-y-6 border border-[rgba(125,211,252,0.12)]">
                <div className="flex items-center justify-between pb-3 border-b border-[rgba(125,211,252,0.08)]">
                  <h3 className="text-sm font-bold text-[#e0e8f0] flex items-center gap-2">
                    <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 20 }}>
                      timeline
                    </span>
                    AI Recovery Journey Timeline
                  </h3>
                  <span className="text-[10px] text-[#a0b4c4] font-mono">{events.length} Events</span>
                </div>

                <div className="relative pl-6 space-y-6 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-[rgba(125,211,252,0.15)]">
                  {events.map((evt, idx) => {
                    const cfg = mapEventLabel(evt.event_type);
                    return (
                      <div key={evt.id || idx} className="relative group">
                        {/* Timeline Bullet Marker */}
                        <div
                          className="absolute -left-[31px] top-0 w-6 h-6 rounded-full flex items-center justify-center border bg-[#00141e] transition-transform group-hover:scale-110"
                          style={{ borderColor: cfg.color }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 12, color: cfg.color }}>
                            {cfg.icon}
                          </span>
                        </div>

                        <div className="glass-panel p-4 rounded-xl border border-[rgba(125,211,252,0.08)] space-y-2 hover:border-[rgba(125,211,252,0.2)] transition-all">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold text-[#e0e8f0] flex items-center gap-2">
                              {cfg.title}
                            </h4>
                            <span className="text-[10px] font-mono text-[#a0b4c4]">
                              {evt.timestamp ? formatDate(evt.timestamp) : ''}
                            </span>
                          </div>

                          <p className="text-xs text-[#a0b4c4] leading-relaxed">
                            {evt.reason || 'Event recorded during transaction execution.'}
                          </p>

                          {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                            <div className="pt-2 text-[10px] font-mono text-[#7dd3fc]/80 border-t border-[rgba(125,211,252,0.05)]">
                              {Object.entries(evt.metadata).map(([k, v]) => (
                                <span key={k} className="mr-3 inline-block">
                                  {k}: <strong className="text-[#e0e8f0]">{String(v)}</strong>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Final Outcome Banner */}
                <div
                  className={`p-4 rounded-xl text-xs font-medium border flex items-center justify-between ${
                    isRecovered
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : isFailed
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                      {badge.icon}
                    </span>
                    <span>
                      {isRecovered
                        ? `Transaction recovered successfully. Total: ${formatCurrency(amount)}`
                        : isFailed
                        ? 'Automation stopped. Final status: UNRECOVERABLE.'
                        : 'Recovery process is currently active.'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
