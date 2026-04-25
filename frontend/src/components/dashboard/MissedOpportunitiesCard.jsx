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
  <Card
    className="mb-3 rounded-2xl border border-[#E5E7EB] bg-white shadow-[0_2px_8px_rgba(15,23,42,0.06)] sm:mb-4"
    data-testid="missed-opportunities-section"
  >
    <CardHeader className="p-4 pb-2 sm:p-5 sm:pb-2">
      <CardTitle className="text-base font-bold text-[#0F172A] sm:text-lg">Missed Opportunities</CardTitle>
      <CardDescription className="text-xs leading-relaxed text-[#64748B] sm:text-sm">
        Expired active policies with <strong>renewal status Open</strong>. Click the summary below
        to open the full resolution page (mix, table, notes).
      </CardDescription>
    </CardHeader>
    <CardContent className="p-4 pt-2 sm:p-5 sm:pt-2">
      <div className="flex justify-center">
        <Link
          to="/missed-opportunities"
          className="group block w-full max-w-md rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2563EB] focus-visible:ring-offset-2"
          data-testid="missed-expired-open-count-link"
        >
          <div
            className="rounded-2xl border border-[#E5E7EB] bg-[#F8FAFC] px-4 py-3 text-center transition-all duration-150 group-hover:bg-[#F1F5F9] group-active:scale-[0.98]"
            data-testid="missed-expired-open-count"
          >
            <p className="text-xs font-semibold text-[#64748B]">
              <span aria-hidden="true">❌</span> Expired but NOT Renewed
            </p>
            <p className="mt-0.5 text-xs text-[#64748B]">Expired (renewal open)</p>
            <p className="mt-1 text-[24px] font-bold leading-tight tabular-nums text-[#DC2626] sm:text-[26px]">
              {count} <span aria-hidden="true">❌</span>
            </p>
            <p className="mt-1 text-xs font-medium text-[#2563EB] group-hover:underline">
              Open resolution page →
            </p>
          </div>
        </Link>
      </div>
    </CardContent>
  </Card>
);

export default MissedOpportunitiesCard;
