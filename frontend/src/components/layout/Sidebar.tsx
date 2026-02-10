import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';

interface MenuItem {
  id: string;
  labelKey: string;
  icon: React.ReactNode;
}

interface SidebarProps {
  activeMenu?: string;
  onMenuClick?: (menuId: string) => void;
}

const menuItems: MenuItem[] = [
  {
    id: 'dashboard',
    labelKey: 'nav.dashboard',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    id: 'create-invoice',
    labelKey: 'nav.createInvoice',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
      </svg>
    ),
  },
  {
    id: 'invoices',
    labelKey: 'nav.invoices',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    id: 'ai-insights',
    labelKey: 'nav.aiInsights',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: 'api-playground',
    labelKey: 'nav.apiPlayground',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  },
  {
    id: 'billing',
    labelKey: 'nav.billing',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
      </svg>
    ),
  },
  {
    id: 'webhooks',
    labelKey: 'nav.webhooks',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'reports',
    labelKey: 'nav.reports',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    id: 'api-keys',
    labelKey: 'nav.apiKeys',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
      </svg>
    ),
  },
  {
    id: 'zatca-setup',
    labelKey: 'nav.zatcaSetup',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeMenu = 'dashboard',
  onMenuClick,
}) => {
  const { language, direction, t } = useLanguage();
  const navigate = useNavigate();
  const isRTL = direction === 'rtl';

  const handleMenuClick = (menuId: string) => {
    if (menuId === 'billing') {
      navigate('/billing');
    } else if (menuId === 'webhooks') {
      navigate('/webhooks');
    } else if (menuId === 'reports') {
      navigate('/reports');
    } else if (menuId === 'api-keys') {
      navigate('/api-keys');
    } else if (menuId === 'dashboard') {
      navigate('/dashboard');
    } else if (menuId === 'create-invoice') {
      navigate('/invoices/create');
    } else if (menuId === 'invoices') {
      navigate('/invoices');
    } else if (menuId === 'ai-insights') {
      navigate('/ai-insights');
    } else if (menuId === 'api-playground') {
      navigate('/api-playground');
    } else if (menuId === 'zatca-setup') {
      navigate('/zatca-setup');
    }
    onMenuClick?.(menuId);
  };

  return (
    <aside
      className={`
        fixed top-0 h-screen w-64 bg-white border-e border-slate-200
        flex flex-col z-40
        ${isRTL ? 'right-0' : 'left-0'}
      `}
      dir={direction}
    >
      {/* Logo Section */}
      <div className="h-16 flex items-center ps-6 pe-6 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">Z</span>
          </div>
          <span className="font-bold text-slate-900 text-lg">
            {language === 'ar' ? 'زاتكا' : 'ZATCA'}
          </span>
        </div>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 ps-3 pe-3">
          {menuItems.map((item) => {
            const isActive = activeMenu === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => handleMenuClick(item.id)}
                  className={`
                    w-full flex items-center gap-3 ps-3 pe-3 py-2.5 rounded-lg
                    text-sm font-medium transition-colors duration-200
                    ${
                      isActive
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'text-slate-700 hover:bg-slate-50'
                    }
                  `}
                >
                  <span className={isActive ? 'text-emerald-600' : 'text-slate-500'}>
                    {item.icon}
                  </span>
                  <span className="text-start flex-1">{t(item.labelKey)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};

