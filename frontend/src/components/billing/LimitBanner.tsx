import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../common/Button';
import { useLanguage } from '../../context/LanguageContext';

interface LimitBannerProps {
  invoiceLimitExceeded?: boolean;
  aiLimitExceeded?: boolean;
}

export const LimitBanner: React.FC<LimitBannerProps> = ({
  invoiceLimitExceeded = false,
  aiLimitExceeded = false,
}) => {
  const { direction } = useLanguage();
  const navigate = useNavigate();
  const isRTL = direction === 'rtl';

  if (!invoiceLimitExceeded && !aiLimitExceeded) {
    return null;
  }

  const getMessage = (): string => {
    if (invoiceLimitExceeded && aiLimitExceeded) {
      return direction === 'rtl'
        ? 'لقد وصلت إلى حد خطتك في الفواتير و AI. قم بالترقية للمتابعة.'
        : "You've reached your plan limits for invoices and AI. Upgrade to continue.";
    }
    if (invoiceLimitExceeded) {
      return direction === 'rtl'
        ? 'لقد وصلت إلى حد الفواتير في خطتك. قم بالترقية للمتابعة.'
        : "You've reached your invoice limit. Upgrade to continue.";
    }
    return direction === 'rtl'
      ? 'لقد وصلت إلى حد AI في خطتك. قم بالترقية للمتابعة.'
      : "You've reached your AI limit. Upgrade to continue.";
  };

  return (
    <div
      className={`mb-6 p-4 rounded-lg border-2 ${
        isRTL ? 'border-amber-500' : 'border-amber-500'
      } bg-amber-50 flex items-center justify-between gap-4`}
      dir={direction}
    >
      <div className="flex items-start gap-3 flex-1">
        <svg
          className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <p className="text-sm font-medium text-amber-900 flex-1 break-words">{getMessage()}</p>
      </div>
      <Button
        variant="primary"
        size="sm"
        onClick={() => navigate('/plans')}
        className="flex-shrink-0 whitespace-nowrap"
      >
        {direction === 'rtl' ? 'عرض الخطط' : 'View Plans'}
      </Button>
    </div>
  );
};

