import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Plus, Search, UserCheck, UserX, Pencil } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/auth/AuthContext';
import { usersAPI } from '@/utils/api';

/**
 * Admin-only user management page.
 *
 * Actions:
 *   - List + search users.
 *   - Create new user (email / name / role / active).
 *   - Edit existing user.
 *   - Toggle active status inline.
 * Every destructive or privilege-changing action surfaces server errors via
 * toasts so admins can see *why* something was refused (duplicate email, last
 * active admin protection, etc.).
 */

const EMPTY_FORM = { email: '', full_name: '', role: 'user', is_active: true };

function roleBadge(role) {
  const map = {
    admin: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    user: 'bg-gray-100 text-gray-800 border-gray-200',
  };
  return map[role] || map.user;
}

export default function UserManagement() {
  const { user: me } = useAuth();
  const { toast } = useToast();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState('create'); // 'create' | 'edit'
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const res = await usersAPI.list();
      setUsers(res.data || []);
    } catch (err) {
      toast({
        title: 'Could not load users',
        description: err?.response?.data?.detail || err?.message || 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    reload();
  }, [reload]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        (u.email || '').toLowerCase().includes(q) ||
        (u.full_name || '').toLowerCase().includes(q),
    );
  }, [users, search]);

  const openCreate = () => {
    setDialogMode('create');
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setDialogOpen(true);
  };

  const openEdit = (u) => {
    setDialogMode('edit');
    setEditingId(u.id);
    setForm({
      email: u.email,
      full_name: u.full_name,
      role: u.role,
      is_active: u.is_active,
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const submit = async () => {
    setFormError(null);

    const fullName = (form.full_name || '').trim();
    const email = (form.email || '').trim();
    if (!fullName) {
      setFormError('Full name is required.');
      return;
    }
    if (dialogMode === 'create' && !email) {
      setFormError('Email is required.');
      return;
    }

    setSubmitting(true);
    try {
      if (dialogMode === 'create') {
        await usersAPI.create({
          email,
          full_name: fullName,
          role: form.role,
          is_active: form.is_active,
        });
        toast({ title: 'User added', description: email });
      } else {
        await usersAPI.update(editingId, {
          full_name: fullName,
          role: form.role,
          is_active: form.is_active,
        });
        toast({ title: 'User updated', description: email });
      }
      setDialogOpen(false);
      reload();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Request failed';
      setFormError(String(detail));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (u) => {
    try {
      await usersAPI.setStatus(u.id, !u.is_active);
      toast({
        title: u.is_active ? 'User disabled' : 'User enabled',
        description: u.email,
      });
      reload();
    } catch (err) {
      toast({
        title: 'Could not change status',
        description: err?.response?.data?.detail || err?.message || 'Unknown error',
        variant: 'destructive',
      });
    }
  };

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
              <h1 className="text-lg font-semibold text-gray-900">User management</h1>
              <p className="text-sm text-gray-500">
                Only users on this list can sign in with Google.
              </p>
            </div>
          </div>
          <Button onClick={openCreate}>
            <Plus className="w-4 h-4 mr-2" />
            Add user
          </Button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-4">
        <div className="relative w-full max-w-sm">
          <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
          <Input
            placeholder="Search by name or email"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="rounded-lg border border-gray-200 bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Gmail ID</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last login</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-sm text-gray-500 py-8">
                    Loading…
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-sm text-gray-500 py-8">
                    No users match.
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((u) => {
                  const isSelf = me?.id === u.id;
                  return (
                    <TableRow key={u.id}>
                      <TableCell className="font-medium">
                        {u.full_name}
                        {isSelf && (
                          <span className="ml-2 text-xs text-gray-400">(you)</span>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">{u.email}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={roleBadge(u.role)}>
                          {u.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={u.is_active}
                            onCheckedChange={() => toggleActive(u)}
                            disabled={isSelf}
                          />
                          <span
                            className={
                              u.is_active
                                ? 'text-xs text-emerald-700'
                                : 'text-xs text-gray-500'
                            }
                          >
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>
                          <Pencil className="w-4 h-4 mr-1" />
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialogMode === 'create' ? 'Add user' : 'Edit user'}</DialogTitle>
            <DialogDescription>
              {dialogMode === 'create'
                ? 'Pre-approve a Gmail ID to allow Google Sign-In.'
                : 'Update the user’s name, role, or status.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Gmail ID</Label>
              <Input
                id="email"
                type="email"
                placeholder="person@gmail.com"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                disabled={dialogMode === 'edit'}
                autoComplete="off"
              />
              {dialogMode === 'edit' && (
                <p className="text-xs text-gray-500">
                  Email cannot be changed. Delete and re-create to move access to a new address.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input
                id="full_name"
                placeholder="Jane Doe"
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label>Role</Label>
              <Select
                value={form.role}
                onValueChange={(v) => setForm((f) => ({ ...f, role: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div>
                <Label className="text-sm">Active</Label>
                <p className="text-xs text-gray-500">Disabled users cannot sign in.</p>
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
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={submitting}>
              {submitting
                ? 'Saving…'
                : dialogMode === 'create'
                  ? (<><UserCheck className="w-4 h-4 mr-1" />Add user</>)
                  : (<><UserX className="w-4 h-4 mr-1" />Save changes</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
