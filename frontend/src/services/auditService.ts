import { API_BASE } from './api';
import type { TransactionAudit } from '../types/audit';

export async function fetchTransactionAudit(txnId: string): Promise<TransactionAudit> {
  const res = await fetch(`${API_BASE}/api/v1/transactions/${txnId}/audit`);
  return res.json();
}
