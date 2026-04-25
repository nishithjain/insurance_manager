import { useCallback } from 'react';
import { policyAPI } from '@/utils/api';
import {
  buildPatchContactStatus,
  buildPatchMarkContacted,
  CONTACT_STATUS,
  defaultFollowUpDateYmd,
} from '@/utils/contactStatus';

/**
 * Encapsulates the three "contact" mutations used by the Expiry list and
 * the daily reminder dialog: marking a row as contacted today, switching
 * the contact status, and editing the follow-up date.
 *
 * All three follow the same pattern — apply an optimistic local merge,
 * call ``policyAPI.patchContact``, then either fold the server response
 * back into the policies array or full-reload on failure. Centralising
 * it keeps the dashboard component free of network plumbing.
 */
export function useDashboardContactActions(setPolicies) {
  const mergePolicyFromServer = useCallback(
    (updated) => {
      setPolicies((prev) =>
        prev.map((p) => (String(p.id) === String(updated.id) ? { ...p, ...updated } : p))
      );
    },
    [setPolicies]
  );

  const mergePolicyContactOptimistic = useCallback(
    (policyId, partial) => {
      setPolicies((prev) =>
        prev.map((p) => (String(p.id) === String(policyId) ? { ...p, ...partial } : p))
      );
    },
    [setPolicies]
  );

  const reloadPoliciesFromApi = useCallback(async () => {
    try {
      const r = await policyAPI.getAll();
      setPolicies(r.data);
    } catch (e) {
      console.error(e);
    }
  }, [setPolicies]);

  const markAsContactedForRow = useCallback(
    async (row) => {
      const patch = buildPatchMarkContacted();
      mergePolicyContactOptimistic(row.policyId, patch);
      try {
        const { data } = await policyAPI.patchContact(row.policyId, patch);
        mergePolicyFromServer(data);
      } catch (err) {
        console.error('Mark contacted failed:', err);
        await reloadPoliciesFromApi();
      }
    },
    [mergePolicyContactOptimistic, mergePolicyFromServer, reloadPoliciesFromApi]
  );

  const handleContactStatusChange = useCallback(
    async (row, value) => {
      const ymd =
        value === CONTACT_STATUS.FOLLOW_UP
          ? row.follow_up_date || defaultFollowUpDateYmd()
          : null;
      const patch = buildPatchContactStatus(value, ymd);
      mergePolicyContactOptimistic(row.policyId, patch);
      try {
        const { data } = await policyAPI.patchContact(row.policyId, patch);
        mergePolicyFromServer(data);
      } catch (err) {
        console.error('Contact status update failed:', err);
        await reloadPoliciesFromApi();
      }
    },
    [mergePolicyContactOptimistic, mergePolicyFromServer, reloadPoliciesFromApi]
  );

  const handleFollowUpDateChange = useCallback(
    async (row, ymd) => {
      if (!ymd) return;
      const patch = {
        contact_status: CONTACT_STATUS.FOLLOW_UP,
        follow_up_date: ymd,
        last_contacted_at: null,
      };
      mergePolicyContactOptimistic(row.policyId, patch);
      try {
        const { data } = await policyAPI.patchContact(row.policyId, patch);
        mergePolicyFromServer(data);
      } catch (err) {
        console.error('Follow-up date update failed:', err);
        await reloadPoliciesFromApi();
      }
    },
    [mergePolicyContactOptimistic, mergePolicyFromServer, reloadPoliciesFromApi]
  );

  return {
    markAsContactedForRow,
    handleContactStatusChange,
    handleFollowUpDateChange,
  };
}
