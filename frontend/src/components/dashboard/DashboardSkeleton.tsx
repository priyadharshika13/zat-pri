import React from 'react';
import { Skeleton } from '../common/Skeleton';
import { Card } from '../common/Card';

export const DashboardSkeleton: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton height="h-8" width="w-48" />
        <Skeleton height="h-4" width="w-64" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} padding="lg">
            <div className="space-y-3">
              <Skeleton height="h-4" width="w-24" />
              <Skeleton height="h-8" width="w-32" />
              <Skeleton height="h-3" width="w-16" />
            </div>
          </Card>
        ))}
      </div>

      {/* System Status and API Usage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card padding="lg">
          <div className="space-y-3">
            <Skeleton height="h-5" width="w-32" />
            <Skeleton height="h-4" width="w-full" />
            <Skeleton height="h-4" width="w-3/4" />
          </div>
        </Card>
        <Card padding="lg">
          <div className="space-y-3">
            <Skeleton height="h-5" width="w-32" />
            <Skeleton height="h-4" width="w-full" />
            <Skeleton height="h-4" width="w-3/4" />
          </div>
        </Card>
      </div>

      {/* Chart and Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card padding="lg">
            <Skeleton height="h-64" width="w-full" />
          </Card>
        </div>
        <Card padding="lg">
          <div className="space-y-4">
            <Skeleton height="h-5" width="w-32" />
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-2 p-3 border border-slate-200 rounded">
                <Skeleton height="h-4" width="w-full" />
                <Skeleton height="h-3" width="w-3/4" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

