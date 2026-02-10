import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatCard } from '../components/dashboard/StatCard';
import { ChartPlaceholder } from '../components/dashboard/ChartPlaceholder';
import { InvoiceTable } from '../components/invoice/InvoiceTable';
import { Card } from '../components/common/Card';
import { SystemStatusCard } from '../components/system/SystemStatusCard';
import { ApiUsageCard } from '../components/system/ApiUsageCard';
import { useLanguage } from '../context/LanguageContext';
import { Invoice, AIInsight } from '../types/invoice';
import { listInvoices } from '../lib/invoiceApi';
import { getStatusBreakdown, getRevenueSummary } from '../lib/reportsApi';
import { InvoiceListItem } from '../types/invoiceHistory';
import { DashboardSkeleton } from '../components/dashboard/DashboardSkeleton';

/** Map API status to display status for InvoiceTable */
function mapStatus(s: string): Invoice['status'] {
  const lower = s.toUpperCase();
  if (lower === 'CLEARED') return 'cleared';
  if (lower === 'REJECTED' || lower === 'ERROR' || lower === 'FAILED') return 'rejected';
  if (lower === 'SUBMITTED' || lower === 'CREATED' || lower === 'PROCESSING') return 'pending';
  return s as Invoice['status'];
}

/** Map InvoiceListItem to Invoice for table (list endpoint does not include seller/buyer/totals) */
function listItemToInvoice(item: InvoiceListItem): Invoice {
  return {
    id: String(item.id),
    invoiceNumber: item.invoice_number,
    phase: 2,
    status: mapStatus(item.status),
    date: item.created_at,
    sellerName: '—',
    totalAmount: 0,
    taxAmount: 0,
    environment: item.environment as 'sandbox' | 'production' | 'SANDBOX' | 'PRODUCTION',
    uuid: item.uuid ?? undefined,
  };
}

const placeholderAIInsights: AIInsight[] = [
  {
    id: '1',
    type: 'readiness',
    title: 'Use AI Explain Error',
    description: 'On rejected invoices, use "Explain Error" to get AI-powered fix suggestions.',
    severity: 'low',
    timestamp: new Date().toISOString(),
  },
  {
    id: '2',
    type: 'prediction',
    title: 'Rejection prediction',
    description: 'Before submitting, use "Predict Rejection" in the API Playground to check compliance risk.',
    severity: 'low',
    timestamp: new Date().toISOString(),
  },
];

export const Dashboard: React.FC = () => {
  const { t, direction } = useLanguage();
  const navigate = useNavigate();
  const [statsLoading, setStatsLoading] = useState(true);
  const [recentLoading, setRecentLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [recentError, setRecentError] = useState<string | null>(null);
  const [totalInvoices, setTotalInvoices] = useState(0);
  const [clearedCount, setClearedCount] = useState(0);
  const [rejectedCount, setRejectedCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [recentInvoices, setRecentInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setStatsLoading(true);
        setStatsError(null);
        const [breakdown, revenue] = await Promise.all([
          getStatusBreakdown(),
          getRevenueSummary(),
        ]);
        setTotalInvoices(revenue.total_invoice_count);
        setClearedCount(revenue.cleared_invoice_count);
        const rejected = breakdown.breakdown.find((b) => b.status === 'REJECTED')?.count ?? 0;
        const failed = breakdown.breakdown.find((b) => b.status === 'FAILED')?.count ?? 0;
        setRejectedCount(rejected + failed);
        const created = breakdown.breakdown.find((b) => b.status === 'CREATED')?.count ?? 0;
        const processing = breakdown.breakdown.find((b) => b.status === 'PROCESSING')?.count ?? 0;
        setPendingCount(created + processing);
      } catch (err: unknown) {
        setStatsError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        setStatsLoading(false);
      }
    };
    fetchStats();
  }, []);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        setRecentLoading(true);
        setRecentError(null);
        const data = await listInvoices({ page: 1, limit: 5 });
        setRecentInvoices(data.invoices.map(listItemToInvoice));
      } catch (err: unknown) {
        setRecentError(err instanceof Error ? err.message : 'Failed to load recent invoices');
      } finally {
        setRecentLoading(false);
      }
    };
    fetchRecent();
  }, []);

  const handleViewInvoice = (invoice: Invoice) => {
    navigate(`/invoices/${invoice.id}`);
  };

  if (statsLoading && totalInvoices === 0 && !statsError) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6" dir={direction} data-testid="dashboard-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t('dashboard.title')}</h1>
        <p className="text-slate-500 mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {statsError && (
        <Card padding="md" className="bg-amber-50 border-amber-200">
          <p className="text-sm text-amber-800">{statsError}</p>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" data-testid="dashboard-stats">
        <StatCard
          title={t('dashboard.totalInvoices')}
          value={statsLoading ? '—' : totalInvoices.toLocaleString()}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
        <StatCard
          title={t('dashboard.cleared')}
          value={statsLoading ? '—' : clearedCount.toLocaleString()}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title={t('dashboard.rejected')}
          value={statsLoading ? '—' : rejectedCount.toLocaleString()}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title={t('dashboard.pending')}
          value={statsLoading ? '—' : pendingCount.toLocaleString()}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SystemStatusCard />
        <ApiUsageCard />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ChartPlaceholder title={t('dashboard.clearanceChart')} height={300} />
        </div>
        <div>
          <Card padding="md">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">{t('dashboard.aiInsights')}</h3>
            <div className="space-y-4">
              {placeholderAIInsights.map((insight) => (
                <div key={insight.id} className="p-3 rounded-lg border border-slate-200 bg-slate-50">
                  <div className="flex items-start justify-between mb-1">
                    <h4 className="text-sm font-medium text-slate-900">{insight.title}</h4>
                    <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800">{insight.severity}</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{insight.description}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">{t('dashboard.recentInvoices')}</h2>
        {recentError && (
          <Card padding="md" className="bg-amber-50 border-amber-200 mb-4">
            <p className="text-sm text-amber-800">{recentError}</p>
          </Card>
        )}
        <InvoiceTable
          invoices={recentInvoices}
          onView={handleViewInvoice}
          isLoading={recentLoading}
        />
      </div>
    </div>
  );
};

