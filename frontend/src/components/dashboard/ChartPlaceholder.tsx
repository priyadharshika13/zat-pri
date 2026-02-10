import React from 'react';
import { Card } from '../common/Card';
import { useLanguage } from '../../context/LanguageContext';

interface ChartPlaceholderProps {
  title: string;
  height?: number;
  className?: string;
}

export const ChartPlaceholder: React.FC<ChartPlaceholderProps> = ({
  title,
  height = 300,
  className = '',
}) => {
  const { direction } = useLanguage();

  return (
    <Card className={className} padding="md">
      <div dir={direction}>
        <h3 className="text-lg font-semibold text-slate-900 mb-4">{title}</h3>
        <div
          className="w-full bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-center"
          style={{ height: `${height}px` }}
        >
          <div className="text-center">
            <svg
              className="w-16 h-16 mx-auto text-slate-400 mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <p className="text-sm text-slate-500">
              {direction === 'rtl' ? 'سيتم إضافة الرسم البياني قريباً' : 'Chart will be added soon'}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
};

