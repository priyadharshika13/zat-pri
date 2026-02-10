import React from 'react';
import { Card } from '../common/Card';
import { useLanguage } from '../../context/LanguageContext';

export const BillingSkeleton: React.FC = () => {
  const { direction } = useLanguage();

  return (
    <div className="space-y-8" dir={direction}>
      {/* Header skeleton */}
      <div>
        <div className="h-8 w-64 bg-slate-200 rounded animate-pulse mb-2" />
        <div className="h-4 w-96 max-w-full bg-slate-100 rounded animate-pulse" />
      </div>

      {/* Plan card skeleton */}
      <Card padding="lg">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-5 w-32 bg-slate-200 rounded animate-pulse" />
            <div className="h-4 w-48 bg-slate-100 rounded animate-pulse" />
          </div>
          <div className="h-6 w-16 bg-slate-200 rounded-full animate-pulse" />
        </div>
        <div className="mt-4 pt-4 border-t border-slate-200">
          <div className="h-4 w-40 bg-slate-100 rounded animate-pulse" />
        </div>
      </Card>

      {/* Usage meters skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card padding="lg">
          <div className="h-5 w-36 bg-slate-200 rounded animate-pulse mb-4" />
          <div className="h-4 w-full bg-slate-100 rounded animate-pulse mb-2" />
          <div className="h-2 w-full bg-slate-100 rounded animate-pulse" />
        </Card>
        <Card padding="lg">
          <div className="h-5 w-28 bg-slate-200 rounded animate-pulse mb-4" />
          <div className="h-4 w-full bg-slate-100 rounded animate-pulse mb-2" />
          <div className="h-2 w-full bg-slate-100 rounded animate-pulse" />
        </Card>
      </div>
    </div>
  );
};

