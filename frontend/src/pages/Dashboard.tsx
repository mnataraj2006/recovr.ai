import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMetrics } from '../hooks/useMetrics';
import { useTransactions } from '../hooks/useTransactions';
import { MetricCards } from '../components/dashboard/MetricCards';
import { SimulationHistory } from '../components/dashboard/SimulationHistory';
import { TransactionTable } from '../components/transactions/TransactionTable';

export function Dashboard() {
  const navigate = useNavigate();
  const [showHistory, setShowHistory] = useState(false);

  const {
    metrics,
    transactions,
    simulationHistory,
    loading,
    simulating,
    statusFilter,
    setStatusFilter,
    refresh,
    triggerSimulation,
    clearData,
  } = useMetrics();

  const { expandedTxnId, txnAudits, handleRowClick } = useTransactions();

  return (
    <div className="p-6 lg:p-8 space-y-6 animate-fade-in max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-[rgba(125,211,252,0.08)]">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-[#e0e8f0] tracking-tight">Dashboard</h1>
          <p className="text-[#a0b4c4] mt-1 text-sm">Autonomous Payment Degradation & Checkout Recovery System</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => navigate('/analytics')}
            className="glass-panel px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 text-[#a0b4c4] hover:text-[#7dd3fc] transition-all border border-[rgba(125,211,252,0.12)] glow-hover"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>analytics</span>
            View Analytics
          </button>
          <button
            onClick={clearData}
            className="glass-panel p-2.5 hover:bg-[rgba(255,107,107,0.15)] transition border border-[rgba(255,107,107,0.2)] text-[#ff6b6b] rounded-xl glow-hover flex items-center gap-1.5 text-xs font-semibold"
            title="Clear all test cohorts and reset database"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>delete_sweep</span>
            Clear Test Data
          </button>
          <button
            onClick={refresh}
            className="glass-panel p-2.5 hover:bg-[rgba(125,211,252,0.08)] transition border border-[rgba(125,211,252,0.12)] text-[#a0b4c4] rounded-xl glow-hover"
            title="Refresh Dashboard Data"
          >
            <span className={`material-symbols-outlined ${loading ? 'animate-spin' : ''}`} style={{ fontSize: 20 }}>refresh</span>
          </button>

          <button
            onClick={triggerSimulation}
            disabled={simulating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-[#001f2e] transition active:scale-95 disabled:opacity-50 shadow-lg"
            style={{
              background: simulating
                ? 'rgba(125,211,252,0.5)'
                : 'linear-gradient(135deg, #7dd3fc 0%, #38bdf8 100%)',
              boxShadow: '0 0 20px rgba(125,211,252,0.2)',
            }}
          >
            <span className={`material-symbols-outlined ${simulating ? 'animate-spin' : ''}`} style={{ fontSize: 18 }}>
              {simulating ? 'settings' : 'play_arrow'}
            </span>
            {simulating ? 'Simulating Cohort...' : 'Trigger Simulation Cohort'}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <MetricCards metrics={metrics} />

      {/* Action Bar / Secondary Panel Toggle */}
      <div className="flex items-center justify-between text-xs text-[#a0b4c4] border-b border-[rgba(125,211,252,0.06)] pb-2">
        <span className="font-semibold uppercase tracking-wider text-[10px] text-[#7dd3fc]">Live Recovery Monitoring</span>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex items-center gap-1.5 hover:text-[#7dd3fc] transition-colors"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>history</span>
          {showHistory ? 'Hide Cohort Runs' : `View Cohort Execution History (${simulationHistory.length})`}
        </button>
      </div>

      {/* Collapsible Cohort Simulation History */}
      {showHistory && (
        <div className="animate-slide-in">
          <SimulationHistory history={simulationHistory} />
        </div>
      )}

      {/* Main Transaction Explorer */}
      <TransactionTable
        transactions={transactions}
        expandedTxnId={expandedTxnId}
        txnAudits={txnAudits}
        statusFilter={statusFilter}
        onRowClick={handleRowClick}
        onFilterChange={setStatusFilter}
      />
    </div>
  );
}

