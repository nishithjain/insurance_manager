import React from 'react';
import { Link } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

/** Summary tile linking to the full missed-opportunities resolution page. */
const MissedOpportunitiesCard = ({ count }) => (
  <Card className="mb-8 shadow-sm" data-testid="missed-opportunities-section">
    <CardHeader>
      <CardTitle>Missed Opportunities</CardTitle>
      <CardDescription>
        Expired active policies with <strong>renewal status Open</strong>. Click the summary below
        to open the full resolution page (mix, table, notes).
      </CardDescription>
    </CardHeader>
    <CardContent>
      <div className="flex justify-center">
        <Link
          to="/missed-opportunities"
          className="group block w-full max-w-md rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          data-testid="missed-expired-open-count-link"
        >
          <div
            className="rounded-xl border-2 border-slate-300 bg-slate-50/90 px-6 py-5 text-center shadow-sm transition-colors group-hover:border-slate-400 group-hover:bg-slate-100/90"
            data-testid="missed-expired-open-count"
          >
            <p className="text-sm font-medium text-slate-900">
              <span aria-hidden="true">❌</span> Expired but NOT Renewed
            </p>
            <p className="text-xs text-slate-600 mt-0.5">Expired (renewal open)</p>
            <p className="mt-2 text-3xl font-bold tabular-nums text-slate-800">
              {count} <span aria-hidden="true">❌</span>
            </p>
            <p className="mt-3 text-xs text-indigo-600 font-medium group-hover:underline">
              Open resolution page →
            </p>
          </div>
        </Link>
      </div>
    </CardContent>
  </Card>
);

export default MissedOpportunitiesCard;
