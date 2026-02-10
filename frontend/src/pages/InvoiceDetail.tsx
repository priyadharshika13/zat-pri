import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Tabs } from '../components/common/Tabs';
import { Modal } from '../components/common/Modal';
import { CodeBlock } from '../components/common/CodeBlock';
import { InvoiceStatusBadge } from '../components/invoice/InvoiceStatusBadge';
import { InvoiceDetailSkeleton } from '../components/invoice/InvoiceDetailSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { useLanguage } from '../context/LanguageContext';
import { getInvoice } from '../lib/invoiceApi';
import { explainError, predictRejection, ErrorExplanationResponse, RejectionPredictionResponse } from '../lib/aiApi';
import { InvoiceDetailResponse } from '../types/invoiceHistory';
import { LimitBanner } from '../components/billing/LimitBanner';
import { getUsage } from '../lib/billingApi';

export const InvoiceDetail: React.FC = () => {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const navigate = useNavigate();
  const { direction, t } = useLanguage();
  const [invoice, setInvoice] = useState<InvoiceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [usage, setUsage] = useState<{ invoice_limit_exceeded: boolean; ai_limit_exceeded: boolean } | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // AI modals
  const [showExplainModal, setShowExplainModal] = useState(false);
  const [showPredictModal, setShowPredictModal] = useState(false);
  const [explainResult, setExplainResult] = useState<ErrorExplanationResponse | null>(null);
  const [predictResult, setPredictResult] = useState<RejectionPredictionResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInvoice = async () => {
      if (!invoiceId) {
        setError(t('invoiceDetail.error'));
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await getInvoice(parseInt(invoiceId, 10));
        setInvoice(data);
      } catch (err: unknown) {
        const apiError = err as { message?: string; detail?: string | Record<string, unknown> };
        const errorMessage =
          typeof apiError.detail === 'string'
            ? apiError.detail
            : apiError.message || t('invoiceDetail.error');
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchInvoice();
  }, [invoiceId, direction]);

  useEffect(() => {
    const checkUsage = async () => {
      try {
        const usageData = await getUsage();
        if (usageData) {
          setUsage({
            invoice_limit_exceeded: usageData.invoice_limit_exceeded,
            ai_limit_exceeded: usageData.ai_limit_exceeded,
          });
        }
      } catch {
        // Ignore errors
      }
    };
    checkUsage();
  }, []);

  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleString(direction === 'rtl' ? 'ar-SA' : 'en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const downloadJSON = (data: Record<string, unknown>, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadXML = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const _copyQRCode = async () => {
    if (!invoice?.qr_code_data) return;
    try {
      await navigator.clipboard.writeText(invoice.qr_code_data);
      setCopiedField('qr');
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Failed to copy QR:', err);
    }
  };

  const handleExplainError = async () => {
    if (!invoice) return;

    setAiLoading(true);
    setAiError(null);
    setExplainResult(null);

    try {
      const errorCode = invoice.zatca_response_code || 'UNKNOWN';
      const result = await explainError({
        error_code: errorCode,
        use_ai: true,
        include_arabic: true,
      });
      setExplainResult(result);
      setShowExplainModal(true);
    } catch (err: unknown) {
      const apiError = err as { message?: string; detail?: string | Record<string, unknown> };
      setAiError(
        typeof apiError.detail === 'string'
          ? apiError.detail
          : apiError.message || t('invoiceDetail.aiError')
      );
    } finally {
      setAiLoading(false);
    }
  };

  const handlePredictRejection = async () => {
    if (!invoice) return;

    setAiLoading(true);
    setAiError(null);
    setPredictResult(null);

    try {
      const invoicePayload = {
        invoice_number: invoice.invoice_number,
        environment: invoice.environment,
        status: invoice.status,
      };

      const result = await predictRejection({
        invoice_payload: invoicePayload,
        environment: invoice.environment as 'SANDBOX' | 'PRODUCTION',
      });
      setPredictResult(result);
      setShowPredictModal(true);
    } catch (err: unknown) {
      const apiError = err as { message?: string; detail?: string | Record<string, unknown> };
      setAiError(
        typeof apiError.detail === 'string'
          ? apiError.detail
          : apiError.message || t('invoiceDetail.aiError')
      );
    } finally {
      setAiLoading(false);
    }
  };

  const CopyButton: React.FC<{ text: string; field: string; label?: string }> = ({ text, field, label }) => {
    const isCopied = copiedField === field;
    return (
      <button
        onClick={() => copyToClipboard(text, field)}
        className="inline-flex items-center gap-1 px-2 py-1 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded transition-colors"
        title={isCopied ? t('common.copied') : (label || t('common.copy'))}
      >
        {isCopied ? (
          <>
            <svg className="w-3 h-3 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-emerald-600">{t('common.copied')}</span>
          </>
        ) : (
          <>
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span>{label || t('common.copy')}</span>
          </>
        )}
      </button>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6" dir={direction} data-testid="invoice-detail-page">
        <InvoiceDetailSkeleton />
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="space-y-6" dir={direction} data-testid="invoice-detail-page">
        <Card padding="md">
          <EmptyState
            icon={
              <svg
                className="w-16 h-16 text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            }
            title={t('invoiceDetail.notFound')}
            description={error || t('invoiceDetail.notFoundDesc')}
            actionLabel={t('invoiceDetail.back')}
            onAction={() => navigate('/invoices')}
          />
        </Card>
      </div>
    );
  }

  const tabs = [
    { id: 'summary', label: t('invoiceDetail.summary') },
    { id: 'request', label: t('invoiceDetail.requestJson') },
    { id: 'xml', label: 'XML' },
    { id: 'response', label: t('invoiceDetail.zatcaResponse') },
    { id: 'troubleshooting', label: t('invoiceDetail.troubleshooting') },
  ];

  // Build request payload (best effort from available data)
  const requestPayload = invoice.request_payload || {
    invoice_number: invoice.invoice_number,
    environment: invoice.environment,
    phase: invoice.phase || (invoice.uuid ? 'PHASE_2' : 'PHASE_1'),
    uuid: invoice.uuid || undefined,
    hash: invoice.hash || undefined,
  };

  // Build ZATCA response (best effort from available data)
  const zatcaResponse = invoice.zatca_response || {
    status: invoice.status,
    zatca_response_code: invoice.zatca_response_code,
    uuid: invoice.uuid,
    hash: invoice.hash,
    environment: invoice.environment,
  };

  return (
    <div className="space-y-6" dir={direction} data-testid="invoice-detail-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t('invoiceDetail.title')}
          </h1>
          <p className="text-slate-500 mt-1">{invoice.invoice_number}</p>
        </div>
        <Button variant="secondary" onClick={() => navigate('/invoices')} data-testid="back-button">
          {t('common.back')}
        </Button>
      </div>

      {/* Limit Banner */}
      {usage && (usage.invoice_limit_exceeded || usage.ai_limit_exceeded) && (
        <LimitBanner
          invoiceLimitExceeded={usage.invoice_limit_exceeded}
          aiLimitExceeded={usage.ai_limit_exceeded}
        />
      )}

      {/* AI Action Buttons */}
      <div className="flex gap-3">
        <Button
          variant="secondary"
          onClick={handleExplainError}
          disabled={aiLoading || !invoice.zatca_response_code || invoice.status !== 'REJECTED'}
        >
          {aiLoading ? (
            <div className="flex items-center gap-2">
              <Loader size="sm" />
              <span>{t('invoiceDetail.processing')}</span>
            </div>
          ) : (
            t('invoiceDetail.explainError')
          )}
        </Button>
        <Button
          variant="secondary"
          onClick={handlePredictRejection}
          disabled={aiLoading}
        >
          {aiLoading ? (
            <div className="flex items-center gap-2">
              <Loader size="sm" />
              <span>{t('invoiceDetail.processing')}</span>
            </div>
          ) : (
            t('invoiceDetail.predictRejection')
          )}
        </Button>
      </div>

      {/* AI Error Display */}
      {aiError && (
        <Card padding="md" className="bg-red-50 border-red-200">
          <p className="text-sm text-red-800 break-words">{aiError}</p>
        </Card>
      )}

      {/* Tabs */}
      <Card padding="none" className="overflow-hidden" data-testid="invoice-detail-tabs">
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'summary' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-slate-600 flex items-center justify-between">
                    <span>{t('invoice.number')}</span>
                    <CopyButton text={invoice.invoice_number} field="invoice_number" />
                  </label>
                  <p className="mt-1 text-sm text-slate-900 font-medium font-mono">{invoice.invoice_number}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-600">
                    {t('invoice.status')}
                  </label>
                  <div className="mt-1">
                    <InvoiceStatusBadge status={invoice.status} />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-600">
                    {t('invoice.phase')}
                  </label>
                  <p className="mt-1 text-sm text-slate-900">
                    {invoice.phase || (invoice.uuid ? 'PHASE_2' : 'PHASE_1')}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-600">
                    {t('topbar.environment.sandbox')} / {t('topbar.environment.production')}
                  </label>
                  <p className="mt-1 text-sm text-slate-900">{invoice.environment}</p>
                </div>
                {invoice.uuid && (
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium text-slate-600 flex items-center justify-between">
                      <span>UUID</span>
                      <CopyButton text={invoice.uuid} field="uuid" />
                    </label>
                    <p className="mt-1 text-sm text-slate-900 font-mono break-all">{invoice.uuid}</p>
                  </div>
                )}
                {invoice.hash && (
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium text-slate-600 flex items-center justify-between">
                      <span>Hash</span>
                      <CopyButton text={invoice.hash} field="hash" />
                    </label>
                    <p className="mt-1 text-sm text-slate-900 font-mono break-all">{invoice.hash}</p>
                  </div>
                )}
                {invoice.zatca_response_code && (
                  <div>
                    <label className="text-sm font-medium text-slate-600">
                      {t('invoiceDetail.responseCode')}
                    </label>
                    <p className="mt-1 text-sm text-slate-900 font-mono">{invoice.zatca_response_code}</p>
                  </div>
                )}
                <div>
                  <label className="text-sm font-medium text-slate-600">
                    {t('invoiceDetail.createdAt')}
                  </label>
                  <p className="mt-1 text-sm text-slate-900">{formatDate(invoice.created_at)}</p>
                </div>
              </div>

              {/* QR Code Preview */}
              {invoice.qr_code_data && (
                <div className="pt-4 border-t border-slate-200">
                  <label className="text-sm font-medium text-slate-600 flex items-center justify-between mb-2">
                    <span>{t('invoiceCreate.qrCode')}</span>
                    <CopyButton text={invoice.qr_code_data} field="qr" label={t('invoiceDetail.copyQr')} />
                  </label>
                  <div className="bg-white p-4 rounded-lg border border-slate-200 inline-block">
                    {invoice.qr_code_data.startsWith('data:image') || invoice.qr_code_data.startsWith('/9j/') ? (
                      <img
                        src={invoice.qr_code_data.startsWith('data:') ? invoice.qr_code_data : `data:image/png;base64,${invoice.qr_code_data}`}
                        alt="QR Code"
                        className="w-32 h-32"
                      />
                    ) : (
                      <div className="w-32 h-32 flex items-center justify-center text-xs text-slate-500">
                        {t('invoiceDetail.invalidQr')}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'request' && (
            <div className="space-y-4">
              {invoice.request_payload ? (
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-600">
                      {t('invoiceDetail.originalRequest')}
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => downloadJSON(requestPayload, `invoice-${invoice.invoice_number}-request.json`)}
                    >
                      {t('invoiceDetail.downloadJson')}
                    </Button>
                  </div>
                  <CodeBlock
                    content={JSON.stringify(requestPayload, null, 2)}
                    language="json"
                    filename={`invoice-${invoice.invoice_number}-request.json`}
                  />
                </>
              ) : (
                <>
                  <p className="text-sm text-slate-600 mb-4">
                    {t('invoiceDetail.requestNotAvailable')}
                  </p>
                  <CodeBlock
                    content={JSON.stringify(requestPayload, null, 2)}
                    language="json"
                    filename={`invoice-${invoice.invoice_number}-request.json`}
                  />
                </>
              )}
            </div>
          )}

          {activeTab === 'xml' && (
            <div className="space-y-4">
              {invoice.xml_content ? (
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-600">
                      {t('invoiceDetail.generatedXml')}
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => downloadXML(invoice.xml_content!, `invoice-${invoice.invoice_number}.xml`)}
                    >
                      {t('invoiceDetail.downloadXml')}
                    </Button>
                  </div>
                  <CodeBlock
                    content={invoice.xml_content}
                    language="xml"
                    filename={`invoice-${invoice.invoice_number}.xml`}
                  />
                </>
              ) : (
                <div className="text-center py-12">
                  <p className="text-slate-500 mb-2">
                    {t('invoiceDetail.xmlNotAvailable')}
                  </p>
                  <p className="text-sm text-slate-400">
                    {t('invoiceDetail.xmlNotStored')}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'response' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-600">
                  {t('invoiceDetail.zatcaResponse')}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => downloadJSON(zatcaResponse, `invoice-${invoice.invoice_number}-response.json`)}
                >
                  {t('invoiceDetail.downloadJson')}
                </Button>
              </div>
              <CodeBlock
                content={JSON.stringify(zatcaResponse, null, 2)}
                language="json"
                filename={`invoice-${invoice.invoice_number}-response.json`}
              />
            </div>
          )}

          {activeTab === 'troubleshooting' && (
            <div className="space-y-6">
              {/* Last Error Message */}
              {invoice.zatca_response_code && invoice.status === 'REJECTED' && (
                <Card padding="md" className="bg-red-50 border-red-200">
                  <h3 className="text-sm font-semibold text-red-900 mb-2">
                    {direction === 'rtl' ? 'آخر رسالة خطأ' : 'Last Error Message'}
                  </h3>
                  <p className="text-sm text-red-800 font-mono">{invoice.zatca_response_code}</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="mt-3"
                    onClick={handleExplainError}
                    disabled={aiLoading}
                  >
                    {direction === 'rtl' ? 'شرح الخطأ' : 'Explain Error'}
                  </Button>
                </Card>
              )}

              {/* Environment Info */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-3">
                  {direction === 'rtl' ? 'معلومات البيئة' : 'Environment Information'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-slate-600">
                      {direction === 'rtl' ? 'البيئة' : 'Environment'}
                    </label>
                    <p className="mt-1 text-sm text-slate-900 font-medium">{invoice.environment}</p>
                  </div>
                  <div>
                    <label className="text-xs text-slate-600">
                      {direction === 'rtl' ? 'المرحلة' : 'Phase'}
                    </label>
                    <p className="mt-1 text-sm text-slate-900">
                      {invoice.phase || (invoice.uuid ? 'PHASE_2' : 'PHASE_1')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Status Timeline */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-3">
                  {direction === 'rtl' ? 'الجدول الزمني للحالة' : 'Status Timeline'}
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-900">
                        {direction === 'rtl' ? 'تم الإنشاء' : 'Created'}
                      </p>
                      <p className="text-xs text-slate-500">{formatDate(invoice.created_at)}</p>
                    </div>
                    <InvoiceStatusBadge status={invoice.status} />
                  </div>
                  {invoice.status === 'REJECTED' && (
                    <div className="flex items-center gap-3 ps-4">
                      <div className="w-2 h-2 rounded-full bg-red-500"></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-red-900">
                          {direction === 'rtl' ? 'مرفوض' : 'Rejected'}
                        </p>
                        {invoice.zatca_response_code && (
                          <p className="text-xs text-red-600 font-mono">{invoice.zatca_response_code}</p>
                        )}
                      </div>
                    </div>
                  )}
                  {invoice.status === 'CLEARED' && (
                    <div className="flex items-center gap-3 ps-4">
                      <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-emerald-900">
                          {direction === 'rtl' ? 'مقبول' : 'Cleared'}
                        </p>
                        {invoice.uuid && (
                          <p className="text-xs text-emerald-600 font-mono">{invoice.uuid}</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* AI Quick Actions */}
              {invoice.status === 'REJECTED' && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">
                    {direction === 'rtl' ? 'إجراءات سريعة' : 'Quick Actions'}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleExplainError}
                      disabled={aiLoading || !invoice.zatca_response_code}
                    >
                      {direction === 'rtl' ? 'شرح الخطأ' : 'Explain Error'}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handlePredictRejection}
                      disabled={aiLoading}
                    >
                      {direction === 'rtl' ? 'التنبؤ بالرفض' : 'Predict Rejection'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Explain Error Modal */}
      <Modal
        isOpen={showExplainModal}
        onClose={() => setShowExplainModal(false)}
        title={direction === 'rtl' ? 'شرح الخطأ' : 'Error Explanation'}
        size="lg"
      >
        {explainResult && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-600">
                {direction === 'rtl' ? 'رمز الخطأ' : 'Error Code'}
              </label>
              <p className="mt-1 text-sm text-slate-900 font-mono">{explainResult.error_code}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">
                {direction === 'rtl' ? 'الشرح' : 'Explanation'}
              </label>
              <p className="mt-1 text-sm text-slate-900">{explainResult.human_explanation}</p>
            </div>
            {explainResult.ai_english_explanation && (
              <div>
                <label className="text-sm font-medium text-slate-600">
                  {direction === 'rtl' ? 'شرح مفصل (AI)' : 'Detailed Explanation (AI)'}
                </label>
                <p className="mt-1 text-sm text-slate-900">{explainResult.ai_english_explanation}</p>
              </div>
            )}
            {explainResult.ai_arabic_explanation && (
              <div>
                <label className="text-sm font-medium text-slate-600">
                  {direction === 'rtl' ? 'الشرح بالعربية (AI)' : 'Arabic Explanation (AI)'}
                </label>
                <p className="mt-1 text-sm text-slate-900" dir="rtl">
                  {explainResult.ai_arabic_explanation}
                </p>
              </div>
            )}
            {explainResult.fix_suggestion && (
              <div>
                <label className="text-sm font-medium text-slate-600">
                  {direction === 'rtl' ? 'اقتراح الإصلاح' : 'Fix Suggestion'}
                </label>
                <p className="mt-1 text-sm text-slate-900">{explainResult.fix_suggestion}</p>
              </div>
            )}
            {explainResult.ai_fix_steps && explainResult.ai_fix_steps.length > 0 && (
              <div>
                <label className="text-sm font-medium text-slate-600">
                  {direction === 'rtl' ? 'خطوات الإصلاح' : 'Fix Steps'}
                </label>
                <ol className="mt-1 list-decimal list-inside space-y-1 text-sm text-slate-900">
                  {explainResult.ai_fix_steps.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Predict Rejection Modal */}
      <Modal
        isOpen={showPredictModal}
        onClose={() => setShowPredictModal(false)}
        title={direction === 'rtl' ? 'التنبؤ بالرفض' : 'Rejection Prediction'}
        size="lg"
      >
        {predictResult && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-600">
                {direction === 'rtl' ? 'مستوى المخاطر' : 'Risk Level'}
              </label>
              <div className="mt-1">
                <Badge
                  variant={
                    predictResult.risk_level === 'HIGH'
                      ? 'danger'
                      : predictResult.risk_level === 'MEDIUM'
                      ? 'warning'
                      : 'success'
                  }
                >
                  {predictResult.risk_level}
                </Badge>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">
                {direction === 'rtl' ? 'الثقة' : 'Confidence'}
              </label>
              <p className="mt-1 text-sm text-slate-900">
                {(predictResult.confidence * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">
                {direction === 'rtl' ? 'الملاحظة الاستشارية' : 'Advisory Note'}
              </label>
              <p className="mt-1 text-sm text-slate-900">{predictResult.advisory_note}</p>
            </div>
            {predictResult.likely_reasons && predictResult.likely_reasons.length > 0 && (
              <div>
                <label className="text-sm font-medium text-slate-600">
                  {direction === 'rtl' ? 'الأسباب المحتملة' : 'Likely Reasons'}
                </label>
                <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-slate-900">
                  {predictResult.likely_reasons.map((reason, idx) => (
                    <li key={idx}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};
