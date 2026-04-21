import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { policyAPI } from '@/utils/api';

/** Map API policy_type label back to form slug (backend resolves slug → insurance_types). */
function policyTypeToSlug(policyType) {
  if (!policyType) return 'auto';
  const t = String(policyType).toLowerCase();
  if (t.includes('health')) return 'health';
  if (t.includes('property') || t.includes('home')) return 'home';
  if (t.includes('motor') || t.includes('car') || t.includes('wheeler')) return 'auto';
  if (t.includes('business')) return 'business';
  if (t.includes('life')) return 'life';
  return 'auto';
}

const EditPolicyDialog = ({ policy, customers, open, onOpenChange, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    customer_id: '',
    policy_number: '',
    policy_type: 'auto',
    start_date: '',
    end_date: '',
    premium: '',
    status: 'active',
  });

  useEffect(() => {
    if (policy && open) {
      const start = policy.start_date?.includes('T')
        ? policy.start_date.split('T')[0]
        : (policy.start_date || '').slice(0, 10);
      const end = policy.end_date?.includes('T')
        ? policy.end_date.split('T')[0]
        : (policy.end_date || '').slice(0, 10);
      setFormData({
        customer_id: String(policy.customer_id),
        policy_number: policy.policy_number || '',
        policy_type: policyTypeToSlug(policy.policy_type),
        start_date: start || '',
        end_date: end || '',
        premium:
          policy.premium !== undefined && policy.premium !== null
            ? String(policy.premium)
            : '',
        status: policy.status || 'active',
      });
    }
  }, [policy, open]);

  if (!policy) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const premium = parseFloat(formData.premium);
    if (Number.isNaN(premium)) {
      alert('Enter a valid premium amount.');
      return;
    }
    setLoading(true);
    try {
      await policyAPI.update(policy.id, {
        customer_id: formData.customer_id,
        policy_number: formData.policy_number.trim(),
        policy_type: formData.policy_type,
        start_date: formData.start_date,
        end_date: formData.end_date,
        premium,
        status: formData.status,
      });
      onOpenChange(false);
      onSuccess();
    } catch (error) {
      console.error('Failed to update policy:', error);
      alert(
        'Failed to update: ' + (error.response?.data?.detail || error.message || 'Unknown error')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit policy</DialogTitle>
          <DialogDescription>
            Update policy details. Changes are saved to the database.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Customer *</Label>
            <Select
              value={formData.customer_id}
              onValueChange={(v) => setFormData({ ...formData, customer_id: v })}
              required
            >
              <SelectTrigger>
                <SelectValue placeholder="Select customer" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="ep-policy-no">Policy number *</Label>
            <Input
              id="ep-policy-no"
              value={formData.policy_number}
              onChange={(e) => setFormData({ ...formData, policy_number: e.target.value })}
              required
            />
          </div>
          <div>
            <Label>Insurance type *</Label>
            <Select
              value={formData.policy_type}
              onValueChange={(v) => setFormData({ ...formData, policy_type: v })}
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
              <Label htmlFor="ep-start">Start date *</Label>
              <Input
                id="ep-start"
                type="date"
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="ep-end">End date *</Label>
              <Input
                id="ep-end"
                type="date"
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="ep-premium">Total premium *</Label>
            <Input
              id="ep-premium"
              type="number"
              step="0.01"
              value={formData.premium}
              onChange={(e) => setFormData({ ...formData, premium: e.target.value })}
              required
            />
          </div>
          <div>
            <Label>Status *</Label>
            <Select
              value={formData.status}
              onValueChange={(v) => setFormData({ ...formData, status: v })}
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
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EditPolicyDialog;
