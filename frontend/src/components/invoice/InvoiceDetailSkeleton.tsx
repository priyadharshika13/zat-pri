import React from 'react';
import { Card } from '../common/Card';
import { Skeleton } from '../common/Skeleton';

export const InvoiceDetailSkeleton: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton height="h-8" width="w-48" />
          <Skeleton height="h-4" width="w-32" />
        </div>
        <Skeleton height="h-10" width="w-20" />
      </div>

      {/* Tabs */}
      <Card padding="none" className="overflow-hidden">
        <div className="flex border-b border-slate-200">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="px-4 py-3">
              <Skeleton height="h-4" width="w-16" />
            </div>
          ))}
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton height="h-3" width="w-24" />
                <Skeleton height="h-4" width="w-full" />
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
};

