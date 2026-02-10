import React, { useState, useEffect } from 'react';
import { Card } from '../common/Card';
import { useLanguage } from '../../context/LanguageContext';
import { Loader } from '../common/Loader';
import { apiGet } from '../../lib/api';
import { isAuthed } from '../../lib/auth';

interface UsageData {
  invoice_count: number;
  invoice_limit: number;
  ai_request_count: number;
  ai_limit: number;
  billing_period: string;
}

export const ApiUsageCard: React.FC = () => {
  const { t: _t, direction } = useLanguage();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsage = async () => {
      // Check if user is authenticated
      if (!isAuthed()) {
        setError(
          direction === 'rtl'
            ? 'يرجى تسجيل الدخول لعرض بيانات الاستخدام'
            : 'Please login to view usage data'
        );
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        const data = await apiGet<UsageData>('/api/v1/plans/usage');
        
        setUsage({
          invoice_count: data.invoice_count,
          invoice_limit: data.invoice_limit,
          ai_request_count: data.ai_request_count,
          ai_limit: data.ai_limit,
          billing_period: data.billing_period,
        });
      } catch (err: unknown) {
        const apiError = err as { message?: string; status?: number; detail?: string };
        
        if (apiError.status === 401) {
          setError(
            direction === 'rtl'
              ? 'يرجى تسجيل الدخول لعرض بيانات الاستخدام'
              : 'Please login to view usage data'
          );
        } else {
          setError(
            apiError.detail ||
            apiError.message ||
            (direction === 'rtl' ? 'فشل تحميل البيانات' : 'Failed to load usage data')
          );
        }
      } finally {
        setLoading(false);
      }
    };

    fetchUsage();
  }, [direction]);

  if (loading) {
    return (
      <Card padding="md">
        <div className="flex items-center justify-center py-8">
          <Loader size="sm" />
        </div>
      </Card>
    );
  }

  if (error || !usage) {
    return (
      <Card padding="md">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">
          {direction === 'rtl' ? 'استخدام API' : 'API Usage'}
        </h3>
        <div className="text-sm text-red-600">
          {direction === 'rtl' ? 'فشل تحميل البيانات' : error || 'No data available'}
        </div>
      </Card>
    );
  }

  const invoicePercentage = usage.invoice_limit > 0 
    ? (usage.invoice_count / usage.invoice_limit) * 100 
    : 0;
  const aiPercentage = usage.ai_limit > 0 
    ? (usage.ai_request_count / usage.ai_limit) * 100 
    : 0;

  return (
    <Card padding="md">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">
        {direction === 'rtl' ? 'استخدام API' : 'API Usage'}
      </h3>
      
      <div className="space-y-4">
        {/* ZATCA Submissions */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">
              {direction === 'rtl' ? 'إرسالات ZATCA' : 'ZATCA Submissions'}
            </span>
            <span className="text-sm font-semibold text-slate-900">
              {usage.invoice_count.toLocaleString()} / {usage.invoice_limit > 0 ? usage.invoice_limit.toLocaleString() : '∞'}
            </span>
          </div>
          {usage.invoice_limit > 0 && (
            <>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden mb-1">
                <div
                  className={`h-full transition-all duration-300 ${
                    invoicePercentage > 95
                      ? 'bg-red-600'
                      : invoicePercentage > 80
                      ? 'bg-amber-500'
                      : 'bg-emerald-600'
                  }`}
                  style={{ width: `${Math.min(invoicePercentage, 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-500">
                {direction === 'rtl' ? 'هذا الشهر' : 'This month'} ({usage.billing_period})
              </p>
            </>
          )}
        </div>

        {/* AI Calls */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">
              {direction === 'rtl' ? 'مكالمات الذكاء الاصطناعي' : 'AI Calls'}
            </span>
            <span className="text-sm font-semibold text-slate-900">
              {usage.ai_request_count.toLocaleString()} / {usage.ai_limit > 0 ? usage.ai_limit.toLocaleString() : '∞'}
            </span>
          </div>
          {usage.ai_limit > 0 && (
            <>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden mb-1">
                <div
                  className={`h-full transition-all duration-300 ${
                    aiPercentage > 95
                      ? 'bg-red-600'
                      : aiPercentage > 80
                      ? 'bg-amber-500'
                      : 'bg-emerald-600'
                  }`}
                  style={{ width: `${Math.min(aiPercentage, 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-500">
                {direction === 'rtl' ? 'هذا الشهر' : 'This month'} ({usage.billing_period})
              </p>
            </>
          )}
        </div>
      </div>
    </Card>
  );
};

