import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  Activity, 
  DollarSign, 
  ArrowUpRight, 
  Play, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock, 
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Cpu
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

const API_BASE = window.location.port === '5173' || window.location.port === '3000' 
  ? 'http://localhost:8000' 
  : '';

interface MetricData {
  total_revenue_at_risk: number;
  total_recovered_revenue: number;
  net_recovered_revenue: number;
  recovery_rate: number;
  total_recovery_cost: number;
  roi: number;
  nudge_count: number;
  retry_count: number;
  status_distribution: Record<string, number>;
  cause_distribution: Record<string, number>;
}

interface Transaction {
  id: string;
  checkout_id: string;
  amount: number;
  status: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  created_at: string;
  failure_mode?: string;
  action_proposed?: string;
}

interface AuditEvent {
  id: string;
  event_type: string;
  actor: string;
  source: string;
  reason: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

interface GuardrailDecision {
  id: string;
  action_id: string;
  allowed: boolean;
  reason: string;
  checks_run: Array<{ name: string; passed: boolean }>;
  created_at: string;
}

interface TransactionAudit {
  transaction_id: string;
  audit_events: AuditEvent[];
  guardrail_decisions: GuardrailDecision[];
}

interface SimulationHistoryItem {
  id: string;
  created_at: string;
  total_revenue_at_risk: number;
  total_recovered_revenue: number;
  recovery_rate: number;
  cohort_summary: Array<any>;
}

function App() {
  const [metrics, setMetrics] = useState<MetricData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [simulationHistory, setSimulationHistory] = useState<SimulationHistoryItem[]>([]);
  const [expandedTxnId, setExpandedTxnId] = useState<string | null>(null);
  const [txnAudits, setTxnAudits] = useState<Record<string, TransactionAudit>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const fetchDashboardData = async () => {
    try {
      // 1. Fetch Metrics
      const resMetrics = await fetch(`${API_BASE}/api/v1/metrics`);
      const dataMetrics = await resMetrics.json();
      setMetrics(dataMetrics);

      // 2. Fetch Transactions
      const statusQuery = statusFilter ? `?status=${statusFilter}` : '';
      const resTxns = await fetch(`${API_BASE}/api/v1/transactions${statusQuery}`);
      const dataTxns = await resTxns.json();
      setTransactions(dataTxns.transactions || []);

      // 3. Fetch Simulation History
      const resSim = await fetch(`${API_BASE}/api/v1/simulation/history`);
      const dataSim = await resSim.json();
      setSimulationHistory(dataSim || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [statusFilter]);

  const triggerSimulation = async () => {
    setSimulating(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/simulation/run`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchDashboardData();
      }
    } catch (err) {
      console.error('Failed to run batch simulation:', err);
    } finally {
      setSimulating(false);
    }
  };

  const handleRowClick = async (txnId: string) => {
    if (expandedTxnId === txnId) {
      setExpandedTxnId(null);
      return;
    }

    setExpandedTxnId(txnId);
    
    // Fetch Audit Log for the transaction if not cached
    if (!txnAudits[txnId]) {
      try {
        const res = await fetch(`${API_BASE}/api/v1/transactions/${txnId}/audit`);
        const auditData = await res.json();
        setTxnAudits(prev => ({ ...prev, [txnId]: auditData }));
      } catch (err) {
        console.error('Failed to load transaction audit:', err);
      }
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  const getStatusBadge = (status: string) => {
    const defaultClasses = "px-2.5 py-1 text-xs font-semibold rounded-full flex items-center gap-1.5 ";
    switch (status) {
      case "RECOVERED":
      case "SUCCESS":
        return <span className={defaultClasses + "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 glow-success"}><CheckCircle size={12}/> RECOVERED</span>;
      case "UNRECOVERABLE":
        return <span className={defaultClasses + "bg-rose-500/10 text-rose-400 border border-rose-500/20 glow-error"}><XCircle size={12}/> UNRECOVERABLE</span>;
      case "CHECKOUT_ABANDONED":
      case "PAYMENT_FAILED":
        return <span className={defaultClasses + "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 glow-warn"}><AlertTriangle size={12}/> FAILURE DETECTED</span>;
      default:
        return <span className={defaultClasses + "bg-blue-500/10 text-blue-400 border border-blue-500/20 glow-primary"}><Clock size={12}/> {status}</span>;
    }
  };

  // Build chart dataset from cause distribution
  const chartData = metrics ? Object.entries(metrics.cause_distribution).map(([key, val]) => ({
    name: key.replace(/_/g, ' '),
    failures: val,
  })) : [];

  return (
    <div className="min-h-screen p-6 md:p-8">
      {/* 1. Navbar */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 pb-6 border-b border-white/5 animate-slide-in">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-extrabold bg-gradient-to-r from-blue-400 via-indigo-200 to-emerald-400 bg-clip-text text-transparent hover-shine cursor-pointer">
              Recovr.ai
            </h1>
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1.5 uppercase tracking-wider">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
              Agent Active
            </span>
          </div>
          <p className="text-zinc-400 text-sm mt-1">Autonomous Payment Degradation & Checkout Recovery System</p>
        </div>

        <div className="flex gap-3">
          <button 
            onClick={fetchDashboardData}
            className="glass-panel p-2.5 hover:bg-white/5 transition border border-white/10 text-zinc-300 rounded-xl"
            title="Refresh Dashboard Data"
          >
            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
          </button>
          
          <button 
            onClick={triggerSimulation}
            disabled={simulating}
            className="flex items-center gap-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-2.5 px-5 rounded-xl transition shadow-lg shadow-indigo-600/20 disabled:opacity-50"
          >
            {simulating ? (
              <>
                <Cpu size={18} className="animate-spin" />
                <span>Simulating Cohort...</span>
              </>
            ) : (
              <>
                <Play size={18} fill="white" />
                <span>Trigger Simulation Cohort</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* 2. KPI Metrics Cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="glass-panel glass-panel-hover p-6 animate-slide-in">
          <div className="flex justify-between items-start mb-4">
            <span className="text-zinc-400 text-sm font-semibold uppercase tracking-wide">Revenue At Risk</span>
            <span className="p-2 bg-yellow-500/10 text-yellow-400 rounded-lg"><AlertTriangle size={18} /></span>
          </div>
          <h3 className="text-3xl font-extrabold font-display">
            {metrics ? formatCurrency(metrics.total_revenue_at_risk) : "₹0"}
          </h3>
          <p className="text-xs text-zinc-500 mt-2">Total failed cart and payment values</p>
        </div>

        <div className="glass-panel glass-panel-hover p-6 animate-slide-in [animation-delay:100ms]">
          <div className="flex justify-between items-start mb-4">
            <span className="text-emerald-400 text-sm font-semibold uppercase tracking-wide">Recovered Revenue</span>
            <span className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg"><DollarSign size={18} /></span>
          </div>
          <h3 className="text-3xl font-extrabold text-emerald-400 font-display">
            {metrics ? formatCurrency(metrics.total_recovered_revenue) : "₹0"}
          </h3>
          <p className="text-xs text-zinc-500 mt-2">Recovered by autonomous actions</p>
        </div>

        <div className="glass-panel glass-panel-hover p-6 animate-slide-in [animation-delay:200ms]">
          <div className="flex justify-between items-start mb-4">
            <span className="text-blue-400 text-sm font-semibold uppercase tracking-wide">Net Recovery Saving</span>
            <span className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><TrendingUp size={18} /></span>
          </div>
          <h3 className="text-3xl font-extrabold text-blue-400 font-display">
            {metrics ? formatCurrency(metrics.net_recovered_revenue) : "₹0"}
          </h3>
          <p className="text-xs text-zinc-500 mt-2">Subtracting SMS and API retry costs</p>
        </div>

        <div className="glass-panel glass-panel-hover p-6 animate-slide-in [animation-delay:300ms]">
          <div className="flex justify-between items-start mb-4">
            <span className="text-zinc-400 text-sm font-semibold uppercase tracking-wide">Recovery Rate / ROI</span>
            <span className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg"><ArrowUpRight size={18} /></span>
          </div>
          <div className="flex justify-between items-baseline">
            <h3 className="text-3xl font-extrabold text-white font-display">
              {metrics ? `${(metrics.recovery_rate * 100).toFixed(1)}%` : "0%"}
            </h3>
            <span className="text-sm font-bold text-zinc-300 bg-white/5 border border-white/10 px-2 py-0.5 rounded">
              {metrics && metrics.roi > 0 ? `${metrics.roi.toFixed(1)}x ROI` : "N/A"}
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            Cost: {metrics ? formatCurrency(metrics.total_recovery_cost) : "₹0"} ({metrics ? metrics.nudge_count + metrics.retry_count : 0} actions)
          </p>
        </div>
      </section>

      {/* 3. Charts & Analytics Section */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Left Area: Failure Mode Chart */}
        <div className="lg:col-span-2 glass-panel p-6">
          <h3 className="text-lg font-bold mb-4 text-zinc-200">Failure Categorization Analytics</h3>
          <div className="h-[280px]">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="name" stroke="#71717a" fontSize={12} tickLine={false} />
                  <YAxis stroke="#71717a" fontSize={12} tickLine={false} allowDecimals={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', borderColor: 'rgba(255,255,255,0.08)', borderRadius: '8px' }} 
                    labelStyle={{ color: '#a1a1aa', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="failures" fill="url(#barGradient)" radius={[8, 8, 0, 0]} maxBarSize={50} />
                  <defs>
                    <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" />
                      <stop offset="100%" stopColor="#8b5cf6" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                <Activity size={32} className="opacity-30 mb-2" />
                <p className="text-sm">No transaction cohorts analyzed yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Area: Simulation History list */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-bold mb-4 text-zinc-200">Cohort Execution Runs</h3>
          <div className="space-y-4 max-h-[280px] overflow-y-auto pr-1">
            {simulationHistory.length > 0 ? (
              simulationHistory.map((item) => (
                <div key={item.id} className="p-3 bg-white/5 border border-white/5 rounded-xl flex justify-between items-center hover:border-white/10 transition">
                  <div>
                    <span className="text-xs font-mono text-zinc-400 block">{item.id}</span>
                    <span className="text-xs text-zinc-500">
                      {new Date(item.created_at).toLocaleTimeString()} · Risk {formatCurrency(item.total_revenue_at_risk)}
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
      </section>

      {/* 4. Real-Time Transaction Explorer */}
      <section className="glass-panel p-6 animate-slide-in [animation-delay:150ms]">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h3 className="text-xl font-bold text-zinc-200">Transaction & Checkout Explorer</h3>
            <p className="text-xs text-zinc-500 mt-1">Autonomous decision flow and diagnostic timeline tracking</p>
          </div>

          <div className="flex gap-2">
            <button 
              onClick={() => setStatusFilter('')}
              className={`text-xs px-3 py-1.5 rounded-lg border transition ${statusFilter === '' ? 'bg-white/10 border-white/20 text-white' : 'border-white/5 text-zinc-400 hover:bg-white/5'}`}
            >
              All
            </button>
            <button 
              onClick={() => setStatusFilter('RECOVERED')}
              className={`text-xs px-3 py-1.5 rounded-lg border transition ${statusFilter === 'RECOVERED' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400' : 'border-white/5 text-zinc-400 hover:bg-white/5'}`}
            >
              Recovered
            </button>
            <button 
              onClick={() => setStatusFilter('UNRECOVERABLE')}
              className={`text-xs px-3 py-1.5 rounded-lg border transition ${statusFilter === 'UNRECOVERABLE' ? 'bg-rose-500/20 border-rose-500/30 text-rose-400' : 'border-white/5 text-zinc-400 hover:bg-white/5'}`}
            >
              Unrecoverable
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 text-zinc-400 text-xs font-semibold uppercase">
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4 text-right">Cart Value</th>
                <th className="py-3 px-4">Initial Failure</th>
                <th className="py-3 px-4">Recovery Mode</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {transactions.length > 0 ? (
                transactions.map((txn) => {
                  const isExpanded = expandedTxnId === txn.id;
                  const audit = txnAudits[txn.id];

                  return (
                    <>
                      <tr 
                        key={txn.id} 
                        onClick={() => handleRowClick(txn.id)}
                        className={`border-b border-white/5 hover:bg-white/5 transition cursor-pointer ${isExpanded ? 'bg-white/5' : ''}`}
                      >
                        <td className="py-4 px-4 font-mono text-xs text-zinc-300">{txn.id}</td>
                        <td className="py-4 px-4">
                          <span className="font-semibold block text-sm text-zinc-200">{txn.customer_name}</span>
                          <span className="text-[11px] text-zinc-500">{txn.customer_email || 'No email'}</span>
                        </td>
                        <td className="py-4 px-4 text-right font-semibold font-display text-zinc-200">{formatCurrency(txn.amount)}</td>
                        <td className="py-4 px-4">
                          <span className="text-xs text-zinc-300 font-medium">
                            {txn.failure_mode ? txn.failure_mode.replace(/_/g, ' ') : 'N/A'}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-xs text-zinc-400">
                            {txn.action_proposed ? txn.action_proposed.replace(/_/g, ' ') : 'No intervention'}
                          </span>
                        </td>
                        <td className="py-4 px-4">{getStatusBadge(txn.status)}</td>
                        <td className="py-4 px-4 text-zinc-500">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="p-0 bg-zinc-950/40 border-b border-white/5">
                            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                              {/* Left Panel: Event Log timeline */}
                              <div>
                                <h4 className="text-xs uppercase tracking-wider font-bold text-zinc-400 mb-4 flex items-center gap-1.5">
                                  <Cpu size={14} className="text-indigo-400" />
                                  Agent Decisions & Audit Timeline
                                </h4>
                                <div className="space-y-4 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
                                  {audit && audit.audit_events.length > 0 ? (
                                    audit.audit_events.map((evt) => (
                                      <div key={evt.id} className="flex gap-4 relative pl-6">
                                        <span className="absolute left-1.5 top-1.5 w-3 h-3 bg-indigo-500 rounded-full border-2 border-zinc-950 glow-primary"></span>
                                        <div>
                                          <span className="text-xs font-semibold text-zinc-300 block">
                                            {evt.event_type.replace(/_/g, ' ')}
                                          </span>
                                          <p className="text-[11px] text-zinc-400 mt-0.5">{evt.reason}</p>
                                          <span className="text-[10px] text-zinc-600 font-mono mt-1 block">
                                            Actor: {evt.actor} ({evt.source}) · {new Date(evt.timestamp).toLocaleTimeString()}
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
                                          <span className={`text-xs px-2 py-0.5 font-bold rounded ${decision.allowed ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                                            {decision.allowed ? 'APPROVED' : 'BLOCKED'}
                                          </span>
                                        </div>
                                        <p className="text-[11px] text-zinc-400 mb-3">{decision.reason}</p>
                                        
                                        <div className="grid grid-cols-2 gap-2">
                                          {decision.checks_run.map((chk, i) => (
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
                      )}
                    </>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-zinc-500">
                    <Activity size={32} className="mx-auto opacity-30 mb-2" />
                    <span>No transactions tracked yet. Click "Trigger Simulation Cohort" to see the agent in action!</span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default App;
