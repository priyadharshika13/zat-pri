import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { useLanguage } from '../context/LanguageContext';

export const AiInsights: React.FC = () => {
  const { t, direction } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="space-y-6" dir={direction} data-testid="ai-insights-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          {direction === 'rtl' ? 'رؤى الذكاء الاصطناعي' : 'AI Insights'}
        </h1>
        <p className="text-slate-500 mt-1">
          {direction === 'rtl'
            ? 'استخدم الذكاء الاصطناعي لشرح أخطاء ZATCA والتنبؤ بالرفض.'
            : 'Use AI to explain ZATCA errors and predict rejection risk.'}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card padding="md" className="border border-slate-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-slate-900">
                {direction === 'rtl' ? 'شرح الخطأ' : 'Explain Error'}
              </h2>
              <p className="text-sm text-slate-600 mt-1">
                {direction === 'rtl'
                  ? 'عند رفض فاتورة، افتح تفاصيل الفاتورة واضغط "شرح الخطأ" للحصول على شرح بالعربية والإنجليزية واقتراحات للإصلاح.'
                  : 'When an invoice is rejected, open the invoice detail and click "Explain Error" for a human and AI explanation in English and Arabic, plus fix suggestions.'}
              </p>
              <Button
                variant="primary"
                size="sm"
                className="mt-3"
                onClick={() => navigate('/invoices')}
                data-testid="ai-insights-go-invoices"
              >
                {direction === 'rtl' ? 'عرض الفواتير' : 'View Invoices'}
              </Button>
            </div>
          </div>
        </Card>

        <Card padding="md" className="border border-slate-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-slate-900">
                {direction === 'rtl' ? 'التنبؤ بالرفض' : 'Predict Rejection'}
              </h2>
              <p className="text-sm text-slate-600 mt-1">
                {direction === 'rtl'
                  ? 'تحقق من احتمال رفض الفاتورة قبل الإرسال. استخدم ساحة اللعب API مع نقطة النهاية predict-rejection.'
                  : 'Check rejection risk before submitting. Use the API Playground with the predict-rejection endpoint.'}
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-3"
                onClick={() => navigate('/api-playground')}
                data-testid="ai-insights-go-playground"
              >
                {direction === 'rtl' ? 'ساحة اللعب API' : 'API Playground'}
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <Card padding="md" className="bg-slate-50 border border-slate-200">
        <h3 className="text-base font-semibold text-slate-900 mb-2">
          {direction === 'rtl' ? 'نقاط النهاية' : 'API Endpoints'}
        </h3>
        <ul className="text-sm text-slate-600 space-y-1 list-disc list-inside">
          <li><code className="bg-white px-1 rounded">POST /api/v1/errors/explain</code> — {direction === 'rtl' ? 'شرح رمز أو رسالة خطأ ZATCA' : 'Explain a ZATCA error code or message'}</li>
          <li><code className="bg-white px-1 rounded">POST /api/v1/ai/predict-rejection</code> — {direction === 'rtl' ? 'التنبؤ بمخاطر الرفض لحمولة فاتورة' : 'Predict rejection risk for an invoice payload'}</li>
        </ul>
      </Card>
    </div>
  );
};
