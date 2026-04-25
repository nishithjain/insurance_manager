import React, { useEffect, useMemo, useState } from 'react';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { policyAPI, typesAPI } from '@/utils/api';
import { useToast } from '@/hooks/use-toast';

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

// Best-effort heuristic for legacy rows where ``policy.insurance_type_id`` is
// NULL. We check the ``policy.policy_type`` legacy text against the user's
// new Insurance Type list (Motor / Health / ...). Used only on first paint
// of the edit modal — the user always has the option to manually re-pick.
function guessInsuranceTypeIdFromLegacy(policy, insuranceTypes) {
  if (!policy || !insuranceTypes?.length) return '';
  if (policy.insurance_type_id) return String(policy.insurance_type_id);
  const hint = `${policy.insurance_type_name || ''} ${policy.policy_type || ''}`.toLowerCase();
  let bucket = null;
  if (hint.includes('motor') || hint.includes('car') || hint.includes('wheeler')) {
    bucket = 'motor';
  } else if (hint.includes('health')) {
    bucket = 'health';
  } else if (hint.includes('property') || hint.includes('home') || hint.includes('business')) {
    bucket = 'property';
  } else if (hint.includes('life')) {
    bucket = 'life';
  } else if (hint.includes('travel')) {
    bucket = 'travel';
  }
  if (!bucket) return '';
  const match = insuranceTypes.find((t) => (t.name || '').toLowerCase() === bucket);
  return match ? String(match.id) : '';
}

const LEGACY_SLUG_FOR_INSURANCE_TYPE = {
  motor: 'auto',
  health: 'health',
  property: 'home',
  life: 'life',
  travel: 'auto',
};

const EMPTY_FORM = {
  policy_number: '',
  policy_type: 'auto',
  insurance_type_id: '',
  policy_type_id: '',
  start_date: '',
  end_date: '',
  premium: '',
  status: 'active',
  customer_email: '',
  customer_phone: '',
  customer_address: '',
};

const EditPolicyDialog = ({ policy, customers, open, onOpenChange, onSuccess }) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [insuranceTypes, setInsuranceTypes] = useState([]);
  const [policyTypes, setPolicyTypes] = useState([]);

  /**
   * Linked customer record. Customer name is shown read-only; the editable
   * customer fields (email / phone / address) are seeded from this record so
   * the modal reflects current data on open.
   */
  const linkedCustomer = useMemo(() => {
    if (!policy) return null;
    return (
      customers?.find((c) => String(c.id) === String(policy.customer_id)) || null
    );
  }, [policy, customers]);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await typesAPI.listInsuranceTypes();
        if (!cancelled) setInsuranceTypes(res.data || []);
      } catch (err) {
        console.warn('Failed to load insurance types', err);
        if (!cancelled) setInsuranceTypes([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    const itid = formData.insurance_type_id;
    if (!itid) {
      setPolicyTypes([]);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await typesAPI.listPolicyTypes(itid);
        if (!cancelled) setPolicyTypes(res.data || []);
      } catch (err) {
        console.warn('Failed to load policy types', err);
        if (!cancelled) setPolicyTypes([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [formData.insurance_type_id]);

  useEffect(() => {
    if (policy && open) {
      const start = policy.start_date?.includes('T')
        ? policy.start_date.split('T')[0]
        : (policy.start_date || '').slice(0, 10);
      const end = policy.end_date?.includes('T')
        ? policy.end_date.split('T')[0]
        : (policy.end_date || '').slice(0, 10);
      const seedItId = policy.insurance_type_id
        ? String(policy.insurance_type_id)
        : guessInsuranceTypeIdFromLegacy(policy, insuranceTypes);
      setFormData({
        policy_number: policy.policy_number || '',
        policy_type: policyTypeToSlug(policy.policy_type),
        insurance_type_id: seedItId,
        policy_type_id: policy.policy_type_id ? String(policy.policy_type_id) : '',
        start_date: start || '',
        end_date: end || '',
        premium:
          policy.premium !== undefined && policy.premium !== null
            ? String(policy.premium)
            : '',
        status: policy.status || 'active',
        customer_email: linkedCustomer?.email || '',
        customer_phone: linkedCustomer?.phone || '',
        customer_address: linkedCustomer?.address || '',
      });
    }
  }, [policy, open, linkedCustomer, insuranceTypes]);

  const selectedInsuranceType = useMemo(
    () =>
      insuranceTypes.find(
        (t) => String(t.id) === String(formData.insurance_type_id)
      ) || null,
    [insuranceTypes, formData.insurance_type_id]
  );

  if (!policy) return null;

  const customerNameDisplay =
    linkedCustomer?.name?.trim() || `Customer #${policy.customer_id}`;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const premium = parseFloat(formData.premium);
    if (Number.isNaN(premium)) {
      toast({
        title: 'Invalid premium',
        description: 'Enter a valid premium amount.',
        variant: 'destructive',
      });
      return;
    }
    if (!formData.policy_number.trim()) {
      toast({
        title: 'Missing policy number',
        description: 'Policy number is required.',
        variant: 'destructive',
      });
      return;
    }

    if (!formData.insurance_type_id) {
      toast({
        title: 'Insurance type required',
        description: 'Pick an Insurance Type before saving.',
        variant: 'destructive',
      });
      return;
    }
    if (!formData.policy_type_id) {
      toast({
        title: 'Policy type required',
        description: 'Pick a Policy Type before saving.',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const itName = (selectedInsuranceType?.name || '').toLowerCase();
      const legacySlug =
        LEGACY_SLUG_FOR_INSURANCE_TYPE[itName] || formData.policy_type || 'auto';

      // ``customer.name`` is intentionally NOT sent — name is read-only here.
      await policyAPI.update(policy.id, {
        customer_id: String(policy.customer_id),
        policy_number: formData.policy_number.trim(),
        policy_type: legacySlug,
        insurance_type_id: Number(formData.insurance_type_id),
        policy_type_id: Number(formData.policy_type_id),
        start_date: formData.start_date,
        end_date: formData.end_date,
        premium,
        status: formData.status,
        customer: {
          email: formData.customer_email.trim(),
          phone: formData.customer_phone.trim(),
          address: formData.customer_address.trim(),
        },
      });
      toast({
        title: 'Policy updated',
        description: `${customerNameDisplay} · ${formData.policy_number.trim() || policy.policy_number}`,
      });
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error('Failed to update policy:', error);
      toast({
        title: 'Could not save policy',
        description:
          error?.response?.data?.detail || error?.message || 'Unknown error',
        variant: 'destructive',
      });
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
            Update policy details and the linked customer's contact info.
            Customer name can be changed from Customer Management.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-3 rounded-lg border p-3 bg-gray-50/80">
            <p className="text-sm font-medium text-gray-800">Customer</p>
            <div>
              <Label>Customer name</Label>
              <div
                className="mt-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-900"
                data-testid="ep-customer-name-readonly"
                aria-readonly="true"
              >
                {customerNameDisplay}
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Read-only here. Edit the name from the Customer Management page.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label htmlFor="ep-cust-phone">Mobile number</Label>
                <Input
                  id="ep-cust-phone"
                  type="tel"
                  value={formData.customer_phone}
                  onChange={(e) =>
                    setFormData({ ...formData, customer_phone: e.target.value })
                  }
                  placeholder="+91 9XXXXXXXXX"
                  autoComplete="off"
                  data-testid="ep-customer-phone"
                />
              </div>
              <div>
                <Label htmlFor="ep-cust-email">Email</Label>
                <Input
                  id="ep-cust-email"
                  type="email"
                  value={formData.customer_email}
                  onChange={(e) =>
                    setFormData({ ...formData, customer_email: e.target.value })
                  }
                  placeholder="customer@example.com"
                  autoComplete="off"
                  data-testid="ep-customer-email"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="ep-cust-address">Address</Label>
              <Textarea
                id="ep-cust-address"
                value={formData.customer_address}
                onChange={(e) =>
                  setFormData({ ...formData, customer_address: e.target.value })
                }
                rows={2}
                placeholder="Street, city, state, ZIP"
                data-testid="ep-customer-address"
              />
            </div>
          </div>

          <div className="space-y-3 rounded-lg border p-3">
            <p className="text-sm font-medium text-gray-800">Policy</p>
            <div>
              <Label htmlFor="ep-policy-no">Policy number *</Label>
              <Input
                id="ep-policy-no"
                value={formData.policy_number}
                onChange={(e) => setFormData({ ...formData, policy_number: e.target.value })}
                required
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label>Insurance type *</Label>
                <Select
                  value={
                    formData.insurance_type_id ? String(formData.insurance_type_id) : ''
                  }
                  onValueChange={(v) =>
                    setFormData((prev) => ({
                      ...prev,
                      insurance_type_id: v,
                      policy_type_id: '',
                    }))
                  }
                >
                  <SelectTrigger data-testid="ep-insurance-type">
                    <SelectValue placeholder="Select category…" />
                  </SelectTrigger>
                  <SelectContent>
                    {insuranceTypes.map((t) => (
                      <SelectItem key={t.id} value={String(t.id)}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Policy type *</Label>
                <Select
                  value={formData.policy_type_id ? String(formData.policy_type_id) : ''}
                  onValueChange={(v) =>
                    setFormData((prev) => ({ ...prev, policy_type_id: v }))
                  }
                  disabled={!formData.insurance_type_id || policyTypes.length === 0}
                >
                  <SelectTrigger data-testid="ep-policy-type">
                    <SelectValue
                      placeholder={
                        formData.insurance_type_id
                          ? policyTypes.length
                            ? 'Select variant…'
                            : 'No variants'
                          : 'Pick insurance type first'
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {policyTypes.map((t) => (
                      <SelectItem key={t.id} value={String(t.id)}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
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
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="ep-save-btn">
              {loading ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EditPolicyDialog;
