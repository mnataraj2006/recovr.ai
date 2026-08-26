import { useMetrics } from '../hooks/useMetrics';
import { formatCurrency } from '../utils/formatCurrency';

export function Analytics() {
  const { metrics, loading, refresh } = useMetrics();

  const totalRevenueAtRisk = metrics?.total_revenue_at_risk ?? 0;
  const totalRecoveredRevenue = metrics?.total_recovered_revenue ?? 0;
  const netRecoveredRevenue = metrics?.net_recovered_revenue ?? 0;
  const recoveryRate = metrics?.transaction_recovery_rate ? (metrics.transaction_recovery_rate * 100).toFixed(1) : '0.0';

  const kpiCards = [
    {
      icon: 'account_balance_wallet',
      color: '#fbbf24',
      glowColor: 'rgba(251,191,36,0.08)',
      label: 'Revenue At Risk',
      value: formatCurrency(totalRevenueAtRisk),
      trend: `${metrics?.at_risk_transactions ?? 0} txns`,
    },
    {
      icon: 'savings',
      color: '#34d399',
      glowColor: 'rgba(52,211,153,0.08)',
      label: 'Revenue Saved',
      value: formatCurrency(totalRecoveredRevenue),
      trend: `${metrics?.recovered_transactions ?? 0} recovered`,
    },
    {
      icon: 'bolt',
      color: '#7dd3fc',
      glowColor: 'rgba(125,211,252,0.08)',
      label: 'Net Revenue Saved',
      value: formatCurrency(netRecoveredRevenue),
      trend: `Cost: ${formatCurrency(metrics?.total_recovery_cost ?? 0)}`,
    },
    {
      icon: 'check_circle',
      color: '#c8a0f0',
      glowColor: 'rgba(200,160,240,0.08)',
      label: 'Recovery Success Rate',
      value: `${recoveryRate}%`,
      trend: metrics && metrics.roi > 0 ? `${metrics.roi.toFixed(1)}x ROI` : 'Stable',
    },
  ];

  const causeEntries = metrics ? Object.entries(metrics.cause_distribution) : [];
  const totalFailures = causeEntries.reduce((acc, [, val]) => acc + val, 0);

  const statusEntries = metrics ? Object.entries(metrics.status_distribution) : [];

  return (
    <div className="p-6 lg:p-8 space-y-6 animate-fade-in max-w-[1400px] mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-[#e0e8f0] tracking-tight">Performance Analytics</h1>
          <p className="text-[#a0b4c4] mt-1 text-sm">Real-time recovery metrics and system efficiency overview.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={refresh}
            className="glass-panel px-4 py-2 rounded-lg text-sm flex items-center gap-2 text-[#7dd3fc] hover:text-[#e0e8f0] transition-colors border border-[rgba(125,211,252,0.2)]"
          >
            <span className={`material-symbols-outlined ${loading ? 'animate-spin' : ''}`} style={{ fontSize: 16 }}>refresh</span>
            Refresh Live Metrics
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((card) => (
          <div key={card.label} className="glass-panel rounded-xl p-5 relative overflow-hidden group transition-all duration-300 glow-hover">
            <div
              className="absolute top-0 right-0 w-32 h-32 rounded-full blur-2xl -mr-16 -mt-16 transition-all pointer-events-none"
              style={{ background: card.glowColor }}
            />
            <div className="flex justify-between items-start mb-4 relative z-10">
              <div className="p-2 rounded-lg border border-[rgba(125,211,252,0.15)]" style={{ background: 'rgba(20,28,46,0.8)' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 22, color: card.color }}>{card.icon}</span>
              </div>
              <span className="text-xs font-medium px-2 py-1 rounded border text-[#a0b4c4] border-[rgba(125,211,252,0.15)]"
                style={{ background: 'rgba(26,36,56,0.8)' }}>
                {card.trend}
              </span>
            </div>
            <div className="relative z-10">
              <p className="text-sm text-[#a0b4c4] mb-1">{card.label}</p>
              <h3 className="text-2xl font-bold text-[#e0e8f0]">
                {card.value}
              </h3>
            </div>
          </div>
        ))}
      </div>

      {/* Charts & Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cause Breakdown Bar / List */}
        <div className="glass-panel-elevated rounded-2xl p-6 lg:col-span-2 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-base font-semibold text-[#e0e8f0]">Root Cause Categorization</h3>
              <p className="text-xs text-[#a0b4c4] mt-0.5">Distribution of failure reasons identified by system diagnosis.</p>
            </div>
          </div>

          <div className="flex-1 flex flex-col justify-center min-h-[220px]">
            {causeEntries.length > 0 ? (
              <div className="space-y-4">
                {causeEntries.map(([cause, count]) => {
                  const pct = totalFailures > 0 ? Math.round((count / totalFailures) * 100) : 0;
                  return (
                    <div key={cause} className="space-y-1.5">
                      <div className="flex justify-between text-xs text-[#e0e8f0]">
                        <span className="font-semibold">{cause.replace(/_/g, ' ')}</span>
                        <span className="text-[#7dd3fc] font-mono">{count} failures ({pct}%)</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-[rgba(125,211,252,0.1)] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            background: 'linear-gradient(90deg, #7dd3fc 0%, #c8a0f0 100%)',
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-[#a0b4c4] py-8">
                <span className="material-symbols-outlined text-3xl mb-2 text-[#a0b4c4]/40">bar_chart</span>
                <p className="text-sm">No root cause failure distribution recorded yet.</p>
                <p className="text-xs text-[#a0b4c4]/70 mt-1">Run a simulation cohort from the dashboard to populate metrics.</p>
              </div>
            )}
          </div>
        </div>

        {/* Status Distribution */}
        <div className="flex flex-col gap-6 lg:col-span-1">
          <div className="glass-panel rounded-2xl p-5 flex-1 flex flex-col">
            <h3 className="text-base font-semibold text-[#e0e8f0] mb-0.5">Status Overview</h3>
            <p className="text-xs text-[#a0b4c4] mb-5">Transaction state counts across all cohorts.</p>
            
            <div className="flex-1 flex flex-col justify-center space-y-3">
              {statusEntries.length > 0 ? (
                statusEntries.map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between p-3 rounded-lg border border-[rgba(125,211,252,0.08)] bg-[rgba(10,14,26,0.5)]">
                    <span className="text-xs font-mono text-[#e0e8f0]">{status}</span>
                    <span className="text-xs font-bold text-[#7dd3fc]">{count}</span>
                  </div>
                ))
              ) : (
                <div className="text-center text-[#a0b4c4] py-6">
                  <span className="material-symbols-outlined text-2xl mb-1 text-[#a0b4c4]/40">pie_chart</span>
                  <p className="text-xs">No status data available yet.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

