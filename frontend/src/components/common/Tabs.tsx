import React from 'react';
import { useLanguage } from '../../context/LanguageContext';

interface TabsProps {
  tabs: Array<{ id: string; label: string }>;
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onTabChange }) => {
  const { direction } = useLanguage();
  const _isRTL = direction === 'rtl';

  return (
    <div className="border-b border-slate-200" dir={direction}>
      <nav className="flex -mb-px" aria-label="Tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              px-4 py-3 text-sm font-medium border-b-2 transition-colors
              ${
                activeTab === tab.id
                  ? 'border-emerald-500 text-emerald-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }
            `}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
};

