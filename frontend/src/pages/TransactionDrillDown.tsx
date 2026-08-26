import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchTransactionAudit } from '../services/auditService';
import type { TransactionAudit, AuditEvent, GuardrailDecision } from '../types/audit';
import { formatDate } from '../utils/formatDate';

export function TransactionDrillDown() {
  const { txnId } = useParams<{ txnId: string }>();
  const navigate = useNavigate();
  const [auditData, setAuditData] = useState<TransactionAudit | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!txnId) return;
    setLoading(true);
    setError(null);
    fetchTransactionAudit(txnId)
      .then((data) => {
        setAuditData(data);
      })
      .catch((err) => {
        console.error('Failed to load transaction audit:', err);
        setError('Could not fetch audit details for this transaction.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [txnId]);

  const displayId = txnId ?? 'N/A';

  const events: AuditEvent[] = auditData?.audit_events ?? [];
  const guardrails: GuardrailDecision[] = auditData?.guardrail_decisions ?? [];

  return (
    <div
      className="h-[calc(100vh-53px)] overflow-y-auto flex flex-col gap-0 animate-fade-in"
      style={{ background: '#0a0e1a' }}
    >
      {/* Page Header Bar */}
      <div className="flex items-center justify-between px-6 lg:px-8 py-4 border-b border-[rgba(125,211,252,0.10)] flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-[#a0b4c4] hover:text-[#7dd3fc] transition-colors">
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>arrow_back</span>
          </button>
          <div>
            <h2 className="text-lg font-bold text-[#e0e8f0] flex items-center gap-2 tracking-tight">
              <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 22 }}>memory</span>
              Transaction Audit Trail
            </h2>
            <p className="text-[10px] text-[#a0b4c4] font-mono mt-0.5">
              TXN_ID: {displayId}
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-[#a0b4c4]">
          <span className="material-symbols-outlined animate-spin text-3xl mb-3 text-[#7dd3fc]">sync</span>
          <p className="text-sm">Fetching live transaction audit log...</p>
        </div>
      ) : error || (!events.length && !guardrails.length) ? (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-[#a0b4c4]">
          <span className="material-symbols-outlined text-4xl mb-3 text-[#a0b4c4]/40">error_outline</span>
          <h3 className="text-base font-semibold text-[#e0e8f0] mb-1">No Audit Data Found</h3>
          <p className="text-xs max-w-md text-center text-[#a0b4c4]/70 mb-4">
            {error || `No audit events or guardrail decisions have been logged for transaction ${displayId}.`}
          </p>
          <button
            onClick={() => navigate('/audit-logs')}
            className="px-4 py-2 rounded-lg text-xs text-[#7dd3fc] border border-[rgba(125,211,252,0.3)] bg-[rgba(125,211,252,0.1)] hover:bg-[rgba(125,211,252,0.2)] transition-all"
          >
            Back to Audit Logs
          </button>
        </div>
      ) : (
        /* 3-Column Grid */
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-6 lg:p-8 min-h-0">
          {/* Left: Context Metadata */}
          <div className="lg:col-span-4">
            <div className="glass-panel-elevated rounded-xl p-5 h-full flex flex-col">
              <h3 className="text-[10px] uppercase tracking-widest text-[#7dd3fc] font-semibold mb-4 pb-2 border-b border-[rgba(125,211,252,0.1)] flex items-center gap-2">
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>data_object</span>
                Context & Summary
              </h3>
              <div className="space-y-4 flex-1">
                <div>
                  <p className="text-[10px] text-[#a0b4c4] mb-1">Transaction ID</p>
                  <p className="text-xs font-mono text-[#e0e8f0] break-all p-2 rounded border border-[rgba(125,211,252,0.1)]"
                    style={{ background: 'rgba(10,14,26,0.6)' }}>
                    {displayId}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-[#a0b4c4] mb-1">Audit Events Recorded</p>
                  <p className="text-lg font-bold text-[#e0e8f0]">{events.length} Events</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#a0b4c4] mb-1">Guardrail Evaluated</p>
                  <p className="text-sm font-semibold text-[#e0e8f0]">
                    {guardrails.length > 0 ? (
                      <span className="text-emerald-400">PASSED ({guardrails.length} checks)</span>
                    ) : (
                      <span className="text-[#a0b4c4]">None</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Center: AI Agent Logic Timeline */}
          <div className="lg:col-span-8">
            <div className="glass-panel-elevated rounded-xl flex flex-col h-full overflow-hidden">
              {/* Tab header */}
              <div className="flex items-center justify-between px-5 py-3 border-b border-[rgba(125,211,252,0.1)]"
                style={{ background: 'rgba(20,28,46,0.5)' }}>
                <h3 className="text-sm font-semibold text-[#e0e8f0] flex items-center gap-2">
                  <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 18 }}>route</span>
                  Live Event Timeline
                </h3>
              </div>

              <div className="flex-1 p-6 overflow-y-auto relative space-y-6">
                {events.map((evt, idx) => (
                  <div key={evt.id || idx} className="relative pl-8 border-l border-[rgba(125,211,252,0.2)]">
                    {/* Circle marker */}
                    <div
                      className="absolute -left-[9px] top-0 w-4 h-4 rounded-full flex items-center justify-center bg-[#0f1524] border border-[#7dd3fc]"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-[#7dd3fc]" />
                    </div>

                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-bold text-[#e0e8f0]">{evt.event_type}</h4>
                      <span className="text-[10px] text-[#a0b4c4] font-mono">
                        {evt.timestamp ? formatDate(evt.timestamp) : ''}
                      </span>
                    </div>

                    <p className="text-xs text-[#a0b4c4] mb-2">{evt.reason || 'System event recorded'}</p>

                    <div className="rounded-lg p-3 font-mono text-[11px] leading-relaxed border border-[rgba(125,211,252,0.1)]"
                      style={{ background: 'rgba(10,14,26,0.6)' }}
                    >
                      <p className="text-[#7dd3fc]">Actor: {evt.actor}</p>
                      <p className="text-[#a0b4c4]">Source: {evt.source}</p>
                      {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                        <pre className="text-[10px] text-[#a0b4c4]/80 mt-1 whitespace-pre-wrap">
                          {JSON.stringify(evt.metadata, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}

                {guardrails.map((g, idx) => (
                  <div key={g.id || idx} className="mt-6 pt-6 border-t border-[rgba(125,211,252,0.1)]">
                    <h4 className="text-xs uppercase tracking-wider font-semibold text-[#c8a0f0] mb-3">Guardrail Evaluation</h4>
                    <div className="space-y-2">
                      {g.checks_run?.map((check, i) => (
                        <div key={i} className="flex items-center justify-between p-2.5 rounded border border-[rgba(125,211,252,0.06)]"
                          style={{ background: 'rgba(10,14,26,0.4)' }}>
                          <span className="text-xs font-mono text-[#e0e8f0]">{check.name}</span>
                          <span className={`text-[10px] font-bold ${check.passed ? 'text-[#7dd3fc]' : 'text-[#ff6b6b]'}`}>
                            {check.passed ? 'PASS' : 'FAIL'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

