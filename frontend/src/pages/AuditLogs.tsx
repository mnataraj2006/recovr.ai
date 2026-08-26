import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchTransactions } from '../services/transactionService';
import type { Transaction } from '../types/transaction';
import { formatCurrency } from '../utils/formatCurrency';
import { formatDate } from '../utils/formatDate';

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { color: string; glow: string }> = {
    RECOVERED: { color: '#34d399', glow: 'rgba(52,211,153,0.6)' },
    UNRECOVERABLE: { color: '#ff6b6b', glow: 'rgba(255,107,107,0.6)' },
    CHECKOUT_ABANDONED: { color: '#fbbf24', glow: 'rgba(251,191,36,0.6)' },
    PENDING: { color: '#fbbf24', glow: 'rgba(251,191,36,0.6)' },
    EXECUTING: { color: '#7dd3fc', glow: 'rgba(125,211,252,0.6)' },
  };
  const s = cfg[status] ?? { color: '#a0b4c4', glow: 'rgba(160,180,196,0.4)' };
  return (
    <div className="flex items-center gap-2">
      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color, boxShadow: `0 0 8px ${s.glow}` }} />
      <span style={{ color: s.color }} className="text-xs font-semibold">{status}</span>
    </div>
  );
}

export function AuditLogs() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState('All Statuses');
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const filter = statusFilter !== 'All Statuses' ? statusFilter : undefined;
      const data = await fetchTransactions(filter);
      setTransactions(data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filtered = transactions.filter((t) => {
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchId = t.id.toLowerCase().includes(q);
      const matchName = (t.customer_name || '').toLowerCase().includes(q);
      const matchEmail = (t.customer_email || '').toLowerCase().includes(q);
      if (!matchId && !matchName && !matchEmail) return false;
    }
    return true;
  });

  const totalResults = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalResults / pageSize));
  const pageTransactions = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="p-6 lg:p-8 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#e0e8f0] tracking-tight">Audit Logs</h1>
          <p className="text-[#a0b4c4] mt-1 text-sm">Review detailed system transactions and recovery events from live data.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="px-4 py-2 rounded-lg text-sm flex items-center gap-2 text-[#7dd3fc] border border-[rgba(125,211,252,0.25)] glow-hover transition-all"
            style={{ background: 'rgba(125,211,252,0.08)' }}
          >
            <span className={`material-symbols-outlined ${loading ? 'animate-spin' : ''}`} style={{ fontSize: 16 }}>refresh</span>
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel rounded-xl p-4 flex flex-wrap gap-4 items-end">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">Search Transaction / Customer</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#a0b4c4]" style={{ fontSize: 16 }}>search</span>
            <input
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              placeholder="Search by ID, name, email..."
              className="w-full rounded pl-9 pr-4 py-2 text-sm text-[#e0e8f0] placeholder:text-[#a0b4c4]/50 outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.35)] transition-all"
              style={{ background: 'rgba(15,21,36,0.6)' }}
            />
          </div>
        </div>

        {/* Status */}
        <div className="flex-1 min-w-[150px]">
          <label className="block text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="w-full appearance-none rounded px-4 py-2 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.35)] transition-all"
            style={{ background: 'rgba(15,21,36,0.6)' }}
          >
            <option>All Statuses</option>
            <option value="RECOVERED">Recovered</option>
            <option value="UNRECOVERABLE">Unrecoverable</option>
            <option value="CHECKOUT_ABANDONED">Abandoned</option>
            <option value="EXECUTING">Executing</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="glass-panel-elevated rounded-xl overflow-hidden border border-[rgba(125,211,252,0.12)] shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="border-b border-[rgba(125,211,252,0.08)]" style={{ background: 'rgba(15,21,36,0.4)' }}>
                {['Transaction ID', 'Customer', 'Timestamp', 'Status', 'Amount', 'Failure Mode', 'Proposed Action', 'Action'].map((h) => (
                  <th key={h} className="py-4 px-5 text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(125,211,252,0.05)]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-[#a0b4c4]">
                    <span className="material-symbols-outlined animate-spin text-2xl mb-2">sync</span>
                    <p className="text-sm">Loading audit logs...</p>
                  </td>
                </tr>
              ) : pageTransactions.length > 0 ? (
                pageTransactions.map((row) => (
                  <tr
                    key={row.id}
                    className="table-row-hover transition-colors cursor-pointer hover:bg-[rgba(125,211,252,0.05)]"
                    onClick={() => navigate(`/audit-logs/${row.id}`)}
                  >
                    <td className="py-4 px-5 font-mono text-[#7dd3fc] text-xs font-medium">{row.id}</td>
                    <td className="py-4 px-5">
                      <span className="text-[#e0e8f0] font-medium block">{row.customer_name || 'N/A'}</span>
                      <span className="text-[11px] text-[#a0b4c4]">{row.customer_email || ''}</span>
                    </td>
                    <td className="py-4 px-5 text-[#a0b4c4] whitespace-nowrap text-xs">
                      {row.created_at ? formatDate(row.created_at) : '-'}
                    </td>
                    <td className="py-4 px-5"><StatusBadge status={row.status} /></td>
                    <td className="py-4 px-5 font-mono text-[#e0e8f0] font-semibold">{formatCurrency(row.amount)}</td>
                    <td className="py-4 px-5 text-[#a0b4c4] text-xs">
                      {row.failure_mode ? row.failure_mode.replace(/_/g, ' ') : '-'}
                    </td>
                    <td className="py-4 px-5 text-xs">
                      <span className="px-2.5 py-1 rounded border text-[#a0b4c4] border-[rgba(125,211,252,0.1)] bg-[rgba(15,21,36,0.6)]">
                        {row.action_proposed ? row.action_proposed.replace(/_/g, ' ') : 'None'}
                      </span>
                    </td>
                    <td className="py-4 px-5 text-xs">
                      <span className="text-[#7dd3fc] font-medium hover:underline flex items-center gap-1">
                        View Replay
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>arrow_forward</span>
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-[#a0b4c4]">
                    <span className="material-symbols-outlined text-3xl mb-2 text-[#a0b4c4]/40">find_in_page</span>
                    <p className="text-sm font-medium">No audit logs found</p>
                    <p className="text-xs text-[#a0b4c4]/70 mt-1">Run a simulation cohort from the dashboard to generate real events.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalResults > 0 && (
          <div className="px-5 py-4 border-t border-[rgba(125,211,252,0.08)] flex items-center justify-between"
            style={{ background: 'rgba(15,21,36,0.5)' }}>
            <p className="text-sm text-[#a0b4c4]">
              Showing <span className="font-medium text-[#e0e8f0]">{Math.min((page - 1) * pageSize + 1, totalResults)}</span> to{' '}
              <span className="font-medium text-[#e0e8f0]">{Math.min(page * pageSize, totalResults)}</span> of{' '}
              <span className="font-medium text-[#e0e8f0]">{totalResults}</span> results
            </p>
            <div className="flex gap-1.5">
              <button
                className="glass-panel w-8 h-8 rounded flex items-center justify-center text-[#a0b4c4] hover:text-[#7dd3fc] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>chevron_left</span>
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).slice(0, 5).map((n) => (
                <button
                  key={n}
                  onClick={() => setPage(n)}
                  className={`w-8 h-8 rounded flex items-center justify-center text-sm font-medium transition-colors ${
                    page === n
                      ? 'text-[#7dd3fc] border border-[rgba(125,211,252,0.35)]'
                      : 'glass-panel text-[#a0b4c4] hover:text-[#7dd3fc]'
                  }`}
                  style={page === n ? { background: 'rgba(125,211,252,0.15)' } : {}}
                >
                  {n}
                </button>
              ))}
              <button
                className="glass-panel w-8 h-8 rounded flex items-center justify-center text-[#a0b4c4] hover:text-[#7dd3fc] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>chevron_right</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

