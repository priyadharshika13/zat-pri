import React from 'react';
import { Card } from '../common/Card';
import { useLanguage } from '../../context/LanguageContext';

interface UsageCardProps {
  title: string;
  used: number;
  limit: number;
  unit?: string;
  className?: string;
}

export const UsageCard: React.FC<UsageCardProps> = ({
  title,
  used,
  limit,
  unit = '',
  className = '',
}) => {
  const { direction } = useLanguage();
  const percentage = (used / limit) * 100;
  const isWarning = percentage > 80;
  const isDanger = percentage > 95;

  return (
    <Card className={className} padding="md">
      <div dir={direction}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-slate-700">{title}</h3>
          <span className="text-sm font-semibold text-slate-900">
            {used} / {limit} {unit}
          </span>
        </div>
        <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              isDanger
                ? 'bg-red-600'
                : isWarning
                ? 'bg-amber-500'
                : 'bg-emerald-600'
            }`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
        <p className="text-xs text-slate-500 mt-2">
          {percentage.toFixed(1)}% {direction === 'rtl' ? 'مستخدم' : 'used'}
        </p>
      </div>
    </Card>
  );
};

