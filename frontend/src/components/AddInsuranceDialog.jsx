import React, { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { customerAPI, policyAPI } from '@/utils/api';
import { ShieldPlus, Search, X } from 'lucide-react';

const MAX_SEARCH_RESULTS = 150;

const emptyPolicy = () => ({
  policy_number: '',
  policy_type: 'auto',
  start_date: new Date().toISOString().split('T')[0],
  end_date: '',
  premium: '',
  status: 'active',
});

const emptyPerson = () => ({
  name: '',
  email: '',
  phone: '',
  address: '',
});

function formatPolicyDate(s) {
  if (!s) return '—';
  const t = String(s);
  return t.includes('T') ? t.split('T')[0] : t.slice(0, 10);
}

/**
 * Add insurance: either create a new customer + policy, or attach a policy to an existing customer.
 * @param {{ id: string, name?: string, email?: string, phone?: string }[]} customers
 * @param {{ id: string, customer_id: string, policy_number?: string, policy_type?: string, start_date?: string, end_date?: string, premium?: number, status?: string }[]} policies
 */
const AddInsuranceDialog = ({ customers = [], policies = [], onSuccess }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  /** @type {'new' | 'existing'} */
  const [mode, setMode] = useState('new');
  const [person, setPerson] = useState(emptyPerson);
  const [policyForm, setPolicyForm] = useState(emptyPolicy);
  const [existingCustomerId, setExistingCustomerId] = useState('');
  /** Search text to filter customers (name, email, phone, id). */
  const [customerQuery, setCustomerQuery] = useState('');
  /** Which existing policy row is expanded to show full details (existing-customer mode). */
  const [viewPolicyId, setViewPolicyId] = useState(null);

  const filteredCustomers = useMemo(() => {
    const q = customerQuery.trim().toLowerCase();
    if (!q) return [];
    return customers.filter((c) => {
      const name = (c.name || '').toLowerCase();
      const email = (c.email || '').toLowerCase();
      const phone = (c.phone || '').replace(/\s/g, '');
      const id = String(c.id);
      const qq = q.replace(/\s/g, '');
      return (
        name.includes(q) ||
        email.includes(q) ||
        phone.includes(qq) ||
        id.includes(q)
      );
    });
  }, [customers, customerQuery]);

  const searchResults = useMemo(() => {
    const list = filteredCustomers;
    const truncated = list.length > MAX_SEARCH_RESULTS;
    return { rows: list.slice(0, MAX_SEARCH_RESULTS), total: list.length, truncated };
  }, [filteredCustomers]);

  const selectedCustomer = useMemo(
    () => customers.find((c) => String(c.id) === String(existingCustomerId)),
    [customers, existingCustomerId]
  );

  const policiesForSelected = useMemo(() => {
    if (!existingCustomerId) return [];
    return policies.filter((p) => String(p.customer_id) === String(existingCustomerId));
  }, [policies, existingCustomerId]);

  /** When customer changes: reset view. If they have exactly one policy, show its details. */
  useEffect(() => {
    if (!existingCustomerId) {
      setViewPolicyId(null);
      return;
    }
    const list = policies.filter((p) => String(p.customer_id) === String(existingCustomerId));
    if (list.length === 1) {
      setViewPolicyId(String(list[0].id));
    } else {
      setViewPolicyId(null);
    }
  }, [existingCustomerId, policies]);

  const viewedPolicy = useMemo(() => {
    if (!viewPolicyId) return null;
    return policiesForSelected.find((p) => String(p.id) === String(viewPolicyId)) || null;
  }, [policiesForSelected, viewPolicyId]);

  const reset = () => {
    setMode('new');
    setPerson(emptyPerson());
    setPolicyForm(emptyPolicy());
    setExistingCustomerId('');
    setCustomerQuery('');
    setViewPolicyId(null);
  };

  const handleOpenChange = (next) => {
    setOpen(next);
    if (!next) reset();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      let customerId = existingCustomerId;
      if (mode === 'new') {
        if (!person.name?.trim()) {
          alert('Customer name is required.');
          return;
        }
        const cr = await customerAPI.create({
          name: person.name.trim(),
          email: person.email?.trim() || undefined,
          phone: person.phone?.trim() || undefined,
          address: person.address?.trim() || undefined,
        });
        customerId = String(cr.data.id);
      } else {
        if (!customerId) {
          alert('Search and select a customer.');
          return;
        }
      }

      const premium = parseFloat(policyForm.premium);
      if (Number.isNaN(premium)) {
        alert('Enter a valid premium amount.');
        return;
      }

      await policyAPI.create({
        customer_id: customerId,
        policy_number: policyForm.policy_number.trim(),
        policy_type: policyForm.policy_type,
        start_date: policyForm.start_date,
        end_date: policyForm.end_date,
        premium,
        status: policyForm.status,
      });

      setOpen(false);
      reset();
      onSuccess();
    } catch (error) {
      console.error('Failed to add insurance:', error);
      alert(
        'Failed to save: ' + (error.response?.data?.detail || error.message || 'Unknown error')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid="add-insurance-btn">
          <ShieldPlus className="w-4 h-4 mr-2" />
          Add insurance
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add insurance</DialogTitle>
          <DialogDescription>
            Create a policy for a new customer, or add a policy to someone already in your list.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex rounded-md border p-1 bg-muted/40 gap-1">
            <button
              type="button"
              className={`flex-1 rounded-sm py-1.5 text-sm font-medium transition-colors ${
                mode === 'new' ? 'bg-background shadow text-foreground' : 'text-muted-foreground'
              }`}
              onClick={() => setMode('new')}
            >
              New customer
            </button>
            <button
              type="button"
              className={`flex-1 rounded-sm py-1.5 text-sm font-medium transition-colors ${
                mode === 'existing'
                  ? 'bg-background shadow text-foreground'
                  : 'text-muted-foreground'
              }`}
              onClick={() => {
                setMode('existing');
                setExistingCustomerId('');
                setCustomerQuery('');
                setViewPolicyId(null);
              }}
            >
              Existing customer
            </button>
          </div>

          {mode === 'new' && (
            <div className="space-y-3 rounded-lg border p-3 bg-gray-50/80">
              <p className="text-sm font-medium text-gray-800">Customer</p>
              <div>
                <Label htmlFor="ai-name">Full name *</Label>
                <Input
                  id="ai-name"
                  value={person.name}
                  onChange={(e) => setPerson({ ...person, name: e.target.value })}
                  required={mode === 'new'}
                  placeholder="Name as on policy"
                  data-testid="add-insurance-name"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="ai-email">Email</Label>
                  <Input
                    id="ai-email"
                    type="email"
                    value={person.email}
                    onChange={(e) => setPerson({ ...person, email: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="ai-phone">Phone</Label>
                  <Input
                    id="ai-phone"
                    type="tel"
                    value={person.phone}
                    onChange={(e) => setPerson({ ...person, phone: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="ai-address">Address</Label>
                <Textarea
                  id="ai-address"
                  value={person.address}
                  onChange={(e) => setPerson({ ...person, address: e.target.value })}
                  rows={2}
                  placeholder="Optional — full address"
                />
              </div>
            </div>
          )}

          {mode === 'existing' && (
            <div className="space-y-2">
              <Label htmlFor="ai-customer-search">Find customer *</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="ai-customer-search"
                  className="pl-9"
                  placeholder={
                    existingCustomerId
                      ? 'Clear selection below to search again…'
                      : 'Type name, phone, email, or ID…'
                  }
                  value={customerQuery}
                  onChange={(e) => {
                    setCustomerQuery(e.target.value);
                    if (existingCustomerId) {
                      setExistingCustomerId('');
                      setViewPolicyId(null);
                    }
                  }}
                  disabled={!!existingCustomerId && !customerQuery}
                  autoComplete="off"
                  data-testid="add-insurance-customer-search"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {existingCustomerId
                  ? 'Customer selected — use Clear to search for someone else.'
                  : 'Results appear below; pick one row. The list closes after you select.'}
              </p>

              {/* Only show search results while typing and no customer locked in yet */}
              {customerQuery.trim() && !existingCustomerId && (
                <div className="rounded-md border bg-popover max-h-48 overflow-y-auto shadow-sm">
                  {searchResults.rows.length === 0 ? (
                    <p className="p-3 text-sm text-muted-foreground">No matching customers.</p>
                  ) : (
                    <ul className="py-1">
                      {searchResults.rows.map((c) => (
                        <li key={c.id}>
                          <button
                            type="button"
                            className="w-full text-left px-3 py-2 text-sm hover:bg-accent"
                            onClick={() => {
                              setExistingCustomerId(String(c.id));
                              setCustomerQuery('');
                            }}
                          >
                            <span className="font-medium">{c.name || '—'}</span>
                            <span className="text-muted-foreground">
                              {' '}
                              · {c.phone || c.email || `ID ${c.id}`}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  {searchResults.truncated && (
                    <p className="px-3 pb-2 text-xs text-amber-700 border-t">
                      Showing first {MAX_SEARCH_RESULTS} of {searchResults.total} matches — refine your
                      search.
                    </p>
                  )}
                </div>
              )}

              {!customerQuery.trim() && !existingCustomerId && customers.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {customers.length} customer{customers.length !== 1 ? 's' : ''} on file — type above to
                  search.
                </p>
              )}

              {selectedCustomer && (
                <div className="flex items-center justify-between gap-2 rounded-md border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <span className="font-medium text-indigo-950">Selected: </span>
                    <span className="text-indigo-900">{selectedCustomer.name}</span>
                    {selectedCustomer.phone && (
                      <span className="text-indigo-800/80"> · {selectedCustomer.phone}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs"
                      onClick={() => {
                        setExistingCustomerId('');
                        setCustomerQuery('');
                        setViewPolicyId(null);
                      }}
                    >
                      Clear
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => {
                        setExistingCustomerId('');
                        setCustomerQuery('');
                        setViewPolicyId(null);
                      }}
                      aria-label="Clear selection"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}

              {customers.length === 0 && (
                <p className="text-xs text-amber-700">Add a customer first or use “New customer”.</p>
              )}
            </div>
          )}

          <div className="space-y-3 rounded-lg border p-3">
            <p className="text-sm font-medium text-gray-800">Policy</p>

            {mode === 'existing' && existingCustomerId && (
              <div className="rounded-md border border-slate-200 bg-slate-50/90 p-3 space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Existing policies for this customer
                </p>
                {policiesForSelected.length === 0 ? (
                  <p className="text-sm text-slate-600">
                    No policies yet — fill in the form below to add the first one.
                  </p>
                ) : (
                  <>
                    <p className="text-xs text-slate-600">
                      {policiesForSelected.length > 1
                        ? 'Click a policy to view full details.'
                        : 'Policy on file:'}
                    </p>
                    <ul className="max-h-36 overflow-y-auto rounded-md border border-slate-200/80 bg-white divide-y divide-slate-100">
                      {policiesForSelected.map((p) => {
                        const isView = String(p.id) === String(viewPolicyId);
                        return (
                          <li key={p.id}>
                            <button
                              type="button"
                              onClick={() => setViewPolicyId(String(p.id))}
                              className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                                isView
                                  ? 'bg-indigo-50 text-indigo-950 ring-1 ring-inset ring-indigo-200'
                                  : 'hover:bg-slate-50'
                              }`}
                            >
                              <span className="font-medium">{p.policy_number || '—'}</span>
                              <span className="text-slate-600"> · {p.policy_type || '—'}</span>
                              <span className="block text-xs text-slate-500 mt-0.5 truncate">
                                {formatPolicyDate(p.start_date)} → {formatPolicyDate(p.end_date)}
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                    {policiesForSelected.length > 1 && !viewPolicyId && (
                      <p className="text-xs text-amber-800/90 bg-amber-50/80 border border-amber-100 rounded px-2 py-1.5">
                        Select a policy in the list above to view full details.
                      </p>
                    )}
                    {viewedPolicy && (
                      <div className="rounded-md border border-indigo-100 bg-white p-3 text-sm space-y-2">
                        <p className="text-xs font-semibold text-indigo-900 uppercase tracking-wide">
                          Policy details
                        </p>
                        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-slate-800">
                          <div>
                            <dt className="text-xs text-slate-500">Policy number</dt>
                            <dd className="font-medium">{viewedPolicy.policy_number || '—'}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-slate-500">Type</dt>
                            <dd>{viewedPolicy.policy_type || '—'}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-slate-500">Company</dt>
                            <dd>
                              {viewedPolicy.insurer_company &&
                              String(viewedPolicy.insurer_company).trim()
                                ? viewedPolicy.insurer_company
                                : '—'}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-slate-500">Start date</dt>
                            <dd>{formatPolicyDate(viewedPolicy.start_date)}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-slate-500">End date</dt>
                            <dd>{formatPolicyDate(viewedPolicy.end_date)}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-slate-500">Premium</dt>
                            <dd>
                              {viewedPolicy.premium != null
                                ? Number(viewedPolicy.premium).toLocaleString()
                                : '—'}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-slate-500">Status</dt>
                            <dd className="capitalize">{viewedPolicy.status || '—'}</dd>
                          </div>
                        </dl>
                      </div>
                    )}
                  </>
                )}
                <p className="text-xs text-slate-500 pt-1 border-t border-slate-200/80">
                  New policy to add (below)
                </p>
              </div>
            )}

            <div>
              <Label htmlFor="ai-policy-no">Policy number *</Label>
              <Input
                id="ai-policy-no"
                value={policyForm.policy_number}
                onChange={(e) => setPolicyForm({ ...policyForm, policy_number: e.target.value })}
                required
                placeholder="e.g. POL-12345"
              />
            </div>
            <div>
              <Label>Insurance type *</Label>
              <Select
                value={policyForm.policy_type}
                onValueChange={(v) => setPolicyForm({ ...policyForm, policy_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Motor / auto</SelectItem>
                  <SelectItem value="health">Health</SelectItem>
                  <SelectItem value="home">Property / home</SelectItem>
                  <SelectItem value="life">Life</SelectItem>
                  <SelectItem value="business">Business</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="ai-start">Start date *</Label>
                <Input
                  id="ai-start"
                  type="date"
                  value={policyForm.start_date}
                  onChange={(e) => setPolicyForm({ ...policyForm, start_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="ai-end">End date *</Label>
                <Input
                  id="ai-end"
                  type="date"
                  value={policyForm.end_date}
                  onChange={(e) => setPolicyForm({ ...policyForm, end_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <Label htmlFor="ai-premium">Total premium *</Label>
              <Input
                id="ai-premium"
                type="number"
                step="0.01"
                value={policyForm.premium}
                onChange={(e) => setPolicyForm({ ...policyForm, premium: e.target.value })}
                required
                placeholder="0.00"
              />
            </div>
            <div>
              <Label>Status *</Label>
              <Select
                value={policyForm.status}
                onValueChange={(v) => setPolicyForm({ ...policyForm, status: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="expired">Expired</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="add-insurance-submit">
              {loading ? 'Saving…' : 'Save to database'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default AddInsuranceDialog;
