import { useState, useCallback } from 'react';
import { fetchTransactionAudit } from '../services/auditService';
import type { TransactionAudit } from '../types/audit';

interface UseTransactionAuditReturn {
  expandedTxnId: string | null;
  txnAudits: Record<string, TransactionAudit>;
  handleRowClick: (txnId: string) => Promise<void>;
}

/**
 * Manages the expand/collapse state for transaction rows and lazily fetches
 * audit data per transaction (with a cache to avoid duplicate requests).
 */
export function useTransactions(): UseTransactionAuditReturn {
  const [expandedTxnId, setExpandedTxnId] = useState<string | null>(null);
  const [txnAudits, setTxnAudits] = useState<Record<string, TransactionAudit>>({});

  const handleRowClick = useCallback(async (txnId: string) => {
    if (expandedTxnId === txnId) {
      setExpandedTxnId(null);
      return;
    }

    setExpandedTxnId(txnId);

    // Only fetch if not already cached
    if (!txnAudits[txnId]) {
      try {
        const auditData = await fetchTransactionAudit(txnId);
        setTxnAudits((prev) => ({ ...prev, [txnId]: auditData }));
      } catch (err) {
        console.error('Failed to load transaction audit:', err);
      }
    }
  }, [expandedTxnId, txnAudits]);

  return { expandedTxnId, txnAudits, handleRowClick };
}
