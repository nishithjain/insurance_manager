import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Pencil } from 'lucide-react';
import AddCustomerDialog from '@/components/AddCustomerDialog';
import AddInsuranceDialog from '@/components/AddInsuranceDialog';

const customerNameById = (customers, customerId) => {
  const c = customers.find((x) => String(x.id) === String(customerId));
  return c?.name?.trim() || '—';
};

/** "Recent Policies" panel with the add-customer and add-policy CTAs. */
const RecentPoliciesCard = ({ policies, customers, onRefresh, onEditPolicy }) => (
  <Card
    className="rounded-2xl border border-[#E5E7EB] bg-white shadow-[0_2px_8px_rgba(15,23,42,0.06)]"
    data-testid="recent-policies"
  >
    <CardHeader className="p-4 pb-2 sm:p-5 sm:pb-2">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <CardTitle className="text-base font-bold text-[#0F172A] sm:text-lg">Recent Policies</CardTitle>
        <div className="flex flex-wrap gap-2 [&_button]:rounded-xl [&_button]:transition-all [&_button]:duration-150 [&_button:active]:scale-[0.98]">
          <AddInsuranceDialog
            customers={customers}
            policies={policies}
            onSuccess={onRefresh}
          />
          <AddCustomerDialog onSuccess={() => onRefresh()} />
        </div>
      </div>
      <CardDescription className="pt-1 text-xs text-[#64748B]">
        Add a customer or policy, or edit a row below.
      </CardDescription>
    </CardHeader>
    <CardContent className="p-4 pt-2 sm:p-5 sm:pt-3">
      {policies.length === 0 ? (
        <p className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] py-6 text-center text-sm text-[#64748B]">No policies yet</p>
      ) : (
        <div className="space-y-2.5">
          {policies.slice(0, 5).map((policy) => (
            <div
              key={policy.id}
              className="flex items-start justify-between gap-3 rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3 transition-all duration-150 active:scale-[0.98]"
            >
              <div className="min-w-0 flex-1 space-y-2">
                <p className="break-words text-sm text-[#0F172A] sm:text-base">
                  <span className="text-[#64748B]">Customer name: </span>
                  <span className="font-semibold text-[#0F172A]">
                    {customerNameById(customers, policy.customer_id)}
                  </span>
                </p>
                <div className="space-y-0.5 text-sm text-[#334155]">
                  <p className="truncate">
                    <span className="text-[#64748B]">Policy number: </span>
                    {policy.policy_number || '—'}
                  </p>
                  <p className="truncate">
                    <span className="text-[#64748B]">Insurance type: </span>
                    {policy.insurance_type_name || policy.policy_type || '—'}
                  </p>
                  <p className="truncate">
                    <span className="text-[#64748B]">Policy type: </span>
                    {policy.policy_type_name || policy.policy_type || '—'}
                  </p>
                  <p className="truncate">
                    <span className="text-[#64748B]">Company: </span>
                    {policy.insurer_company && String(policy.insurer_company).trim()
                      ? policy.insurer_company
                      : '—'}
                  </p>
                  <p className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[#64748B]">Active: </span>
                    <Badge variant={policy.status === 'active' ? 'default' : 'secondary'}>
                      {policy.status}
                    </Badge>
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-1 shrink-0 pt-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-xl transition-all duration-150 active:scale-[0.98]"
                  onClick={() => onEditPolicy(policy)}
                  aria-label="Edit policy"
                  data-testid={`edit-policy-${policy.id}`}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </CardContent>
  </Card>
);

export default RecentPoliciesCard;
