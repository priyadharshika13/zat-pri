import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { EnvironmentBanner } from '../system/EnvironmentBanner';
import { useLanguage } from '../../context/LanguageContext';

interface PageWrapperProps {
  children: React.ReactNode;
  activeMenu?: string;
  onMenuClick?: (menuId: string) => void;
  environment?: 'sandbox' | 'production';
  apiUsage?: {
    used: number;
    limit: number;
  };
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const PageWrapper: React.FC<PageWrapperProps> = ({
  children,
  activeMenu,
  onMenuClick,
  environment: propEnvironment,
  apiUsage,
}) => {
  const { direction } = useLanguage();
  const isRTL = direction === 'rtl';
  const [environment, setEnvironment] = useState<'SANDBOX' | 'PRODUCTION'>('SANDBOX');

  // Fetch environment from health endpoint
  useEffect(() => {
    const fetchEnvironment = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/system/health`);
        if (response.ok) {
          const data = await response.json();
          setEnvironment(data.environment as 'SANDBOX' | 'PRODUCTION');
        } else if (propEnvironment) {
          // Fallback to prop if health check fails
          setEnvironment(propEnvironment.toUpperCase() as 'SANDBOX' | 'PRODUCTION');
        }
      } catch {
        // Fallback to prop if fetch fails
        if (propEnvironment) {
          setEnvironment(propEnvironment.toUpperCase() as 'SANDBOX' | 'PRODUCTION');
        }
      }
    };

    fetchEnvironment();
  }, [propEnvironment]);

  // Convert environment for Topbar (lowercase)
  const topbarEnvironment = environment.toLowerCase() as 'sandbox' | 'production';

  return (
    <div className="min-h-screen bg-slate-50" dir={direction}>
      <Sidebar activeMenu={activeMenu} onMenuClick={onMenuClick} />
      <Topbar environment={topbarEnvironment} apiUsage={apiUsage} />
      <EnvironmentBanner environment={environment} />
      <main className={`pt-24 min-h-screen ${isRTL ? 'pe-64 ps-0' : 'ps-64 pe-0'}`}>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
};

