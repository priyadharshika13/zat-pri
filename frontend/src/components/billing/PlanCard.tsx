import React from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { useLanguage } from '../../context/LanguageContext';
import { Plan } from '../../types/plan';

interface PlanCardProps {
  plan: Plan;
  isRecommended?: boolean;
  isCurrentPlan?: boolean;
  onSelect?: () => void;
  ctaText?: string;
  showUpgrade?: boolean;
}

export const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  isRecommended = false,
  isCurrentPlan = false,
  onSelect,
  ctaText,
  showUpgrade = false,
}) => {
  const { t: _t, direction } = useLanguage();
  const isRTL = direction === 'rtl';

  const formatLimit = (limit: number): string => {
    if (limit === 0) {
      return direction === 'rtl' ? 'غير محدود' : 'Unlimited';
    }
    return limit.toLocaleString();
  };

  const getFeatures = (): string[] => {
    if (!plan.features) {
      return [];
    }
    
    // Extract feature list from features object
    const features: string[] = [];
    for (const [key, value] of Object.entries(plan.features)) {
      if (typeof value === 'string') {
        features.push(value);
      } else if (typeof value === 'boolean' && value) {
        features.push(key);
      }
    }
    return features;
  };

  const features = getFeatures();

  return (
    <Card
      className={`relative ${
        isRecommended
          ? 'border-2 border-emerald-500 shadow-lg'
          : isCurrentPlan
          ? 'border-2 border-slate-300'
          : ''
      }`}
      padding="lg"
    >
      {isRecommended && (
        <div
          className={`absolute top-0 ${
            isRTL ? 'left-0 rounded-tl-lg rounded-br-lg' : 'right-0 rounded-tr-lg rounded-bl-lg'
          } bg-emerald-600 text-white px-3 py-1 text-xs font-semibold`}
        >
          {direction === 'rtl' ? 'موصى به' : 'Recommended'}
        </div>
      )}

      {isCurrentPlan && (
        <div
          className={`absolute top-0 ${
            isRTL ? 'left-0 rounded-tl-lg rounded-br-lg' : 'right-0 rounded-tr-lg rounded-bl-lg'
          } bg-slate-600 text-white px-3 py-1 text-xs font-semibold`}
        >
          {direction === 'rtl' ? 'الخطة الحالية' : 'Current Plan'}
        </div>
      )}

      <div className="space-y-4">
        {/* Plan Name */}
        <div>
          <h3 className="text-2xl font-bold text-slate-900">{plan.name}</h3>
        </div>

        {/* Limits */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">
              {direction === 'rtl' ? 'فواتير شهرياً' : 'Invoices/month'}
            </span>
            <span className="text-sm font-semibold text-slate-900">
              {formatLimit(plan.monthly_invoice_limit)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">
              {direction === 'rtl' ? 'مكالمات AI شهرياً' : 'AI calls/month'}
            </span>
            <span className="text-sm font-semibold text-slate-900">
              {formatLimit(plan.monthly_ai_limit)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">
              {direction === 'rtl' ? 'معدل الطلبات/دقيقة' : 'Rate limit/min'}
            </span>
            <span className="text-sm font-semibold text-slate-900">
              {plan.rate_limit_per_minute}
            </span>
          </div>
        </div>

        {/* Features */}
        {features.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-900 mb-2">
              {direction === 'rtl' ? 'المميزات' : 'Features'}
            </h4>
            <ul className={`space-y-1 ${isRTL ? 'text-right' : 'text-left'}`}>
              {features.map((feature, index) => (
                <li key={index} className="text-sm text-slate-600 flex items-start gap-2">
                  <svg
                    className={`w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0 ${isRTL ? 'order-2' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="break-words flex-1">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* CTA Button */}
        {onSelect && (
          <Button
            variant={isRecommended ? 'primary' : 'secondary'}
            className="w-full whitespace-nowrap"
            onClick={onSelect}
            disabled={isCurrentPlan}
          >
            {isCurrentPlan
              ? direction === 'rtl'
                ? 'الخطة الحالية'
                : 'Current Plan'
              : ctaText ||
                (showUpgrade
                  ? direction === 'rtl'
                    ? 'ترقية'
                    : 'Upgrade'
                  : direction === 'rtl'
                  ? 'احصل على مفتاح API'
                  : 'Get API Key')}
          </Button>
        )}
      </div>
    </Card>
  );
};

