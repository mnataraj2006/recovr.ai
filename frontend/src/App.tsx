import { useMetrics } from './hooks/useMetrics';
import { useTransactions } from './hooks/useTransactions';
import { Navbar } from './components/common/Navbar';
import { MetricCards } from './components/dashboard/MetricCards';
import { FailureChart } from './components/dashboard/FailureChart';
import { SimulationHistory } from './components/dashboard/SimulationHistory';
import { TransactionTable } from './components/transactions/TransactionTable';

function App() {
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
  } = useMetrics();

  const { expandedTxnId, txnAudits, handleRowClick } = useTransactions();

  return (
    <div className="min-h-screen p-6 md:p-8">
      <Navbar
        loading={loading}
        simulating={simulating}
        onRefresh={refresh}
        onSimulate={triggerSimulation}
      />

      <MetricCards metrics={metrics} />

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <FailureChart metrics={metrics} />
        <SimulationHistory history={simulationHistory} />
      </section>

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

export default App;
