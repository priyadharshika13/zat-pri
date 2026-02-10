import React, { useState, useEffect } from 'react';
import { Card } from '../common/Card';
import { useLanguage } from '../../context/LanguageContext';
import { Loader } from '../common/Loader';

interface SystemHealthResponse {
  environment: string;
  zatca: {
    status: string;
    environment: string;
    last_checked: string;
    error_message?: string;
  };
  ai: {
    status: string;
    provider: string;
    error_message?: string;
  };
  system: {
    uptime_seconds: number;
    version: string;
    environment: string;
  };
  timestamp: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const SystemStatusCard: React.FC = () => {
  const { t: _t, direction } = useLanguage();
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${API_BASE_URL}/api/v1/system/health`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        setHealth(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch health status');
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string): string => {
    switch (status.toUpperCase()) {
      case 'CONNECTED':
      case 'ENABLED':
        return 'bg-emerald-500';
      case 'DISCONNECTED':
      case 'DISABLED':
        return 'bg-red-500';
      case 'ERROR':
        return 'bg-amber-500';
      default:
        return 'bg-slate-400';
    }
  };

  const getStatusLabel = (status: string): string => {
    switch (status.toUpperCase()) {
      case 'CONNECTED':
        return direction === 'rtl' ? 'متصل' : 'Connected';
      case 'DISCONNECTED':
        return direction === 'rtl' ? 'غير متصل' : 'Disconnected';
      case 'ENABLED':
        return direction === 'rtl' ? 'مفعل' : 'Enabled';
      case 'DISABLED':
        return direction === 'rtl' ? 'معطل' : 'Disabled';
      case 'ERROR':
        return direction === 'rtl' ? 'خطأ' : 'Error';
      default:
        return status;
    }
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
      return direction === 'rtl' 
        ? `${days} يوم ${hours} ساعة`
        : `${days}d ${hours}h`;
    }
    if (hours > 0) {
      return direction === 'rtl'
        ? `${hours} ساعة ${minutes} دقيقة`
        : `${hours}h ${minutes}m`;
    }
    return direction === 'rtl'
      ? `${minutes} دقيقة`
      : `${minutes}m`;
  };

  const formatLastChecked = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
      
      if (diffSeconds < 60) {
        return direction === 'rtl' ? 'الآن' : 'Just now';
      }
      if (diffSeconds < 3600) {
        const minutes = Math.floor(diffSeconds / 60);
        return direction === 'rtl' 
          ? `منذ ${minutes} دقيقة`
          : `${minutes}m ago`;
      }
      
      return date.toLocaleTimeString(direction === 'rtl' ? 'ar-SA' : 'en-US', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '-';
    }
  };

  if (loading && !health) {
    return (
      <Card padding="md">
        <div className="flex items-center justify-center py-8">
          <Loader />
        </div>
      </Card>
    );
  }

  if (error && !health) {
    return (
      <Card padding="md">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">
          {direction === 'rtl' ? 'حالة النظام' : 'System Status'}
        </h3>
        <div className="text-sm text-red-600">
          {direction === 'rtl' ? 'فشل تحميل الحالة' : `Failed to load: ${error}`}
        </div>
      </Card>
    );
  }

  if (!health) {
    return null;
  }

  return (
    <Card padding="md">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">
        {direction === 'rtl' ? 'حالة النظام' : 'System Status'}
      </h3>
      
      <div className="space-y-4">
        {/* ZATCA Status */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-slate-700">
                {direction === 'rtl' ? 'ZATCA API' : 'ZATCA API'}
              </span>
              <span
                className={`w-2 h-2 rounded-full ${getStatusColor(health.zatca.status)}`}
                title={getStatusLabel(health.zatca.status)}
              />
            </div>
            <div className="text-xs text-slate-500">
              {health.zatca.environment}
              {health.zatca.error_message && (
                <span className="block text-red-600 mt-1">
                  {health.zatca.error_message}
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {direction === 'rtl' ? 'آخر فحص:' : 'Last checked:'} {formatLastChecked(health.zatca.last_checked)}
            </div>
          </div>
        </div>

        {/* AI Status */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-slate-700">
                {direction === 'rtl' ? 'خدمة الذكاء الاصطناعي' : 'AI Service'}
              </span>
              <span
                className={`w-2 h-2 rounded-full ${getStatusColor(health.ai.status)}`}
                title={getStatusLabel(health.ai.status)}
              />
            </div>
            <div className="text-xs text-slate-500">
              {health.ai.provider}
              {health.ai.error_message && (
                <span className="block text-red-600 mt-1">
                  {health.ai.error_message}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* System Info */}
        <div className="pt-3 border-t border-slate-200">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>{direction === 'rtl' ? 'وقت التشغيل:' : 'Uptime:'}</span>
            <span className="font-medium">{formatUptime(health.system.uptime_seconds)}</span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-500 mt-1">
            <span>{direction === 'rtl' ? 'الإصدار:' : 'Version:'}</span>
            <span className="font-medium">{health.system.version}</span>
          </div>
        </div>
      </div>
    </Card>
  );
};

