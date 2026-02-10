import React, { useState, useEffect } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { useLanguage } from '../context/LanguageContext';
import {
  getStatusBreakdown,
  getRevenueSummary,
  getInvoiceReport,
  getVATSummary,
  type StatusBreakdownResponse,
  type RevenueSummaryResponse,
  type InvoiceReportResponse,
  type VATSummaryResponse,
} from '../lib/reportsApi';

export const Reports: React.FC = () => {
  const { direction, t } = useLanguage();
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'vat'>('overview');
  const [statusBreakdown, setStatusBreakdown] = useState<StatusBreakdownResponse | null>(null);
  const [revenueSummary, setRevenueSummary] = useState<RevenueSummaryResponse | null>(null);
  const [invoiceReport, setInvoiceReport] = useState<InvoiceReportResponse | null>(null);
  const [vatSummary, setVatSummary] = useState<VATSummaryResponse | null>(null);
  const [reportPage, setReportPage] = useState(1);
  const [vatGroupBy, setVatGroupBy] = useState<'day' | 'month'>('day');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        if (activeTab === 'overview') {
          const [breakdown, revenue] = await Promise.all([
            getStatusBreakdown(),
            getRevenueSummary(),
          ]);
          setStatusBreakdown(breakdown);
          setRevenueSummary(revenue);
        } else if (activeTab === 'invoices') {
          const report = await getInvoiceReport({ page: reportPage, page_size: 20 });
          setInvoiceReport(report);
        } else {
          const vat = await getVATSummary({ group_by: vatGroupBy });
          setVatSummary(vat);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load report');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [activeTab, reportPage, vatGroupBy]);

  const formatDate = (s: string) => {
    try {
      return new Date(s).toLocaleDateString(direction === 'rtl' ? 'ar-SA' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return s;
    }
  };

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat(direction === 'rtl' ? 'ar-SA' : 'en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);

  return (
    <div className="space-y-6" dir={direction} data-testid="reports-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          {direction === 'rtl' ? 'التقارير' : 'Reports'}
        </h1>
        <p className="text-slate-500 mt-1">
          {direction === 'rtl' ? 'ملخص الفواتير والضريبة والإيرادات.' : 'Invoice, VAT, and revenue summaries.'}
        </p>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {(['overview', 'invoices', 'vat'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === tab
                ? 'border-emerald-600 text-emerald-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {tab === 'overview' && (direction === 'rtl' ? 'نظرة عامة' : 'Overview')}
            {tab === 'invoices' && (direction === 'rtl' ? 'الفواتير' : 'Invoices')}
            {tab === 'vat' && (direction === 'rtl' ? 'الضريبة' : 'VAT')}
          </button>
        ))}
      </div>

      {error && (
        <Card padding="md" className="bg-red-50 border-red-200">
          <p className="text-sm text-red-800">{error}</p>
        </Card>
      )}

      {loading && activeTab === 'overview' && (
        <Card padding="md">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-slate-200 rounded w-1/3" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-20 bg-slate-200 rounded" />
              ))}
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'overview' && !loading && statusBreakdown && revenueSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card padding="md">
            <p className="text-sm text-slate-500">{direction === 'rtl' ? 'إجمالي الفواتير' : 'Total Invoices'}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{revenueSummary.total_invoice_count}</p>
          </Card>
          <Card padding="md">
            <p className="text-sm text-slate-500">{direction === 'rtl' ? 'مقبولة' : 'Cleared'}</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{revenueSummary.cleared_invoice_count}</p>
          </Card>
          <Card padding="md">
            <p className="text-sm text-slate-500">{direction === 'rtl' ? 'إجمالي الإيرادات' : 'Total Revenue'}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatCurrency(revenueSummary.total_revenue)}</p>
          </Card>
          <Card padding="md">
            <p className="text-sm text-slate-500">{direction === 'rtl' ? 'إجمالي الضريبة' : 'Total Tax'}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatCurrency(revenueSummary.total_tax)}</p>
          </Card>
        </div>
      )}

      {activeTab === 'overview' && !loading && statusBreakdown && (
        <Card padding="md">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">
            {direction === 'rtl' ? 'حالة الفواتير' : 'Status Breakdown'}
          </h3>
          <div className="flex flex-wrap gap-3">
            {statusBreakdown.breakdown.map((b) => (
              <Badge key={b.status} variant="info" className="text-sm">
                {b.status}: {b.count}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'invoices' && (
        <>
          {!loading && invoiceReport && (
            <>
              <Card padding="none" className="overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                          {t('invoice.number')}
                        </th>
                        <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                          {t('invoice.status')}
                        </th>
                        <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                          Phase
                        </th>
                        <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                          Amount
                        </th>
                        <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                          {t('invoice.date')}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {invoiceReport.invoices.map((inv) => (
                        <tr key={inv.invoice_number} className="hover:bg-slate-50">
                          <td className="px-4 py-3 text-sm font-medium text-slate-900">{inv.invoice_number}</td>
                          <td className="px-4 py-3">
                            <Badge variant={inv.status === 'CLEARED' ? 'success' : inv.status === 'REJECTED' ? 'danger' : 'default'}>
                              {inv.status}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{inv.phase}</td>
                          <td className="px-4 py-3 text-sm text-slate-600">{formatCurrency(inv.total_amount)}</td>
                          <td className="px-4 py-3 text-sm text-slate-600">{formatDate(inv.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {invoiceReport.total_pages > 1 && (
                  <div className="px-4 py-3 border-t border-slate-200 flex justify-between items-center">
                    <span className="text-sm text-slate-600">
                      {t('common.page')} {reportPage} {t('common.of')} {invoiceReport.total_pages}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setReportPage((p) => Math.max(1, p - 1))}
                        disabled={reportPage === 1}
                      >
                        {t('common.previous')}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setReportPage((p) => p + 1)}
                        disabled={reportPage >= invoiceReport.total_pages}
                      >
                        {t('common.next')}
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            </>
          )}
        </>
      )}

      {activeTab === 'vat' && (
        <>
          <div className="flex gap-2">
            <Button
              variant={vatGroupBy === 'day' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setVatGroupBy('day')}
            >
              By day
            </Button>
            <Button
              variant={vatGroupBy === 'month' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setVatGroupBy('month')}
            >
              By month
            </Button>
          </div>
          {!loading && vatSummary && (
            <Card padding="md">
              <div className="flex flex-wrap gap-4 mb-4">
                <p className="text-sm text-slate-600">
                  Total tax: <strong>{formatCurrency(vatSummary.total_tax_amount)}</strong>
                </p>
                <p className="text-sm text-slate-600">
                  Total amount: <strong>{formatCurrency(vatSummary.total_invoice_amount)}</strong>
                </p>
                <p className="text-sm text-slate-600">
                  Invoices: <strong>{vatSummary.total_invoice_count}</strong>
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">Date</th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">Tax</th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">Amount</th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {vatSummary.summary.map((row) => (
                      <tr key={row.date} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-900">{row.date}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{formatCurrency(row.total_tax_amount)}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{formatCurrency(row.total_invoice_amount)}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{row.invoice_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
};
