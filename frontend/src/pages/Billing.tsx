import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { UsageMeter } from '../components/billing/UsageMeter';
import { LimitBanner } from '../components/billing/LimitBanner';
import { BillingSkeleton } from '../components/billing/BillingSkeleton';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { useLanguage } from '../context/LanguageContext';
import { getCurrentSubscription, getUsage } from '../lib/billingApi';
import { Subscription } from '../types/subscription';
import { Usage } from '../types/usage';

export const Billing: React.FC = () => {
  const { direction, t } = useLanguage();
  const navigate = useNavigate();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPlanChangeModal, setShowPlanChangeModal] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [subData, usageData] = await Promise.all([
          getCurrentSubscription(),
          getUsage(),
        ]);

        setSubscription(subData);
        setUsage(usageData);
      } catch (err: unknown) {
        const apiError = err as { message?: string };
        setError(
          apiError.message || t('error.generic')
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [direction]);

  const getStatusBadgeVariant = (status: string): 'success' | 'warning' | 'danger' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'trial':
        return 'warning';
      case 'expired':
      case 'suspended':
        return 'danger';
      default:
        return 'warning';
    }
  };

  const formatBillingPeriod = (period: string): string => {
    try {
      const [year, month] = period.split('-');
      const date = new Date(parseInt(year), parseInt(month) - 1);
      return date.toLocaleDateString(direction === 'rtl' ? 'ar-SA' : 'en-US', {
        year: 'numeric',
        month: 'long',
      });
    } catch {
      return period;
    }
  };

  const hasLimitExceeded = usage && (usage.invoice_limit_exceeded || usage.ai_limit_exceeded);

  if (loading) {
    return (
      <div className="space-y-8" dir={direction}>
        <BillingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6" dir={direction}>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t('billing.title')}
          </h1>
        </div>
        <Card padding="md">
          <div className="text-center py-8">
            <p className="text-red-600 mb-4 break-words">{error}</p>
            <Button onClick={() => window.location.reload()}>
              {t('common.retry')}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // No subscription (404 from backend)
  if (!subscription && !usage) {
    return (
      <div className="space-y-6" dir={direction}>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t('billing.title')}
          </h1>
          <p className="text-slate-500 mt-1">
            {t('billing.subtitle')}
          </p>
        </div>
        <Card padding="lg">
          <div className="text-center py-12">
            <svg
              className="w-16 h-16 text-slate-400 mx-auto mb-4"
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
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              {t('billing.noSubscription')}
            </h3>
            <p className="text-slate-600 mb-6 max-w-md mx-auto">
              {t('billing.noSubscriptionDesc')}
            </p>
            <Button onClick={() => navigate('/plans')}>
              {t('billing.viewPlans')}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8" dir={direction} data-testid="billing-page">
      {/* Limit Banner — at the very top */}
      {hasLimitExceeded && (
        <LimitBanner
          invoiceLimitExceeded={usage?.invoice_limit_exceeded}
          aiLimitExceeded={usage?.ai_limit_exceeded}
        />
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          {t('billing.title')}
        </h1>
        <p className="text-slate-500 mt-1">
          {t('billing.subtitle')}
        </p>
      </div>

      {/* Current Subscription — improved spacing */}
      {subscription && (
        <Card padding="lg" data-testid="current-subscription-card">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {t('billing.currentPlan')}
                </h2>
                <p className="text-sm text-slate-600 mt-1" data-testid="plan-name">
                  {subscription.plan_name}
                </p>
              </div>
              <Badge variant={getStatusBadgeVariant(subscription.status)} data-testid="subscription-status">
                {subscription.status === 'active'
                  ? t('billing.status.active')
                  : subscription.status === 'trial'
                  ? t('billing.status.trial')
                  : subscription.status === 'expired'
                  ? t('billing.status.expired')
                  : t('billing.status.suspended')}
              </Badge>
            </div>

            {subscription.trial_days_remaining != null && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-900">
                  {t('billing.trialDaysRemaining')}: {subscription.trial_days_remaining}
                </p>
              </div>
            )}

            {usage && (
              <div className="pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-600">
                  {t('billing.billingPeriod')}:{' '}
                  <span className="font-medium">{formatBillingPeriod(usage.billing_period)}</span>
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Usage Meters — improved spacing, handles limit=0 in UsageMeter */}
      {usage && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-testid="usage-meters">
          <Card padding="lg" data-testid="invoice-usage-card">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              {t('billing.invoiceUsage')}
            </h3>
            <UsageMeter
              label={t('billing.invoicesSent')}
              used={usage.invoice_count}
              limit={usage.invoice_limit}
              exceeded={usage.invoice_limit_exceeded}
            />
          </Card>

          <Card padding="lg" data-testid="ai-usage-card">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              {t('billing.aiUsage')}
            </h3>
            <UsageMeter
              label={t('billing.aiCalls')}
              used={usage.ai_request_count}
              limit={usage.ai_limit}
              exceeded={usage.ai_limit_exceeded}
            />
          </Card>
        </div>
      )}

      {/* Rate Limit Info */}
      {subscription && (
        <Card padding="md" className="bg-slate-50">
          <div>
            <p className="text-sm font-medium text-slate-900">
              {t('billing.rateLimit')}
            </p>
            <p className="text-xs text-slate-600 mt-1">
              {t('billing.rateLimitDesc')}
            </p>
          </div>
        </Card>
      )}

      {/* Upgrade CTA */}
      <Card padding="md" className="bg-emerald-50 border border-emerald-200">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold text-slate-900 mb-1 break-words">
              {t('billing.upgradeTitle')}
            </h3>
            <p className="text-sm text-slate-600 break-words">
              {t('billing.upgradeDesc')}
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowPlanChangeModal(true)}
            className="sm:flex-shrink-0 whitespace-nowrap"
            data-testid="view-plans-button"
          >
            {t('billing.viewPlans')}
          </Button>
        </div>
      </Card>

      {/* Plan Change Confirmation Modal */}
      <Modal
        isOpen={showPlanChangeModal}
        onClose={() => setShowPlanChangeModal(false)}
        title={t('billing.changePlan')}
        size="md"
      >
        <div className="space-y-4" dir={direction}>
          <p className="text-sm text-slate-600">
            {t('billing.changePlanDesc')}
          </p>
          <div className="flex gap-3 justify-end">
            <Button
              variant="secondary"
              onClick={() => setShowPlanChangeModal(false)}
              data-testid="cancel-plan-change"
            >
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setShowPlanChangeModal(false);
                navigate('/plans');
              }}
              data-testid="confirm-plan-change"
            >
              {t('billing.continue')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
