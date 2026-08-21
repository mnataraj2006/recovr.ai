import { Activity, ChevronDown, ChevronUp } from 'lucide-react';
import { getStatusBadge } from '../../utils/statusHelpers';
import { formatCurrency } from '../../utils/formatCurrency';
import { TransactionDetail } from './TransactionDetail';
import type { Transaction } from '../../types/transaction';
import type { TransactionAudit } from '../../types/audit';

interface TransactionTableProps {
  transactions: Transaction[];
  expandedTxnId: string | null;
  txnAudits: Record<string, TransactionAudit>;
  statusFilter: string;
  onRowClick: (txnId: string) => void;
  onFilterChange: (filter: string) => void;
}

/**
 * Transaction explorer table with expand-to-detail rows and status filter buttons.
 * Extracted from App.tsx lines 363–532.
 */
export function TransactionTable({
  transactions,
  expandedTxnId,
  txnAudits,
  statusFilter,
  onRowClick,
  onFilterChange,
}: TransactionTableProps) {
  return (
    <section className="glass-panel p-6 animate-slide-in [animation-delay:150ms]">
      {/* Header + filter buttons */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h3 className="text-xl font-bold text-zinc-200">Transaction &amp; Checkout Explorer</h3>
          <p className="text-xs text-zinc-500 mt-1">Autonomous decision flow and diagnostic timeline tracking</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onFilterChange('')}
            className={`text-xs px-3 py-1.5 rounded-lg border transition ${
              statusFilter === '' ? 'bg-white/10 border-white/20 text-white' : 'border-white/5 text-zinc-400 hover:bg-white/5'
            }`}
          >
            All
          </button>
          <button
            onClick={() => onFilterChange('RECOVERED')}
            className={`text-xs px-3 py-1.5 rounded-lg border transition ${
              statusFilter === 'RECOVERED'
                ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                : 'border-white/5 text-zinc-400 hover:bg-white/5'
            }`}
          >
            Recovered
          </button>
          <button
            onClick={() => onFilterChange('UNRECOVERABLE')}
            className={`text-xs px-3 py-1.5 rounded-lg border transition ${
              statusFilter === 'UNRECOVERABLE'
                ? 'bg-rose-500/20 border-rose-500/30 text-rose-400'
                : 'border-white/5 text-zinc-400 hover:bg-white/5'
            }`}
          >
            Unrecoverable
          </button>
        </div>
      </div>

      {/* Table */}
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
              <th className="py-3 px-4" />
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
                      onClick={() => onRowClick(txn.id)}
                      className={`border-b border-white/5 hover:bg-white/5 transition cursor-pointer ${isExpanded ? 'bg-white/5' : ''}`}
                    >
                      <td className="py-4 px-4 font-mono text-xs text-zinc-300">{txn.id}</td>
                      <td className="py-4 px-4">
                        <span className="font-semibold block text-sm text-zinc-200">{txn.customer_name}</span>
                        <span className="text-[11px] text-zinc-500">{txn.customer_email || 'No email'}</span>
                      </td>
                      <td className="py-4 px-4 text-right font-semibold font-display text-zinc-200">
                        {formatCurrency(txn.amount)}
                      </td>
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

                    {isExpanded && <TransactionDetail audit={audit} />}
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
  );
}
