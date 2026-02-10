import React from 'react';
import { useLanguage } from '../../context/LanguageContext';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const paddingStyles: Record<NonNullable<CardProps['padding']>, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  padding = 'md',
}) => {
  const { direction } = useLanguage();

  return (
    <div
      className={`
        bg-white rounded-lg shadow-sm border border-slate-200
        ${paddingStyles[padding]}
        ${className}
      `}
      dir={direction}
    >
      {children}
    </div>
  );
};

