import { useCallback, useEffect, useRef, useState } from 'react';
import { customerAPI, importAPI, policyAPI, syncAPI } from '@/utils/api';

/**
 * Owns the dashboard's primary remote state: policies, customers, the
 * sync status banner, the statement-CSV row count, and the loading flag.
 *
 * Also drives the one-shot "auto-materialize" effect: when an import has
 * loaded ``statement_policy_lines`` rows but no customer/policy rows
 * exist yet, hit the backend converter once so the dashboard immediately
 * shows the imported data instead of an empty state.
 *
 * Returns a tuple of state + setters + helpers so the UI layer stays
 * declarative. Keeping mutators separate from selectors lets unrelated
 * children re-render independently.
 */
export function useDashboardData() {
  const [policies, setPolicies] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [syncStatus, setSyncStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statementRows, setStatementRows] = useState(null);

  const autoMaterializeAttempted = useRef(false);

  const loadPolicies = useCallback(async () => {
    try {
      const response = await policyAPI.getAll();
      setPolicies(response.data);
    } catch (error) {
      console.error('Failed to load policies:', error);
    }
  }, []);

  const loadCustomers = useCallback(async () => {
    try {
      const response = await customerAPI.getAll();
      setCustomers(response.data);
    } catch (error) {
      console.error('Failed to load customers:', error);
    }
  }, []);

  const loadSyncStatus = useCallback(async () => {
    try {
      const response = await syncAPI.getStatus();
      setSyncStatus(response.data);
    } catch (error) {
      console.error('Failed to load sync status:', error);
    }
  }, []);

  const refreshInsuranceData = useCallback(
    () => Promise.all([loadPolicies(), loadCustomers()]),
    [loadPolicies, loadCustomers]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await Promise.all([
          loadPolicies(),
          loadCustomers(),
          loadSyncStatus(),
          importAPI
            .statementSummary()
            .then((r) => {
              if (!cancelled) setStatementRows(r.data.statement_rows);
            })
            .catch(() => {
              if (!cancelled) setStatementRows(null);
            }),
        ]);
      } catch (error) {
        console.error('Failed to load:', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadPolicies, loadCustomers, loadSyncStatus]);

  useEffect(() => {
    if (loading) return;
    if (statementRows === null || statementRows === 0) return;
    if (customers.length > 0 || policies.length > 0) return;
    if (autoMaterializeAttempted.current) return;
    autoMaterializeAttempted.current = true;
    let cancelled = false;
    (async () => {
      try {
        await importAPI.statementLinesToPolicies();
        if (cancelled) return;
        await Promise.all([loadPolicies(), loadCustomers()]);
        const s = await importAPI.statementSummary();
        if (!cancelled) setStatementRows(s.data.statement_rows);
      } catch (e) {
        console.error('Auto-import from statement CSV failed:', e);
        autoMaterializeAttempted.current = false;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loading, statementRows, customers.length, policies.length, loadPolicies, loadCustomers]);

  return {
    policies,
    setPolicies,
    customers,
    syncStatus,
    loading,
    statementRows,
    refreshInsuranceData,
    loadPolicies,
  };
}
