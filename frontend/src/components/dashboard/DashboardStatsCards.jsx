import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { FileText, Users, Wallet } from 'lucide-react';

/** Four headline metrics shown above the dashboard sections. */
const DashboardStatsCards = ({
  totalPolicies,
  activePolicies,
  customers,
  pendingPaymentCount,
}) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <Card data-testid="total-policies-card">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Total Policies</p>
            <p className="text-3xl font-bold text-gray-900">{totalPolicies}</p>
          </div>
          <FileText className="w-12 h-12 text-indigo-600 opacity-20" />
        </div>
      </CardContent>
    </Card>

    <Card data-testid="active-policies-card">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Active Policies</p>
            <p className="text-3xl font-bold text-green-600">{activePolicies}</p>
          </div>
          <FileText className="w-12 h-12 text-green-600 opacity-20" />
        </div>
      </CardContent>
    </Card>

    <Card data-testid="customers-card">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Customers</p>
            <p className="text-3xl font-bold text-blue-600">{customers}</p>
          </div>
          <Users className="w-12 h-12 text-blue-600 opacity-20" />
        </div>
      </CardContent>
    </Card>

    <Card data-testid="pending-payments-summary-card">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Pending payments</p>
            <p className="text-3xl font-bold text-amber-600">{pendingPaymentCount}</p>
          </div>
          <Wallet className="w-12 h-12 text-amber-600 opacity-20" />
        </div>
      </CardContent>
    </Card>
  </div>
);

export default DashboardStatsCards;
