import { API_BASE } from './api';
import type { Transaction } from '../types/transaction';

export async function fetchTransactions(statusFilter?: string): Promise<Transaction[]> {
  const query = statusFilter ? `?status=${statusFilter}` : '';
  const res = await fetch(`${API_BASE}/api/v1/transactions${query}`);
  const data = await res.json();
  return data.transactions ?? [];
}
