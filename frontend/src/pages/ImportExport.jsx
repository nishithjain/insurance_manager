import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  policyAPI,
  customerAPI,
  importAPI,
  exportAPI,
} from '@/utils/api';
import { FileText, ArrowLeft, Upload, Download, AlertCircle, Archive } from 'lucide-react';

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const ImportExport = () => {
  const [loading, setLoading] = useState(true);
  const [policies, setPolicies] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [statementRows, setStatementRows] = useState(null);
  const [importingStatements, setImportingStatements] = useState(false);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvReplaceExisting, setCsvReplaceExisting] = useState(true);
  const [csvPromote, setCsvPromote] = useState(false);
  const csvFileInputRef = useRef(null);
  const [exportYear, setExportYear] = useState(() => new Date().getFullYear());
  const [exportMonth, setExportMonth] = useState(() => new Date().getMonth() + 1);
  const [exportBy, setExportBy] = useState('policy_end_date');
  const [exportLoading, setExportLoading] = useState(false);
  const [fullZipLoading, setFullZipLoading] = useState(false);

  const exportYearOptions = useMemo(() => {
    const hi = new Date().getFullYear() + 2;
    const lo = 2000;
    return Array.from({ length: hi - lo + 1 }, (_, i) => hi - i);
  }, []);

  const loadPolicies = async () => {
    try {
      const response = await policyAPI.getAll();
      setPolicies(response.data);
    } catch (error) {
      console.error('Failed to load policies:', error);
    }
  };

  const loadCustomers = async () => {
    try {
      const response = await customerAPI.getAll();
      setCustomers(response.data);
    } catch (error) {
      console.error('Failed to load customers:', error);
    }
  };

  const refreshInsuranceData = () => Promise.all([loadPolicies(), loadCustomers()]);

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([
          loadPolicies(),
          loadCustomers(),
          importAPI
            .statementSummary()
            .then((r) => setStatementRows(r.data.statement_rows))
            .catch(() => setStatementRows(null)),
        ]);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleStatementCsvSelected = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Please choose a .csv file (export from Excel as CSV).');
      return;
    }
    setCsvUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('replace_existing', String(csvReplaceExisting));
      fd.append('promote_to_dashboard', String(csvPromote));
      const res = await importAPI.uploadStatementCsv(fd);
      const d = res.data;
      let msg = `Imported ${d.rows_inserted} row(s) from ${d.source_file}.`;
      if (d.materialize) {
        const m = d.materialize;
        msg +=
          ` Dashboard: ${m.policies_created} policies (${m.customers_created} new customers), ${m.policies_skipped} skipped.`;
      }
      alert(msg);
      const s = await importAPI.statementSummary();
      setStatementRows(s.data.statement_rows);
      await refreshInsuranceData();
    } catch (err) {
      console.error('CSV upload failed:', err);
      const detail = err.response?.data?.detail;
      alert(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((x) => x.msg || x).join(' ')
            : err.message || 'Upload failed'
      );
    } finally {
      setCsvUploading(false);
    }
  };

  const handleImportStatementLines = async () => {
    setImportingStatements(true);
    try {
      const res = await importAPI.statementLinesToPolicies();
      const d = res.data;
      alert(
        `Created ${d.policies_created} policies (${d.customers_created} new customers). ` +
          `Skipped ${d.policies_skipped} duplicate policy numbers.`
      );
      await refreshInsuranceData();
      const s = await importAPI.statementSummary();
      setStatementRows(s.data.statement_rows);
    } catch (error) {
      console.error('Statement import failed:', error);
      alert(error.response?.data?.detail || error.message || 'Import failed');
    } finally {
      setImportingStatements(false);
    }
  };

  const handleExportPoliciesCsv = async () => {
    setExportLoading(true);
    try {
      const res = await exportAPI.downloadPoliciesMonthly({
        year: exportYear,
        month: exportMonth,
        by: exportBy,
      });
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cd = res.headers['content-disposition'];
      const m = cd && /filename="([^"]+)"/.exec(cd);
      const fallback = `policies_${exportYear}-${String(exportMonth).padStart(2, '0')}.csv`;
      a.download = m ? m[1] : fallback;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      let msg = error.message || 'Export failed';
      const raw = error.response?.data;
      if (raw instanceof Blob) {
        try {
          const text = await raw.text();
          const j = JSON.parse(text);
          msg = typeof j.detail === 'string' ? j.detail : msg;
        } catch {
          msg = 'Export failed';
        }
      } else if (error.response?.data?.detail) {
        msg =
          typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail);
      }
      alert(msg);
    } finally {
      setExportLoading(false);
    }
  };

  const handleFullDataZip = async () => {
    setFullZipLoading(true);
    try {
      const res = await exportAPI.downloadFullDataZip();
      const blob = new Blob([res.data], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cd = res.headers['content-disposition'];
      const m = cd && /filename="([^"]+)"/.exec(cd);
      a.download = m ? m[1] : 'insurance_full_export.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Full export failed:', error);
      let msg = error.message || 'Export failed';
      const raw = error.response?.data;
      if (raw instanceof Blob) {
        try {
          const text = await raw.text();
          const j = JSON.parse(text);
          msg = typeof j.detail === 'string' ? j.detail : msg;
        } catch {
          msg = 'Export failed';
        }
      } else if (error.response?.data?.detail) {
        msg =
          typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail);
      }
      alert(msg);
    } finally {
      setFullZipLoading(false);
    }
  };

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
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <FileText className="w-6 h-6 text-indigo-600" />
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">Import &amp; Export</h1>
                  <p className="text-sm text-gray-500">Local</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link to="/statements">
                <Button variant="outline" size="sm">
                  Statement CSV table
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <Card data-testid="statement-csv-upload-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Upload statement CSV</CardTitle>
            <CardDescription>
              Import rows into the database (same columns as the March statements template). Use a .csv
              file — not .xlsx.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <input
              ref={csvFileInputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={handleStatementCsvSelected}
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="secondary"
                disabled={csvUploading}
                onClick={() => csvFileInputRef.current?.click()}
                data-testid="statement-csv-upload-btn"
              >
                <Upload className="w-4 h-4 mr-2" />
                {csvUploading ? 'Uploading…' : 'Choose CSV file'}
              </Button>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={csvReplaceExisting}
                onChange={(e) => setCsvReplaceExisting(e.target.checked)}
              />
              Replace existing rows for this filename
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={csvPromote}
                onChange={(e) => setCsvPromote(e.target.checked)}
              />
              Also load into customers and policies (same as &quot;Load CSV rows into dashboard&quot;)
            </label>
          </CardContent>
        </Card>

        {statementRows != null && statementRows > 0 && (
          <Alert data-testid="statement-import-hint">
            <FileText className="h-4 w-4" />
            <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span>
                Your database has {statementRows} row(s) from the statement CSV (name = first line of
                column 1; rest = address). Open{' '}
                <Link className="underline font-medium" to="/statements">
                  Statement CSV table
                </Link>{' '}
                to review. If you have no policies yet, rows can be copied into customers and policies
                from the dashboard when you first open it, or use the button below.
              </span>
              <Button
                type="button"
                variant="secondary"
                disabled={importingStatements}
                onClick={handleImportStatementLines}
              >
                {importingStatements ? 'Loading…' : 'Load CSV rows into dashboard'}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <Card data-testid="export-policies-csv-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Export policies (CSV)</CardTitle>
            <CardDescription>
              Choose a calendar month and year, then pick whether to export by policies{' '}
              <strong>issued</strong> in that month or policies <strong>expiring</strong> (end date) in
              that month. Columns are business-friendly (customer, category, primary details, premium, …)
              with a full JSON <code className="text-xs bg-gray-100 px-1 rounded">extra_details</code>{' '}
              cell preserving motor, health, and property tables plus policy extras.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-4 sm:items-end">
              <div className="flex flex-col gap-1 min-w-[140px]">
                <label htmlFor="ie-export-month" className="text-sm font-medium text-gray-700">
                  Month
                </label>
                <select
                  id="ie-export-month"
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white text-gray-900"
                  value={exportMonth}
                  onChange={(e) => setExportMonth(Number(e.target.value))}
                >
                  {MONTH_NAMES.map((name, idx) => (
                    <option key={name} value={idx + 1}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1 min-w-[100px]">
                <label htmlFor="ie-export-year" className="text-sm font-medium text-gray-700">
                  Year
                </label>
                <select
                  id="ie-export-year"
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white text-gray-900"
                  value={exportYear}
                  onChange={(e) => setExportYear(Number(e.target.value))}
                >
                  {exportYearOptions.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1 min-w-[260px] flex-1 max-w-md">
                <label htmlFor="ie-export-by" className="text-sm font-medium text-gray-700">
                  Month is based on
                </label>
                <select
                  id="ie-export-by"
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white text-gray-900"
                  value={exportBy}
                  onChange={(e) => setExportBy(e.target.value)}
                >
                  <option value="policy_end_date">Expiring this month</option>
                  <option value="date_of_issue">Month of issue</option>
                </select>
              </div>
              <Button
                type="button"
                variant="secondary"
                disabled={exportLoading}
                onClick={handleExportPoliciesCsv}
                data-testid="export-policies-csv-btn"
              >
                <Download className="w-4 h-4 mr-2" />
                {exportLoading ? 'Preparing…' : 'Download CSV'}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="export-full-data-zip-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Export complete data (ZIP)</CardTitle>
            <CardDescription>
              Download a ZIP: customers, addresses, policies (slim columns +{' '}
              <code className="text-xs bg-gray-100 px-1 rounded">extra_details</code> JSON), split CSVs by
              category (motor / health / non-motor), renewal history, and the statement import staging table.
              Use for backups or offline analysis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              type="button"
              variant="secondary"
              disabled={fullZipLoading}
              onClick={handleFullDataZip}
              data-testid="export-full-data-zip-btn"
            >
              <Archive className="w-4 h-4 mr-2" />
              {fullZipLoading ? 'Building ZIP…' : 'Download full export (ZIP)'}
            </Button>
            <p className="mt-3 text-xs text-gray-500">
              Includes <code className="text-xs bg-gray-100 px-1 rounded">README.txt</code> describing
              each file.
            </p>
          </CardContent>
        </Card>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Customers loaded:</strong> {customers.length} — <strong>Policies:</strong>{' '}
            {policies.length}
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
};

export default ImportExport;
