import { Clock } from 'lucide-react';
import { formatCurrency } from '../../utils/formatCurrency';
import { formatTime } from '../../utils/formatDate';
import type { SimulationHistoryItem } from '../../types/metrics';

interface SimulationHistoryProps {
  history: SimulationHistoryItem[];
}

/**
 * Panel listing past cohort simulation run results.
 * Extracted from App.tsx lines 330–360.
 */
export function SimulationHistory({ history }: SimulationHistoryProps) {
  return (
    <div className="glass-panel p-6">
      <h3 className="text-lg font-bold mb-4 text-zinc-200">Cohort Execution Runs</h3>
      <div className="space-y-4 max-h-[280px] overflow-y-auto pr-1">
        {history.length > 0 ? (
          history.map((item) => (
            <div
              key={item.id}
              className="p-3 bg-white/5 border border-white/5 rounded-xl flex justify-between items-center hover:border-white/10 transition"
            >
              <div>
                <span className="text-xs font-mono text-zinc-400 block">{item.id}</span>
                <span className="text-xs text-zinc-500">
                  {formatTime(item.created_at)} · Risk {formatCurrency(item.total_revenue_at_risk)}
                </span>
              </div>
              <div className="text-right">
                <span className="text-xs font-bold text-emerald-400 block">
                  +{formatCurrency(item.total_recovered_revenue)}
                </span>
                <span className="text-[10px] text-zinc-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                  {(item.recovery_rate * 100).toFixed(0)}% Recov.
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-48 text-zinc-500">
            <Clock size={24} className="opacity-30 mb-1" />
            <p className="text-xs">No execution history recorded.</p>
          </div>
        )}
      </div>
    </div>
  );
}
