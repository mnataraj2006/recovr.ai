import { authFetch } from './api';
import type { TransactionAudit } from '../types/audit';

export async function fetchTransactionAudit(txnId: string): Promise<TransactionAudit> {
  const res = await authFetch(`/api/v1/transactions/${txnId}/audit`);
  if (!res.ok) {
    throw new Error(`Failed to fetch audit: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
