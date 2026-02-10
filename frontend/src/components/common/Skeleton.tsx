import React from 'react';

interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '', width, height }) => {
  return (
    <div
      className={`bg-slate-200 rounded animate-pulse ${className}`}
      style={{ width, height }}
    />
  );
};

export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={`p-6 border border-slate-200 rounded-lg bg-white ${className}`}>
      <div className="space-y-3">
        <Skeleton height="h-5" width="w-3/4" />
        <Skeleton height="h-4" width="w-1/2" />
        <Skeleton height="h-4" width="w-2/3" />
      </div>
    </div>
  );
};

export const SkeletonTable: React.FC<{ rows?: number; cols?: number }> = ({ rows = 5, cols = 5 }) => {
  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={`header-${i}`} height="h-4" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={`row-${rowIdx}`} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((_, colIdx) => (
            <Skeleton key={`cell-${rowIdx}-${colIdx}`} height="h-8" />
          ))}
        </div>
      ))}
    </div>
  );
};

