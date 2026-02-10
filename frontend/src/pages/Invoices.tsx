import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { InvoiceStatusBadge } from '../components/invoice/InvoiceStatusBadge';
import { InvoiceListSkeleton } from '../components/invoice/InvoiceListSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { useLanguage } from '../context/LanguageContext';
import { listInvoices } from '../lib/invoiceApi';
import { exportInvoices, exportInvoiceLogs } from '../lib/exportsApi';
import { InvoiceListItem } from '../types/invoiceHistory';

export const Invoices: React.FC = () => {
  const { direction, t } = useLanguage();
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onOutside = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
    };
    document.addEventListener('click', onOutside);
    return () => document.removeEventListener('click', onOutside);
  }, []);

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await listInvoices({ page, limit: 50 });
        setInvoices(data.invoices);
        setTotalPages(data.total_pages);
        setTotal(data.total);
      } catch (err: unknown) {
        const apiError = err as { message?: string };
        setError(
          apiError.message || t('invoiceList.error')
        );
      } finally {
        setLoading(false);
      }
    };

    fetchInvoices();
  }, [page, direction]);

  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleString(direction === 'rtl' ? 'ar-SA' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  const getPhaseLabel = (environment: string): string => {
    return environment === 'PRODUCTION' ? 'Phase 2' : 'Phase 1';
  };

  const handleExport = async (type: 'invoices' | 'logs', format: 'csv' | 'json') => {
    setExportError(null);
    setExporting(true);
    try {
      if (type === 'invoices') await exportInvoices({ format });
      else await exportInvoiceLogs({ format });
      setExportOpen(false);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6" dir={direction} data-testid="invoices-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t('invoiceList.title')}
          </h1>
          <p className="text-slate-500 mt-1">
            {t('invoiceList.total')}: {total}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <div className="relative" ref={exportRef}>
            <Button
              variant="secondary"
              onClick={() => setExportOpen((o) => !o)}
              disabled={exporting}
              data-testid="export-invoices-button"
            >
              {exporting ? (direction === 'rtl' ? 'جاري التصدير...' : 'Exporting...') : t('common.export')}
            </Button>
            {exportOpen && (
              <div className="absolute top-full right-0 mt-1 w-48 py-1 bg-white border border-slate-200 rounded-lg shadow-lg z-10">
                <button type="button" className="block w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => handleExport('invoices', 'csv')}>Invoices (CSV)</button>
                <button type="button" className="block w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => handleExport('invoices', 'json')}>Invoices (JSON)</button>
                <button type="button" className="block w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => handleExport('logs', 'csv')}>Invoice logs (CSV)</button>
                <button type="button" className="block w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => handleExport('logs', 'json')}>Invoice logs (JSON)</button>
              </div>
            )}
          </div>
          <Button variant="primary" onClick={() => navigate('/invoices/create')} data-testid="create-invoice-button">
            {t('invoiceList.createInvoice')}
          </Button>
        </div>
      </div>

      {exportError && (
        <Card padding="md" className="bg-amber-50 border-amber-200">
          <p className="text-sm text-amber-800">{exportError}</p>
        </Card>
      )}

      {/* Loading State - Show skeleton inside invoice-list container */}
      {loading && invoices.length === 0 && !error && (
        <Card padding="none" className="overflow-hidden" data-testid="invoice-list">
          <InvoiceListSkeleton />
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card padding="md" data-testid="error-state">
          <EmptyState
            icon={
              <svg
                className="w-16 h-16 text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            }
            title={t('error.generic')}
            description={error}
            actionLabel={t('common.retry')}
            onAction={() => window.location.reload()}
          />
        </Card>
      )}

      {/* Invoice Table - Always render container, show content or empty state */}
      {!error && (
        <Card padding="none" className="overflow-hidden" data-testid="invoice-list">
          {invoices.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={
                  <svg
                    className="w-16 h-16 text-slate-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                }
                title={t('invoiceList.empty')}
                description={t('invoiceList.emptyDesc')}
                actionLabel={t('invoiceList.createInvoice')}
                onAction={() => navigate('/invoices/create')}
              />
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full" data-testid="invoice-table">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                        {t('invoice.number')}
                      </th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                        {t('invoice.phase')}
                      </th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                        {t('invoice.status')}
                      </th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                        {t('invoice.date')}
                      </th>
                      <th className="px-4 py-3 text-start text-xs font-semibold text-slate-700 uppercase">
                        {t('topbar.environment.sandbox')} / {t('topbar.environment.production')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {invoices.map((invoice) => (
                      <tr
                        key={invoice.id}
                        onClick={() => navigate(`/invoices/${invoice.id}`)}
                        className="hover:bg-slate-50 cursor-pointer transition-colors"
                        data-testid={`invoice-row-${invoice.id}`}
                      >
                        <td className="px-4 py-3 text-sm font-medium text-slate-900">
                          {invoice.invoice_number}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {getPhaseLabel(invoice.environment)}
                        </td>
                        <td className="px-4 py-3">
                          <InvoiceStatusBadge status={invoice.status} />
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {formatDate(invoice.created_at)}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {invoice.environment}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-3 border-t border-slate-200 flex items-center justify-between" data-testid="pagination">
                  <div className="text-sm text-slate-600">
                    {t('common.page')} {page} {t('common.of')} {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      data-testid="pagination-prev"
                    >
                      {t('common.previous')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      data-testid="pagination-next"
                    >
                      {t('common.next')}
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      )}
    </div>
  );
};

