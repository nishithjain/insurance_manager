import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { policyAPI } from '@/utils/api';
import { PAYMENT_UPDATE_OPTIONS_FROM_PENDING } from '@/utils/paymentStatus';

/**
 * Update payment status when policy is PENDING (clears from pending list after save).
 * @param {{ policy: object|null, open: boolean, onOpenChange: (open: boolean) => void, onSuccess?: (policy: object) => void }} props
 */
const UpdatePaymentDialog = ({ policy, open, onOpenChange, onSuccess }) => {
  const [status, setStatus] = useState(PAYMENT_UPDATE_OPTIONS_FROM_PENDING[0]);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && policy) {
      setStatus(PAYMENT_UPDATE_OPTIONS_FROM_PENDING[0]);
      setNote('');
      setError(null);
    }
  }, [open, policy?.id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!policy) return;
    setLoading(true);
    setError(null);
    try {
      const res = await policyAPI.patchPayment(policy.id, {
        payment_status: status,
        payment_note: note.trim() || undefined,
      });
      onSuccess?.(res.data);
      onOpenChange(false);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : JSON.stringify(d || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!policy) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Update payment</DialogTitle>
            <DialogDescription>
              Policy <span className="font-mono text-xs">{policy.policy_number || policy.id}</span> is
              currently <strong>PENDING</strong>. Choose how payment was received.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="pay-status">New payment status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger id="pay-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_UPDATE_OPTIONS_FROM_PENDING.map((opt) => (
                    <SelectItem key={opt} value={opt}>
                      {opt}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="pay-note">Payment note (optional)</Label>
              <Textarea
                id="pay-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Reference, UTR, cheque no., etc."
                rows={3}
                className="resize-y min-h-[72px]"
              />
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving…' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default UpdatePaymentDialog;
