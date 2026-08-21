import { AlertTriangle, DollarSign, TrendingUp, ArrowUpRight } from 'lucide-react';
import { formatCurrency } from '../../utils/formatCurrency';
import type { MetricData } from '../../types/metrics';

interface MetricCardsProps {
  metrics: MetricData | null;
}

/**
 * Four KPI metric cards displayed at the top of the dashboard.
 * Extracted from App.tsx lines 242–294.
 */
export function MetricCards({ metrics }: MetricCardsProps) {
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {/* Revenue At Risk */}
      <div className="glass-panel glass-panel-hover p-6 animate-slide-in">
        <div className="flex justify-between items-start mb-4">
          <span className="text-zinc-400 text-sm font-semibold uppercase tracking-wide">Revenue At Risk</span>
          <span className="p-2 bg-yellow-500/10 text-yellow-400 rounded-lg"><AlertTriangle size={18} /></span>
        </div>
        <h3 className="text-3xl font-extrabold font-display">
          {metrics ? formatCurrency(metrics.total_revenue_at_risk) : '₹0'}
        </h3>
        <p className="text-xs text-zinc-500 mt-2">Total failed cart and payment values</p>
      </div>

      {/* Recovered Revenue */}
      <div className="glass-panel glass-panel-hover p-6 animate-slide-in [animation-delay:100ms]">
        <div className="flex justify-between items-start mb-4">
          <span className="text-emerald-400 text-sm font-semibold uppercase tracking-wide">Recovered Revenue</span>
          <span className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg"><DollarSign size={18} /></span>
        </div>
        <h3 className="text-3xl font-extrabold text-emerald-400 font-display">
          {metrics ? formatCurrency(metrics.total_recovered_revenue) : '₹0'}
        </h3>
        <p className="text-xs text-zinc-500 mt-2">Recovered by autonomous actions</p>
      </div>

      {/* Net Recovery Saving */}
      <div className="glass-panel glass-panel-hover p-6 animate-slide-in [animation-delay:200ms]">
        <div className="flex justify-between items-start mb-4">
          <span className="text-blue-400 text-sm font-semibold uppercase tracking-wide">Net Recovery Saving</span>
          <span className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><TrendingUp size={18} /></span>
        </div>
        <h3 className="text-3xl font-extrabold text-blue-400 font-display">
          {metrics ? formatCurrency(metrics.net_recovered_revenue) : '₹0'}
        </h3>
        <p className="text-xs text-zinc-500 mt-2">Subtracting SMS and API retry costs</p>
      </div>

      {/* Recovery Rate / ROI */}
      <div className="glass-panel glass-panel-hover p-6 animate-slide-in [animation-delay:300ms]">
        <div className="flex justify-between items-start mb-4">
          <span className="text-zinc-400 text-sm font-semibold uppercase tracking-wide">Recovery Rate / ROI</span>
          <span className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg"><ArrowUpRight size={18} /></span>
        </div>
        <div className="flex justify-between items-baseline">
          <h3 className="text-3xl font-extrabold text-white font-display">
            {metrics ? `${(metrics.recovery_rate * 100).toFixed(1)}%` : '0%'}
          </h3>
          <span className="text-sm font-bold text-zinc-300 bg-white/5 border border-white/10 px-2 py-0.5 rounded">
            {metrics && metrics.roi > 0 ? `${metrics.roi.toFixed(1)}x ROI` : 'N/A'}
          </span>
        </div>
        <p className="text-xs text-zinc-500 mt-2">
          Cost: {metrics ? formatCurrency(metrics.total_recovery_cost) : '₹0'}{' '}
          ({metrics ? metrics.nudge_count + metrics.retry_count : 0} actions)
        </p>
      </div>
    </section>
  );
}
