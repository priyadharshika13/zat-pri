import React from 'react';
import { Card } from '../common/Card';
import { Skeleton } from '../common/Skeleton';

export const InvoiceListSkeleton: React.FC = () => {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-4 border-b border-slate-200">
        <Skeleton height="h-5" width="w-48" />
      </div>
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <Skeleton height="h-4" width="w-32" />
            <Skeleton height="h-4" width="w-20" />
            <Skeleton height="h-6" width="w-16" />
            <Skeleton height="h-4" width="w-24" />
            <Skeleton height="h-4" width="w-20" />
          </div>
        ))}
      </div>
    </Card>
  );
};

