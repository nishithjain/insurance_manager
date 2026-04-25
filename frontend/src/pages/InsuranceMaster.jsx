import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pencil, Plus, Trash2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { adminInsuranceTypesAPI, adminPolicyTypesAPI } from '@/utils/api';

/**
 * Admin-only "Insurance Master" page.
 *
 * Two tabs:
 *   - Insurance Types  → manages ``insurance_categories``
 *   - Policy Types     → manages ``policy_types`` (filtered by Insurance Type)
 *
 * Both tabs share a uniform CRUD shape: list/grid + create/edit dialog +
 * activate-toggle + delete. Delete is "smart" on the backend: rows referenced
 * by a policy are soft-deactivated rather than removed, and the response tells
 * us which path was taken so the toast message is accurate.
 */

const EMPTY_IT_FORM = { name: '', description: '', is_active: true };
const EMPTY_PT_FORM = {
  insurance_type_id: '',
  name: '',
  description: '',
  is_active: true,
};

function describeError(err) {
  return err?.response?.data?.detail || err?.message || 'Request failed';
}

export default function InsuranceMaster() {
  const [tab, setTab] = useState('insurance');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-4">
          <Link to="/dashboard">
            <Button variant="outline" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Dashboard
            </Button>
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Insurance Master</h1>
            <p className="text-sm text-gray-500">
              Manage Insurance Types (Motor, Health, …) and the Policy Types under
              each (Private Car, Family Floater, …).
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList>
            <TabsTrigger value="insurance">Insurance Types</TabsTrigger>
            <TabsTrigger value="policy">Policy Types</TabsTrigger>
          </TabsList>
          <TabsContent value="insurance">
            <InsuranceTypesTab />
          </TabsContent>
          <TabsContent value="policy">
            <PolicyTypesTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Insurance Types tab                                                         //
// --------------------------------------------------------------------------- //

function InsuranceTypesTab() {
  const { toast } = useToast();

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState('create');
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_IT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminInsuranceTypesAPI.list();
      setRows(res.data || []);
    } catch (err) {
      toast({
        title: 'Could not load Insurance Types',
        description: describeError(err),
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    reload();
  }, [reload]);

  const openCreate = () => {
    setDialogMode('create');
    setEditingId(null);
    setForm(EMPTY_IT_FORM);
    setFormError(null);
    setDialogOpen(true);
  };

  const openEdit = (row) => {
    setDialogMode('edit');
    setEditingId(row.id);
    setForm({
      name: row.name || '',
      description: row.description || '',
      is_active: !!row.is_active,
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const submit = async () => {
    setFormError(null);
    const name = form.name.trim();
    if (!name) {
      setFormError('Insurance Type name is required.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        name,
        description: form.description.trim() || null,
        is_active: form.is_active,
      };
      if (dialogMode === 'create') {
        await adminInsuranceTypesAPI.create(payload);
        toast({ title: 'Insurance Type added', description: name });
      } else {
        await adminInsuranceTypesAPI.update(editingId, payload);
        toast({ title: 'Insurance Type updated', description: name });
      }
      setDialogOpen(false);
      reload();
    } catch (err) {
      setFormError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (row) => {
    try {
      await adminInsuranceTypesAPI.update(row.id, { is_active: !row.is_active });
      toast({
        title: row.is_active ? 'Deactivated' : 'Activated',
        description: row.name,
      });
      reload();
    } catch (err) {
      toast({
        title: 'Could not change status',
        description: describeError(err),
        variant: 'destructive',
      });
    }
  };

  const onDelete = async (row) => {
    const verb = row.in_use ? 'deactivate' : 'delete';
    if (!window.confirm(`Are you sure you want to ${verb} "${row.name}"?`)) return;
    try {
      const res = await adminInsuranceTypesAPI.delete(row.id);
      const data = res.data || {};
      toast({
        title:
          data.outcome === 'deactivated'
            ? 'Deactivated (in use)'
            : 'Insurance Type deleted',
        description: data.message || row.name,
      });
      reload();
    } catch (err) {
      toast({
        title: 'Could not delete',
        description: describeError(err),
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4 mr-2" />
          Add Insurance Type
        </Button>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Policy Types</TableHead>
              <TableHead>Active</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-gray-500 py-8">
                  Loading…
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-gray-500 py-8">
                  No Insurance Types yet.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-medium">
                    {row.name}
                    {row.in_use && (
                      <Badge variant="outline" className="ml-2 text-[10px]">
                        in use
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600 max-w-md">
                    {row.description || <span className="text-gray-400">—</span>}
                  </TableCell>
                  <TableCell className="text-sm">{row.policy_type_count}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={row.is_active}
                        onCheckedChange={() => toggleActive(row)}
                      />
                      <span
                        className={
                          row.is_active
                            ? 'text-xs text-emerald-700'
                            : 'text-xs text-gray-500'
                        }
                      >
                        {row.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(row)}>
                      <Pencil className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(row)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      {row.in_use ? 'Deactivate' : 'Delete'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === 'create' ? 'Add Insurance Type' : 'Edit Insurance Type'}
            </DialogTitle>
            <DialogDescription>
              Insurance Types are the broad categories shown in the policy form
              dropdown (Motor, Health, Life, …).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="it-name">Name</Label>
              <Input
                id="it-name"
                placeholder="e.g. Cyber"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                maxLength={120}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="it-desc">Description (optional)</Label>
              <Textarea
                id="it-desc"
                placeholder="Short description shown to admins"
                value={form.description}
                onChange={(e) =>
                  setForm((f) => ({ ...f, description: e.target.value }))
                }
                maxLength={500}
                rows={3}
              />
            </div>
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div>
                <Label className="text-sm">Active</Label>
                <p className="text-xs text-gray-500">
                  Inactive types are hidden from the policy form dropdowns.
                </p>
              </div>
              <Switch
                checked={form.is_active}
                onCheckedChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
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
            <Button onClick={submit} disabled={submitting}>
              {submitting ? 'Saving…' : dialogMode === 'create' ? 'Add' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Policy Types tab                                                            //
// --------------------------------------------------------------------------- //

function PolicyTypesTab() {
  const { toast } = useToast();

  const [insuranceTypes, setInsuranceTypes] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterParentId, setFilterParentId] = useState('all');

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState('create');
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_PT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const loadParents = useCallback(async () => {
    try {
      const res = await adminInsuranceTypesAPI.list();
      setInsuranceTypes(res.data || []);
    } catch (err) {
      toast({
        title: 'Could not load Insurance Types',
        description: describeError(err),
        variant: 'destructive',
      });
    }
  }, [toast]);

  const loadRows = useCallback(async () => {
    setLoading(true);
    try {
      const params =
        filterParentId !== 'all'
          ? { insurance_type_id: filterParentId }
          : undefined;
      const res = await adminPolicyTypesAPI.list(params);
      setRows(res.data || []);
    } catch (err) {
      toast({
        title: 'Could not load Policy Types',
        description: describeError(err),
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [filterParentId, toast]);

  useEffect(() => {
    loadParents();
  }, [loadParents]);

  useEffect(() => {
    loadRows();
  }, [loadRows]);

  const activeParents = useMemo(
    () => insuranceTypes.filter((t) => t.is_active),
    [insuranceTypes],
  );

  const openCreate = () => {
    setDialogMode('create');
    setEditingId(null);
    setForm({
      ...EMPTY_PT_FORM,
      insurance_type_id:
        filterParentId !== 'all'
          ? String(filterParentId)
          : activeParents[0]?.id != null
            ? String(activeParents[0].id)
            : '',
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const openEdit = (row) => {
    setDialogMode('edit');
    setEditingId(row.id);
    setForm({
      insurance_type_id: String(row.insurance_type_id),
      name: row.name || '',
      description: row.description || '',
      is_active: !!row.is_active,
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const submit = async () => {
    setFormError(null);
    const name = form.name.trim();
    if (!name) {
      setFormError('Policy Type name is required.');
      return;
    }
    if (!form.insurance_type_id) {
      setFormError('Please choose an Insurance Type.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        insurance_type_id: Number(form.insurance_type_id),
        name,
        description: form.description.trim() || null,
        is_active: form.is_active,
      };
      if (dialogMode === 'create') {
        await adminPolicyTypesAPI.create(payload);
        toast({ title: 'Policy Type added', description: name });
      } else {
        await adminPolicyTypesAPI.update(editingId, payload);
        toast({ title: 'Policy Type updated', description: name });
      }
      setDialogOpen(false);
      loadRows();
    } catch (err) {
      setFormError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (row) => {
    try {
      await adminPolicyTypesAPI.update(row.id, { is_active: !row.is_active });
      toast({
        title: row.is_active ? 'Deactivated' : 'Activated',
        description: row.name,
      });
      loadRows();
    } catch (err) {
      toast({
        title: 'Could not change status',
        description: describeError(err),
        variant: 'destructive',
      });
    }
  };

  const onDelete = async (row) => {
    const verb = row.in_use ? 'deactivate' : 'delete';
    if (!window.confirm(`Are you sure you want to ${verb} "${row.name}"?`)) return;
    try {
      const res = await adminPolicyTypesAPI.delete(row.id);
      const data = res.data || {};
      toast({
        title:
          data.outcome === 'deactivated'
            ? 'Deactivated (in use)'
            : 'Policy Type deleted',
        description: data.message || row.name,
      });
      loadRows();
    } catch (err) {
      toast({
        title: 'Could not delete',
        description: describeError(err),
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="space-y-1">
          <Label className="text-sm">Filter by Insurance Type</Label>
          <Select value={String(filterParentId)} onValueChange={setFilterParentId}>
            <SelectTrigger className="w-full sm:w-64">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {insuranceTypes.map((t) => (
                <SelectItem key={t.id} value={String(t.id)}>
                  {t.name}
                  {!t.is_active ? ' (inactive)' : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={openCreate} disabled={activeParents.length === 0}>
          <Plus className="w-4 h-4 mr-2" />
          Add Policy Type
        </Button>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Insurance Type</TableHead>
              <TableHead>Policy Type</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Active</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-gray-500 py-8">
                  Loading…
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-gray-500 py-8">
                  No Policy Types match.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="text-sm">{row.insurance_type_name}</TableCell>
                  <TableCell className="font-medium">
                    {row.name}
                    {row.in_use && (
                      <Badge variant="outline" className="ml-2 text-[10px]">
                        in use
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600 max-w-md">
                    {row.description || <span className="text-gray-400">—</span>}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={row.is_active}
                        onCheckedChange={() => toggleActive(row)}
                      />
                      <span
                        className={
                          row.is_active
                            ? 'text-xs text-emerald-700'
                            : 'text-xs text-gray-500'
                        }
                      >
                        {row.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(row)}>
                      <Pencil className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(row)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      {row.in_use ? 'Deactivate' : 'Delete'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === 'create' ? 'Add Policy Type' : 'Edit Policy Type'}
            </DialogTitle>
            <DialogDescription>
              Policy Types are the specific products under each Insurance Type
              (e.g. "Private Car" under Motor).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Insurance Type</Label>
              <Select
                value={form.insurance_type_id}
                onValueChange={(v) =>
                  setForm((f) => ({ ...f, insurance_type_id: v }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose an Insurance Type" />
                </SelectTrigger>
                <SelectContent>
                  {activeParents.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="pt-name">Policy Type name</Label>
              <Input
                id="pt-name"
                placeholder="e.g. Private Car"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                maxLength={120}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pt-desc">Description (optional)</Label>
              <Textarea
                id="pt-desc"
                placeholder="Short description"
                value={form.description}
                onChange={(e) =>
                  setForm((f) => ({ ...f, description: e.target.value }))
                }
                maxLength={500}
                rows={3}
              />
            </div>
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div>
                <Label className="text-sm">Active</Label>
                <p className="text-xs text-gray-500">
                  Inactive types are hidden from the policy form dropdown.
                </p>
              </div>
              <Switch
                checked={form.is_active}
                onCheckedChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
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
            <Button onClick={submit} disabled={submitting}>
              {submitting ? 'Saving…' : dialogMode === 'create' ? 'Add' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
