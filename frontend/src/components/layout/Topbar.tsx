import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { getUserData, clearApiKey } from '../../lib/auth';

interface TopbarProps {
  environment?: 'sandbox' | 'production';
  apiUsage?: {
    used: number;
    limit: number;
  };
}

export const Topbar: React.FC<TopbarProps> = ({
  environment = 'sandbox',
  apiUsage = { used: 0, limit: 1000 },
}) => {
  const { language, direction, toggleLanguage, t } = useLanguage();
  const navigate = useNavigate();
  const isRTL = direction === 'rtl';
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const userData = getUserData();

  const usagePercentage = (apiUsage.used / apiUsage.limit) * 100;

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserMenu]);

  const handleLogout = () => {
    clearApiKey();
    navigate('/login');
  };

  return (
    <header
      className={`
        fixed top-0 h-16 bg-white border-b border-slate-200 z-30
        flex items-center justify-between ps-4 pe-4
        ${isRTL ? 'right-64 left-0' : 'left-64 right-0'}
      `}
      dir={direction}
    >
      <div className="flex-1" />

      {/* Right side (LTR) or Left side (RTL) */}
      <div className="flex items-center gap-4">
        {/* API Usage Indicator */}
        <div className="hidden md:flex items-center gap-2">
          <span className="text-sm text-slate-600">{t('topbar.apiUsage')}:</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  usagePercentage > 90
                    ? 'bg-red-600'
                    : usagePercentage > 70
                    ? 'bg-amber-500'
                    : 'bg-emerald-600'
                }`}
                style={{ width: `${Math.min(usagePercentage, 100)}%` }}
              />
            </div>
            <span className="text-sm text-slate-700 font-medium">
              {apiUsage.used} / {apiUsage.limit}
            </span>
          </div>
        </div>

        {/* Environment Badge */}
        <Badge
          variant={environment === 'production' ? 'success' : 'warning'}
        >
          {environment === 'production'
            ? t('topbar.environment.production')
            : t('topbar.environment.sandbox')}
        </Badge>

        {/* Language Toggle */}
        <Button
          variant="secondary"
          size="sm"
          onClick={toggleLanguage}
          className="min-w-[60px]"
        >
          {language === 'en' ? 'AR' : 'EN'}
        </Button>

        {/* User Menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-medium">
              {userData?.company_name?.[0]?.toUpperCase() || userData?.email?.[0]?.toUpperCase() || 'K'}
            </div>
            <span className="hidden md:block text-sm text-slate-700 font-medium">
              {t('topbar.apiKeySession')}
            </span>
            <svg
              className={`w-4 h-4 text-slate-600 transition-transform ${
                showUserMenu ? 'rotate-180' : ''
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {showUserMenu && (
            <div
              className={`absolute ${
                isRTL ? 'left-0' : 'right-0'
              } mt-2 w-56 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50`}
              dir={direction}
            >
              <div className="px-4 py-2 border-b border-slate-200">
                <p className="text-xs text-slate-500 mb-1">
                  {t('topbar.apiKeySession')}
                </p>
                {userData?.api_key_masked && (
                  <p className="text-sm font-mono text-slate-900">
                    {userData.api_key_masked}
                  </p>
                )}
                {userData?.company_name && (
                  <p className="text-xs text-slate-600 mt-1">{userData.company_name}</p>
                )}
                {userData?.email && (
                  <p className="text-xs text-slate-500 mt-1">{userData.email}</p>
                )}
              </div>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
                {t('topbar.logout')}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

