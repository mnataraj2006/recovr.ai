import { authFetch } from './api';
import type { Transaction } from '../types/transaction';

export async function fetchTransactions(statusFilter?: string): Promise<Transaction[]> {
  const query = statusFilter ? `?status=${statusFilter}` : '';
  const res = await authFetch(`/api/v1/transactions${query}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.transactions ?? [];
}

export async function fetchTransactionAudit(txnId: string): Promise<any> {

  const res = await authFetch(`/api/v1/transactions/${txnId}/audit`);
  if (!res.ok) return null;
  return res.json();
}
