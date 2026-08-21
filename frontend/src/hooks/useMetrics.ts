import { useState, useEffect, useCallback } from 'react';
import { fetchMetrics, fetchSimulationHistory, runSimulation } from '../services/metricsService';
import { fetchTransactions } from '../services/transactionService';
import type { MetricData, SimulationHistoryItem } from '../types/metrics';
import type { Transaction } from '../types/transaction';

interface DashboardData {
  metrics: MetricData | null;
  transactions: Transaction[];
  simulationHistory: SimulationHistoryItem[];
  loading: boolean;
  simulating: boolean;
  statusFilter: string;
  setStatusFilter: (filter: string) => void;
  refresh: () => Promise<void>;
  triggerSimulation: () => Promise<void>;
}

/**
 * Central hook that drives the dashboard: fetches metrics, transactions, and
 * simulation history together. Exposes a simulation trigger and a status filter.
 */
export function useMetrics(): DashboardData {
  const [metrics, setMetrics] = useState<MetricData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [simulationHistory, setSimulationHistory] = useState<SimulationHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [metricsData, txnData, simData] = await Promise.all([
        fetchMetrics(),
        fetchTransactions(statusFilter),
        fetchSimulationHistory(),
      ]);
      setMetrics(metricsData);
      setTransactions(txnData);
      setSimulationHistory(simData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const triggerSimulation = useCallback(async () => {
    setSimulating(true);
    try {
      const ok = await runSimulation();
      if (ok) await refresh();
    } catch (err) {
      console.error('Failed to run batch simulation:', err);
    } finally {
      setSimulating(false);
    }
  }, [refresh]);

  return {
    metrics,
    transactions,
    simulationHistory,
    loading,
    simulating,
    statusFilter,
    setStatusFilter,
    refresh,
    triggerSimulation,
  };
}
