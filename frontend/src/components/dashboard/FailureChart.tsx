import { Activity } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { MetricData } from '../../types/metrics';

interface FailureChartProps {
  metrics: MetricData | null;
}

/**
 * Bar chart showing failure categorization by root cause.
 * Extracted from App.tsx lines 298–328.
 */
export function FailureChart({ metrics }: FailureChartProps) {
  const chartData = metrics
    ? Object.entries(metrics.cause_distribution).map(([key, val]) => ({
        name: key.replace(/_/g, ' '),
        failures: val,
      }))
    : [];

  return (
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
  );
}
