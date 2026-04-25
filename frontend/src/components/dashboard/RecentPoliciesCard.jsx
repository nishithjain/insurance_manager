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
  <Card data-testid="recent-policies">
    <CardHeader>
      <div className="flex flex-wrap justify-between items-center gap-2">
        <CardTitle>Recent Policies</CardTitle>
        <div className="flex flex-wrap gap-2">
          <AddInsuranceDialog
            customers={customers}
            policies={policies}
            onSuccess={onRefresh}
          />
          <AddCustomerDialog onSuccess={() => onRefresh()} />
        </div>
      </div>
      <CardDescription className="text-xs pt-1">
        Add a customer or policy, or edit a row below.
      </CardDescription>
    </CardHeader>
    <CardContent>
      {policies.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No policies yet</p>
      ) : (
        <div className="space-y-3">
          {policies.slice(0, 5).map((policy) => (
            <div
              key={policy.id}
              className="flex justify-between items-start gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <div className="min-w-0 flex-1 space-y-2">
                <p className="text-base text-gray-900 break-words">
                  <span className="text-gray-500">Customer name: </span>
                  <span className="font-semibold text-gray-900">
                    {customerNameById(customers, policy.customer_id)}
                  </span>
                </p>
                <div className="text-sm text-gray-700 space-y-0.5">
                  <p className="truncate">
                    <span className="text-gray-500">Policy number: </span>
                    {policy.policy_number || '—'}
                  </p>
                  <p className="truncate">
                    <span className="text-gray-500">Insurance type: </span>
                    {policy.insurance_type_name || policy.policy_type || '—'}
                  </p>
                  <p className="truncate">
                    <span className="text-gray-500">Policy type: </span>
                    {policy.policy_type_name || policy.policy_type || '—'}
                  </p>
                  <p className="truncate">
                    <span className="text-gray-500">Company: </span>
                    {policy.insurer_company && String(policy.insurer_company).trim()
                      ? policy.insurer_company
                      : '—'}
                  </p>
                  <p className="flex flex-wrap items-center gap-1.5">
                    <span className="text-gray-500">Active: </span>
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
                  className="h-8 w-8"
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
