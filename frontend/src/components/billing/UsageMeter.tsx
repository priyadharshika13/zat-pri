import React from 'react';
import { useLanguage } from '../../context/LanguageContext';

interface UsageMeterProps {
  label: string;
  used: number;
  limit: number; // 0 = unlimited
  exceeded?: boolean;
  className?: string;
}

export const UsageMeter: React.FC<UsageMeterProps> = ({
  label,
  used,
  limit,
  exceeded = false,
  className = '',
}) => {
  const { direction } = useLanguage();
  const _isRTL = direction === 'rtl';

  const isUnlimited = limit === 0;
  const percentage = isUnlimited ? 0 : Math.min((used / limit) * 100, 100);
  const isWarning = percentage > 80 && !exceeded;
  const isDanger = exceeded || percentage >= 100;

  const formatValue = (value: number): string => {
    return value.toLocaleString();
  };

  const formatLimit = (): string => {
    if (isUnlimited) {
      return direction === 'rtl' ? 'غير محدود' : 'Unlimited';
    }
    return formatValue(limit);
  };

  return (
    <div className={`space-y-2 ${className}`} dir={direction}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className="text-sm font-semibold text-slate-900">
          {formatValue(used)} / {formatLimit()}
        </span>
      </div>

      {!isUnlimited && (
        <>
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
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">
              {percentage.toFixed(1)}% {direction === 'rtl' ? 'مستخدم' : 'used'}
            </span>
            {exceeded && (
              <span className="text-red-600 font-medium">
                {direction === 'rtl' ? 'تم تجاوز الحد' : 'Limit exceeded'}
              </span>
            )}
          </div>
        </>
      )}

      {isUnlimited && (
        <div className="text-xs text-slate-500">
          {direction === 'rtl' ? 'لا يوجد حد' : 'No limit'}
        </div>
      )}
    </div>
  );
};

