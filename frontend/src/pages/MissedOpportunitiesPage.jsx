import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { policyAPI, customerAPI } from '@/utils/api';
import { ArrowLeft } from 'lucide-react';
import { daysLeftUntil, parsePolicyEndDate } from '@/utils/policyDates';
import { isRenewalOpen, RESOLVED_RENEWAL_OPTIONS, RENEWAL_STATUS } from '@/utils/renewalResolution';

const MissedOpportunitiesPage = () => {
  const [loading, setLoading] = useState(true);
  const [policies, setPolicies] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [renewalDraftByPolicyId, setRenewalDraftByPolicyId] = useState({});

  const loadPolicies = async () => {
    try {
      const response = await policyAPI.getAll();
      setPolicies(response.data);
    } catch (error) {
      console.error('Failed to load policies:', error);
    }
  };

  const loadCustomers = async () => {
    try {
      const response = await customerAPI.getAll();
      setCustomers(response.data);
    } catch (error) {
      console.error('Failed to load customers:', error);
    }
  };

  const mergePolicyFromServer = useCallback((updated) => {
    setPolicies((prev) =>
      prev.map((p) => (String(p.id) === String(updated.id) ? { ...p, ...updated } : p))
    );
  }, []);

  const applyRenewalResolution = async (policyId) => {
    const draft = renewalDraftByPolicyId[policyId];
    if (!draft?.status) {
      alert('Choose a resolution (e.g. Renewed Elsewhere).');
      return;
    }
    try {
      const { data } = await policyAPI.patchRenewalResolution(policyId, {
        renewal_status: draft.status,
        renewal_resolution_note: draft.note?.trim() ? draft.note.trim() : null,
      });
      mergePolicyFromServer(data);
      setRenewalDraftByPolicyId((prev) => {
        const next = { ...prev };
        delete next[policyId];
        return next;
      });
    } catch (err) {
      console.error('Renewal resolution failed:', err);
      alert(err.response?.data?.detail || err.message || 'Failed to save renewal resolution');
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([loadPolicies(), loadCustomers()]);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const expiredActivePastEnd = useMemo(() => {
    const list = [];
    for (const p of policies) {
      if (p.status !== 'active') continue;
      const end = parsePolicyEndDate(p.end_date);
      if (!end) continue;
      if (daysLeftUntil(end) >= 0) continue;
      list.push(p);
    }
    return list;
  }, [policies]);

  const expiredRenewalStatusCounts = useMemo(() => {
    const c = {
      Open: 0,
      RenewedWithUs: 0,
      RenewedElsewhere: 0,
      NotInterested: 0,
      PolicyClosed: 0,
      Duplicate: 0,
    };
    for (const p of expiredActivePastEnd) {
      const s = p.renewal_status || RENEWAL_STATUS.OPEN;
      if (s in c) c[s] += 1;
      else c.Open += 1;
    }
    return c;
  }, [expiredActivePastEnd]);

  const expiredOpenRows = useMemo(() => {
    const byId = Object.fromEntries(customers.map((c) => [String(c.id), c]));
    const rows = [];
    for (const p of expiredActivePastEnd) {
      if (!isRenewalOpen(p)) continue;
      const cust = byId[String(p.customer_id)];
      const end = parsePolicyEndDate(p.end_date);
      rows.push({
        policyId: p.id,
        customerName: cust?.name?.trim() || '—',
        policyType: p.policy_type || '—',
        policyNumber: (p.policy_number && String(p.policy_number).trim()) || '—',
        endDate: end,
      });
    }
    rows.sort((a, b) => (a.endDate?.getTime?.() || 0) - (b.endDate?.getTime?.() || 0));
    return rows;
  }, [expiredActivePastEnd, customers]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto" />
          <p className="mt-4 text-gray-600">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-wrap items-center gap-3">
          <Button variant="ghost" size="sm" asChild className="-ml-2">
            <Link to="/dashboard" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Dashboard
            </Link>
          </Button>
          <h1 className="text-lg font-semibold text-gray-900">Missed opportunities — expired renewals</h1>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card className="shadow-sm" data-testid="missed-opportunities-detail">
          <CardHeader>
            <CardTitle>Expired policies — resolution mix</CardTitle>
            <CardDescription>
              Counts are for <strong>active</strong> policies whose end date has passed, by renewal
              resolution status. Open items appear in the table below until you resolve them.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
                {[
                  { key: 'Open', label: 'Expired open', value: expiredRenewalStatusCounts.Open },
                  { key: 'RWU', label: 'Renewed w/ us', value: expiredRenewalStatusCounts.RenewedWithUs },
                  { key: 'RWE', label: 'Renewed elsewhere', value: expiredRenewalStatusCounts.RenewedElsewhere },
                  { key: 'NI', label: 'Not interested', value: expiredRenewalStatusCounts.NotInterested },
                  { key: 'PC', label: 'Policy closed', value: expiredRenewalStatusCounts.PolicyClosed },
                  { key: 'Dup', label: 'Duplicate', value: expiredRenewalStatusCounts.Duplicate },
                ].map((x) => (
                  <div
                    key={x.key}
                    className="rounded-lg border bg-white px-2 py-2 text-center shadow-sm"
                    data-testid={`expired-renewal-mix-${x.key}`}
                  >
                    <div className="text-[10px] text-muted-foreground leading-tight">{x.label}</div>
                    <div className="text-lg font-bold tabular-nums text-slate-900">{x.value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h2 className="text-base font-semibold text-gray-900 mb-2">Resolve expired policies</h2>
              {expiredOpenRows.length === 0 ? (
                <p className="text-sm text-gray-500 py-6 text-center border rounded-lg bg-gray-50/80">
                  No expired policies with renewal status Open.
                </p>
              ) : (
                <div className="rounded-lg border bg-white overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50/80">
                        <TableHead className="min-w-[100px]">Customer</TableHead>
                        <TableHead>Policy no.</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Ended</TableHead>
                        <TableHead className="min-w-[220px]">Resolve</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {expiredOpenRows.map((row) => {
                        const pid = row.policyId;
                        const draft = renewalDraftByPolicyId[pid] || { status: '', note: '' };
                        return (
                          <TableRow key={pid} data-testid={`expired-open-row-${pid}`}>
                            <TableCell className="font-medium">{row.customerName}</TableCell>
                            <TableCell className="text-sm">{row.policyNumber}</TableCell>
                            <TableCell className="text-sm">{row.policyType}</TableCell>
                            <TableCell className="whitespace-nowrap text-sm">
                              {row.endDate
                                ? row.endDate.toLocaleDateString('en-IN', {
                                    day: 'numeric',
                                    month: 'short',
                                    year: 'numeric',
                                  })
                                : '—'}
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-2 max-w-md">
                                <Select
                                  value={draft.status || undefined}
                                  onValueChange={(v) =>
                                    setRenewalDraftByPolicyId((prev) => ({
                                      ...prev,
                                      [pid]: { ...prev[pid], status: v, note: prev[pid]?.note || '' },
                                    }))
                                  }
                                >
                                  <SelectTrigger className="h-9 text-xs">
                                    <SelectValue placeholder="Choose resolution…" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {RESOLVED_RENEWAL_OPTIONS.map((opt) => (
                                      <SelectItem key={opt.value} value={opt.value}>
                                        {opt.label}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <Textarea
                                  placeholder="Optional note (e.g. renewed through another agent, vehicle sold)"
                                  className="min-h-[56px] text-xs"
                                  value={draft.note}
                                  onChange={(e) =>
                                    setRenewalDraftByPolicyId((prev) => ({
                                      ...prev,
                                      [pid]: {
                                        ...prev[pid],
                                        status: prev[pid]?.status || '',
                                        note: e.target.value,
                                      },
                                    }))
                                  }
                                />
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="secondary"
                                  disabled={!draft.status}
                                  onClick={() => void applyRenewalResolution(pid)}
                                  data-testid={`apply-renewal-resolution-${pid}`}
                                >
                                  Save resolution
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MissedOpportunitiesPage;
