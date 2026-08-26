import { Cpu, ShieldCheck, CheckCircle, XCircle } from 'lucide-react';
import { formatTime } from '../../utils/formatDate';
import type { TransactionAudit } from '../../types/audit';

interface TransactionDetailProps {
  audit: TransactionAudit | undefined;
}

/**
 * Expanded transaction detail panel showing the agent decision audit timeline
 * and guardrail shield evaluations.
 * Extracted from App.tsx lines 440–517 (the expanded <tr> content).
 */
export function TransactionDetail({ audit }: TransactionDetailProps) {
  return (
    <tr>
      <td colSpan={7} className="p-0 bg-zinc-950/40 border-b border-white/5">
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">

          {/* Left Panel: Agent Decisions & Audit Timeline */}
          <div>
            <h4 className="text-xs uppercase tracking-wider font-bold text-zinc-400 mb-4 flex items-center gap-1.5">
              <Cpu size={14} className="text-indigo-400" />
              Agent Decisions &amp; Audit Timeline
            </h4>
            <div className="space-y-4 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
              {audit && audit.audit_events.length > 0 ? (
                audit.audit_events.map((evt) => (
                  <div key={evt.id} className="flex gap-4 relative pl-6">
                    <span className="absolute left-1.5 top-1.5 w-3 h-3 bg-indigo-500 rounded-full border-2 border-zinc-950 glow-primary" />
                    <div>
                      <span className="text-xs font-semibold text-zinc-300 block">
                        {evt.event_type.replace(/_/g, ' ')}
                      </span>
                      <p className="text-[11px] text-zinc-400 mt-0.5">{evt.reason}</p>
                      <span className="text-[10px] text-zinc-600 font-mono mt-1 block">
                        Actor: {evt.actor} ({evt.source}) · {formatTime(evt.timestamp)}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-zinc-500 italic pl-4">Loading audit logs...</p>
              )}
            </div>
          </div>

          {/* Right Panel: Guardrail Checks */}
          <div>
            <h4 className="text-xs uppercase tracking-wider font-bold text-zinc-400 mb-4 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-400" />
              Guardrail Shield Evaluations
            </h4>
            <div className="space-y-3">
              {audit && audit.guardrail_decisions.length > 0 ? (
                audit.guardrail_decisions.map((decision) => (
                  <div key={decision.id} className="p-3 bg-white/5 border border-white/5 rounded-xl">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-semibold text-zinc-300">
                        Action: {decision.action_id}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 font-bold rounded ${
                          decision.allowed
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {decision.allowed ? 'APPROVED' : 'BLOCKED'}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 mb-3">{decision.reason}</p>
                    <div className="grid grid-cols-2 gap-2">
                      {decision.checks_run?.map((chk, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px]">
                          {chk.passed ? (
                            <CheckCircle size={12} className="text-emerald-400" />
                          ) : (
                            <XCircle size={12} className="text-rose-400" />
                          )}
                          <span className="text-zinc-500 capitalize">{chk.name.replace(/_/g, ' ')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center p-6 border border-dashed border-white/5 rounded-xl text-zinc-600">
                  <ShieldCheck size={24} className="opacity-20 mb-1" />
                  <p className="text-[11px]">No active guardrail reviews required for this flow.</p>
                </div>
              )}
            </div>
          </div>

        </div>
      </td>
    </tr>
  );
}
