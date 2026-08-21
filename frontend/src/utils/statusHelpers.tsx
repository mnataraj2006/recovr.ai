import React from 'react';
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';

const BASE = 'px-2.5 py-1 text-xs font-semibold rounded-full flex items-center gap-1.5 ';

/**
 * Returns a styled badge element for a given transaction status string.
 * Identical to the original getStatusBadge function in App.tsx.
 */
export function getStatusBadge(status: string): React.JSX.Element {
  switch (status) {
    case 'RECOVERED':
    case 'SUCCESS':
      return (
        <span className={BASE + 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 glow-success'}>
          <CheckCircle size={12} /> RECOVERED
        </span>
      );
    case 'UNRECOVERABLE':
      return (
        <span className={BASE + 'bg-rose-500/10 text-rose-400 border border-rose-500/20 glow-error'}>
          <XCircle size={12} /> UNRECOVERABLE
        </span>
      );
    case 'CHECKOUT_ABANDONED':
    case 'PAYMENT_FAILED':
      return (
        <span className={BASE + 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 glow-warn'}>
          <AlertTriangle size={12} /> FAILURE DETECTED
        </span>
      );
    default:
      return (
        <span className={BASE + 'bg-blue-500/10 text-blue-400 border border-blue-500/20 glow-primary'}>
          <Clock size={12} /> {status}
        </span>
      );
  }
}
