import React from 'react';
import { useLanguage } from '../../context/LanguageContext';

interface EnvironmentBannerProps {
  environment: 'SANDBOX' | 'PRODUCTION';
}

export const EnvironmentBanner: React.FC<EnvironmentBannerProps> = ({ environment }) => {
  const { direction } = useLanguage();
  const isSandbox = environment === 'SANDBOX';

  return (
    <div
      className={`
        fixed top-16 left-0 right-0 z-20
        ${isSandbox ? 'bg-amber-500' : 'bg-red-600'}
        text-white px-4 py-2
        ${direction === 'rtl' ? 'text-right' : 'text-left'}
      `}
      dir={direction}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-2">
        <svg
          className="w-5 h-5 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          {isSandbox ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          )}
        </svg>
        <div className="flex-1 text-center">
          {isSandbox ? (
            <>
              <span className="font-semibold">
                {direction === 'rtl' ? 'وضع التجربة' : 'Sandbox Mode'}
              </span>
              <span className="mx-2">–</span>
              <span>
                {direction === 'rtl'
                  ? 'الفواتير غير صالحة قانونياً'
                  : 'Invoices are NOT legally valid'}
              </span>
            </>
          ) : (
            <>
              <span className="font-semibold">
                {direction === 'rtl' ? 'وضع الإنتاج' : 'Production Mode'}
              </span>
              <span className="mx-2">–</span>
              <span>
                {direction === 'rtl'
                  ? 'إرسالات ZATCA مباشرة'
                  : 'ZATCA submissions are LIVE'}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

