import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { importAPI } from '@/utils/api';
import { ArrowLeft } from 'lucide-react';

const Statements = () => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await importAPI.listStatementLines();
        setRows(res.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center gap-4 flex-wrap">
              <Link to="/dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Dashboard
                </Button>
              </Link>
              <Link to="/import-export">
                <Button variant="outline" size="sm">
                  Import &amp; Export
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <img src="/InsuranceManager.png" alt="" className="w-8 h-8 rounded-md object-cover" />
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">Statement CSV import</h1>
                  <p className="text-sm text-gray-500">
                    Name = first line of the CSV cell; address = remaining lines
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[140px]">Customer name</TableHead>
                <TableHead className="min-w-[200px]">Address</TableHead>
                <TableHead>Phone number</TableHead>
                <TableHead className="min-w-[180px] max-w-[240px] leading-snug">
                  Vehicle no. · product or vehicle details
                </TableHead>
                <TableHead>Company (insurer)</TableHead>
                <TableHead>Policy number</TableHead>
                <TableHead>Premium</TableHead>
                <TableHead>Policy end date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-gray-500 py-12">
                    No statement rows yet. Import a CSV with{' '}
                    <code className="text-xs bg-gray-100 px-1 rounded">import_march_statements.py</code>.
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium align-top whitespace-pre-wrap max-w-[220px]">
                      {r.customer_name}
                    </TableCell>
                    <TableCell className="text-gray-700 align-top whitespace-pre-wrap max-w-[320px]">
                      {r.address || '—'}
                    </TableCell>
                    <TableCell className="align-top">{r.phone_number || '—'}</TableCell>
                    <TableCell className="align-top text-sm">
                      {[r.vehicle_registration, r.vehicle_details].filter(Boolean).join(' · ') ||
                        '—'}
                    </TableCell>
                    <TableCell className="align-top text-sm">{r.insurer_company || '—'}</TableCell>
                    <TableCell className="align-top text-sm font-mono">{r.policy_number || '—'}</TableCell>
                    <TableCell className="align-top">{r.premium_total || '—'}</TableCell>
                    <TableCell className="align-top whitespace-nowrap">{r.policy_end_date || '—'}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <p className="mt-4 text-sm text-gray-500">
          Showing up to 5,000 rows (newest first).
          {rows.length > 0 ? ` Source file: ${rows[0].source_file}.` : ''}
        </p>
      </div>
    </div>
  );
};

export default Statements;
