import React from 'react';
import { Button } from './Button';
import { useLanguage } from '../../context/LanguageContext';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  const { direction } = useLanguage();

  const defaultIcon = (
    <svg
      className="w-16 h-16 text-slate-400"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );

  return (
    <div className={`text-center py-12 ${className}`} dir={direction}>
      <div className="flex justify-center mb-4">{icon || defaultIcon}</div>
      <h3 className="text-lg font-semibold text-slate-900 mb-2">{title}</h3>
      <p className="text-slate-600 mb-6 max-w-md mx-auto">{description}</p>
      {actionLabel && onAction && (
        <Button variant="primary" onClick={onAction} data-testid="empty-state-action">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};

