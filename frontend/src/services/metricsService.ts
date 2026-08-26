import { authFetch } from './api';
import type { MetricData, SimulationHistoryItem } from '../types/metrics';

export async function fetchMetrics(): Promise<MetricData> {
  const res = await authFetch('/api/v1/metrics');
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
}

export async function fetchSimulationHistory(): Promise<SimulationHistoryItem[]> {
  const res = await authFetch('/api/v1/simulation/history');
  if (!res.ok) return [];
  return res.json();
}

export async function runSimulation(): Promise<boolean> {
  const res = await authFetch('/api/v1/simulation/run', { method: 'POST' });
  return res.ok;
}

export async function clearSimulationData(): Promise<boolean> {
  const res = await authFetch('/api/v1/simulation/clear', { method: 'DELETE' });
  return res.ok;
}
