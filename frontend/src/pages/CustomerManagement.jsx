import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pencil, Save, Search } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import { adminCustomerAPI } from '@/utils/api';

/**
 * Admin-only Customer Management page.
 *
 *   - Lists every customer (with policy_count) using GET /api/admin/customers.
 *   - Server-side search by name / phone / email / address / policy number.
 *   - Inline edit via a modal that calls PUT /api/admin/customers/{id}.
 *
 * Route protection lives in :file:`App.js` (``ProtectedRoute requireAdmin``).
 * The backend additionally enforces admin role on every endpoint, so a
 * non-admin opening the route directly would still be refused at the API
 * layer.
 */

const EMPTY_FORM = { name: '', email: '', phone: '', address: '' };
const SEARCH_DEBOUNCE_MS = 250;

function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function CustomerManagement() {
  const { toast } = useToast();

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const requestSeq = useRef(0);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  // Debounce the search input → applied query so we don't fire a request on every keystroke.
  useEffect(() => {
    const handle = setTimeout(() => {
      setAppliedSearch(searchInput.trim());
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [searchInput]);

  const reload = useCallback(
    async (searchValue) => {
      const seq = ++requestSeq.current;
      setLoading(true);
      try {
        const params = searchValue ? { search: searchValue } : {};
        const res = await adminCustomerAPI.list(params);
        if (seq !== requestSeq.current) return; // newer request in flight
        setRows(Array.isArray(res.data) ? res.data : []);
      } catch (err) {
        if (seq !== requestSeq.current) return;
        toast({
          title: 'Could not load customers',
          description:
            err?.response?.data?.detail || err?.message || 'Unknown error',
          variant: 'destructive',
        });
      } finally {
        if (seq === requestSeq.current) setLoading(false);
      }
    },
    [toast],
  );

  useEffect(() => {
    reload(appliedSearch);
  }, [reload, appliedSearch]);

  const openEdit = (c) => {
    setEditingId(c.id);
    setForm({
      name: c.name || '',
      email: c.email || '',
      phone: c.phone || '',
      address: c.address || '',
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const submit = async () => {
    setFormError(null);
    const name = (form.name || '').trim();
    if (!name) {
      setFormError('Customer name is required.');
      return;
    }

    setSubmitting(true);
    try {
      await adminCustomerAPI.update(editingId, {
        name,
        email: (form.email || '').trim() || null,
        phone: (form.phone || '').trim() || null,
        address: (form.address || '').trim() || null,
      });
      toast({ title: 'Customer updated', description: name });
      setDialogOpen(false);
      setEditingId(null);
      // Refresh the currently-applied filter so the row reflects the new data.
      reload(appliedSearch);
    } catch (err) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Update failed';
      setFormError(String(detail));
    } finally {
      setSubmitting(false);
    }
  };

  const totalCount = rows.length;
  const heading = useMemo(
    () =>
      appliedSearch
        ? `${totalCount} match${totalCount === 1 ? '' : 'es'} for “${appliedSearch}”`
        : `${totalCount} customer${totalCount === 1 ? '' : 's'}`,
    [appliedSearch, totalCount],
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                Customer management
              </h1>
              <p className="text-sm text-gray-500">
                Search, review, and update customer details across the
                organization.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-4">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="relative w-full max-w-md">
            <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
            <Input
              placeholder="Search by name, mobile, email, address, or policy number"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9"
              data-testid="customer-search-input"
            />
          </div>
          <p className="text-sm text-gray-500" data-testid="customer-result-count">
            {loading ? 'Loading…' : heading}
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Mobile</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="min-w-[240px]">Address</TableHead>
                <TableHead className="text-right">Policies</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="text-center text-sm text-gray-500 py-8"
                  >
                    Loading…
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="text-center text-sm text-gray-500 py-8"
                    data-testid="customer-empty-row"
                  >
                    No customers found.
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((c) => (
                  <TableRow key={c.id} data-testid={`customer-row-${c.id}`}>
                    <TableCell className="font-medium">
                      {c.name || '—'}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {c.phone || '—'}
                    </TableCell>
                    <TableCell className="font-mono text-sm break-all">
                      {c.email || '—'}
                    </TableCell>
                    <TableCell className="text-sm text-gray-700">
                      <span className="line-clamp-2 whitespace-pre-line">
                        {c.address || '—'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {c.policy_count ?? 0}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500 whitespace-nowrap">
                      {formatDate(c.created_at)}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500 whitespace-nowrap">
                      {formatDate(c.updated_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEdit(c)}
                        data-testid={`edit-customer-${c.id}`}
                      >
                        <Pencil className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            setEditingId(null);
            setFormError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit customer</DialogTitle>
            <DialogDescription>
              Update the customer record. Changes are saved immediately.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="cust-name">Name *</Label>
              <Input
                id="cust-name"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                placeholder="Customer name"
                autoComplete="off"
                data-testid="edit-customer-name"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cust-phone">Mobile number</Label>
              <Input
                id="cust-phone"
                value={form.phone}
                onChange={(e) =>
                  setForm((f) => ({ ...f, phone: e.target.value }))
                }
                placeholder="+91 9XXXXXXXXX"
                autoComplete="off"
                data-testid="edit-customer-phone"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cust-email">Email</Label>
              <Input
                id="cust-email"
                type="email"
                value={form.email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email: e.target.value }))
                }
                placeholder="customer@example.com"
                autoComplete="off"
                data-testid="edit-customer-email"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cust-address">Address</Label>
              <Textarea
                id="cust-address"
                value={form.address}
                onChange={(e) =>
                  setForm((f) => ({ ...f, address: e.target.value }))
                }
                placeholder="Street, city, state, ZIP"
                rows={3}
                data-testid="edit-customer-address"
              />
            </div>

            {formError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
                {formError}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              onClick={submit}
              disabled={submitting}
              data-testid="save-customer-btn"
            >
              {submitting ? (
                'Saving…'
              ) : (
                <>
                  <Save className="w-4 h-4 mr-1" />
                  Save changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
