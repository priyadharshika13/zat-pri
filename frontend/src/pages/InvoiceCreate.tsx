import React, { useState, FormEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Loader } from '../components/common/Loader';
import { Badge } from '../components/common/Badge';
import { useLanguage } from '../context/LanguageContext';
import { createInvoice } from '../lib/invoiceApi';
import { InvoiceRequest, InvoiceResponse, LineItem } from '../types/invoice';
import { LimitBanner } from '../components/billing/LimitBanner';
import { getUsage } from '../lib/billingApi';
import { apiGet } from '../lib/api';
import { getZatcaStatus, ZatcaStatus } from '../lib/zatcaApi';

const INVOICE_DRAFT_KEY = 'zatca-invoice-draft';

interface InvoiceDraft {
  phase: 'PHASE_1' | 'PHASE_2';
  environment: 'SANDBOX' | 'PRODUCTION';
  invoiceNumber: string;
  invoiceDate: string;
  invoiceType: string;
  sellerName: string;
  sellerTaxNumber: string;
  sellerAddress: string;
  buyerName: string;
  buyerTaxNumber: string;
  lineItems: LineItem[];
}

function loadDraft(): InvoiceDraft | null {
  try {
    const raw = localStorage.getItem(INVOICE_DRAFT_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as InvoiceDraft;
  } catch {
    return null;
  }
}

function saveDraftToStorage(draft: InvoiceDraft): void {
  try {
    localStorage.setItem(INVOICE_DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // ignore
  }
}

function clearDraftFromStorage(): void {
  try {
    localStorage.removeItem(INVOICE_DRAFT_KEY);
  } catch {
    // ignore
  }
}

interface TenantInfo {
  company_name: string;
  vat_number: string;
  address?: string;
}

export const InvoiceCreate: React.FC = () => {
  const { direction, t } = useLanguage();
  const navigate = useNavigate();
  
  // Form state
  const [phase, setPhase] = useState<'PHASE_1' | 'PHASE_2'>('PHASE_1');
  const [environment, setEnvironment] = useState<'SANDBOX' | 'PRODUCTION'>('SANDBOX');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 16));
  const [invoiceType, setInvoiceType] = useState('388');
  
  // Seller (from tenant - readonly)
  const [sellerName, setSellerName] = useState('');
  const [sellerTaxNumber, setSellerTaxNumber] = useState('');
  const [sellerAddress, setSellerAddress] = useState('');
  const [loadingTenant, setLoadingTenant] = useState(true);
  
  // Buyer
  const [buyerName, setBuyerName] = useState('');
  const [buyerTaxNumber, setBuyerTaxNumber] = useState('');
  
  // Line items
  const [lineItems, setLineItems] = useState<LineItem[]>([
    {
      name: '',
      quantity: 1,
      unit_price: 0,
      tax_rate: 15,
      tax_category: 'S',
      discount: 0,
    },
  ]);
  
  // Totals (calculated)
  const [totals, setTotals] = useState({
    taxExclusive: 0,
    taxAmount: 0,
    totalAmount: 0,
    totalDiscount: 0,
  });
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvoiceResponse | null>(null);
  const [usage, setUsage] = useState<{ invoice_limit_exceeded: boolean; ai_limit_exceeded: boolean } | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [zatcaStatus, setZatcaStatus] = useState<ZatcaStatus | null>(null);
  const [loadingZatcaStatus, setLoadingZatcaStatus] = useState(false);
  const [draftSavedMessage, setDraftSavedMessage] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);

  // Load tenant info
  useEffect(() => {
    const loadTenantInfo = async () => {
      try {
        setLoadingTenant(true);
        const tenant = await apiGet<TenantInfo>('/api/v1/tenants/me');
        setSellerName(tenant.company_name || '');
        setSellerTaxNumber(tenant.vat_number || '');
        setSellerAddress(tenant.address || '');
      } catch (err) {
        console.error('Failed to load tenant info:', err);
        // Continue without tenant info - user can fill manually
      } finally {
        setLoadingTenant(false);
      }
    };
    loadTenantInfo();
  }, []);

  // Check for saved draft on mount
  useEffect(() => {
    const draft = loadDraft();
    setHasDraft(!!draft);
  }, []);

  // Check usage limits
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
        // Ignore errors in usage check
      }
    };
    checkUsage();
  }, []);

  // Check ZATCA status when environment changes
  useEffect(() => {
    const checkZatcaStatus = async () => {
      try {
        setLoadingZatcaStatus(true);
        const status = await getZatcaStatus(environment);
        setZatcaStatus(status);
        
        // If Phase 2 is selected but ZATCA is not connected, switch to Phase 1
        if (phase === 'PHASE_2' && !status.connected) {
          setPhase('PHASE_1');
        }
      } catch {
        // Ignore errors - set status to disconnected
        setZatcaStatus({ connected: false, environment: environment, certificate: null, certificate_expiry: null, last_sync: null });
      } finally {
        setLoadingZatcaStatus(false);
      }
    };
    checkZatcaStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [environment]);

  // Calculate totals whenever line items change
  useEffect(() => {
    let taxExclusive = 0;
    let taxAmount = 0;
    let totalDiscount = 0;

    lineItems.forEach((item) => {
      const itemSubtotal = item.quantity * item.unit_price;
      const itemDiscount = item.discount || 0;
      const itemTaxable = itemSubtotal - itemDiscount;
      const itemTax = itemTaxable * (item.tax_rate / 100);
      
      taxExclusive += itemTaxable;
      taxAmount += itemTax;
      totalDiscount += itemDiscount;
    });

    setTotals({
      taxExclusive: Math.round(taxExclusive * 100) / 100,
      taxAmount: Math.round(taxAmount * 100) / 100,
      totalAmount: Math.round((taxExclusive + taxAmount) * 100) / 100,
      totalDiscount: Math.round(totalDiscount * 100) / 100,
    });
  }, [lineItems]);

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!invoiceNumber.trim()) {
      errors.invoiceNumber = t('invoiceCreate.validation.invoiceNumberRequired');
    }

    if (!invoiceDate) {
      errors.invoiceDate = t('invoiceCreate.validation.invoiceDateRequired');
    }

    if (!sellerName.trim()) {
      errors.sellerName = t('invoiceCreate.validation.sellerNameRequired');
    }

    if (!sellerTaxNumber.trim()) {
      errors.sellerTaxNumber = t('invoiceCreate.validation.sellerTaxNumberRequired');
    } else if (sellerTaxNumber.length !== 15) {
      errors.sellerTaxNumber = t('invoiceCreate.validation.sellerTaxNumberLength');
    }

    if (lineItems.length === 0) {
      errors.lineItems = t('invoiceCreate.validation.lineItemsRequired');
    }

    lineItems.forEach((item, index) => {
      if (!item.name.trim()) {
        errors[`lineItem_${index}_name`] = t('invoiceCreate.validation.itemNameRequired');
      }
      if (item.quantity <= 0) {
        errors[`lineItem_${index}_quantity`] = t('invoiceCreate.validation.quantityRequired');
      }
      if (item.unit_price < 0) {
        errors[`lineItem_${index}_unit_price`] = t('invoiceCreate.validation.priceRequired');
      }
      if (item.tax_rate < 0 || item.tax_rate > 100) {
        errors[`lineItem_${index}_tax_rate`] = t('invoiceCreate.validation.taxRateRequired');
      }
      if (item.discount && item.discount < 0) {
        errors[`lineItem_${index}_discount`] = t('invoiceCreate.validation.discountRequired');
      }
    });

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleLineItemChange = (index: number, field: keyof LineItem, value: string | number) => {
    const updated = [...lineItems];
    updated[index] = { ...updated[index], [field]: value };
    setLineItems(updated);
    // Clear error for this field
    const errorKey = `lineItem_${index}_${field}`;
    if (formErrors[errorKey]) {
      const newErrors = { ...formErrors };
      delete newErrors[errorKey];
      setFormErrors(newErrors);
    }
  };

  const addLineItem = () => {
    setLineItems([
      ...lineItems,
      {
        name: '',
        quantity: 1,
        unit_price: 0,
        tax_rate: 15,
        tax_category: 'S',
        discount: 0,
      },
    ]);
  };

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index));
    }
  };

  const handleRestoreDraft = () => {
    const draft = loadDraft();
    if (!draft) return;
    setPhase(draft.phase);
    setEnvironment(draft.environment);
    setInvoiceNumber(draft.invoiceNumber);
    setInvoiceDate(draft.invoiceDate);
    setInvoiceType(draft.invoiceType);
    setSellerName(draft.sellerName);
    setSellerTaxNumber(draft.sellerTaxNumber);
    setSellerAddress(draft.sellerAddress);
    setBuyerName(draft.buyerName);
    setBuyerTaxNumber(draft.buyerTaxNumber);
    setLineItems(draft.lineItems.length > 0 ? draft.lineItems : [{
      name: '',
      quantity: 1,
      unit_price: 0,
      tax_rate: 15,
      tax_category: 'S',
      discount: 0,
    }]);
    clearDraftFromStorage();
    setHasDraft(false);
  };

  const handleDiscardDraft = () => {
    clearDraftFromStorage();
    setHasDraft(false);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>, isDraft: boolean = false) => {
    e.preventDefault();
    setError(null);
    setFormErrors({});

    if (!isDraft && !validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const invoiceData: InvoiceRequest = {
        mode: phase,
        environment: environment,
        invoice_number: invoiceNumber,
        invoice_date: new Date(invoiceDate).toISOString(),
        invoice_type: invoiceType,
        seller_name: sellerName,
        seller_tax_number: sellerTaxNumber,
        seller_address: sellerAddress || undefined,
        buyer_name: buyerName || undefined,
        buyer_tax_number: buyerTaxNumber || undefined,
        line_items: lineItems,
        total_discount: totals.totalDiscount > 0 ? totals.totalDiscount : undefined,
        total_tax_exclusive: totals.taxExclusive,
        total_tax_amount: totals.taxAmount,
        total_amount: totals.totalAmount,
      };

      if (isDraft) {
        const draft: InvoiceDraft = {
          phase,
          environment,
          invoiceNumber,
          invoiceDate,
          invoiceType,
          sellerName,
          sellerTaxNumber,
          sellerAddress,
          buyerName,
          buyerTaxNumber,
          lineItems,
        };
        saveDraftToStorage(draft);
        setDraftSavedMessage(true);
        setTimeout(() => setDraftSavedMessage(false), 4000);
        setLoading(false);
        return;
      }

      const response = await createInvoice(invoiceData);
      setResult(response);
      clearDraftFromStorage();
    } catch (err: unknown) {
      const apiError = err as { message?: string; detail?: string | Record<string, unknown> };
      const errorMessage =
        typeof apiError.detail === 'string'
          ? apiError.detail
          : apiError.message || t('invoiceCreate.error');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (loadingTenant) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center" dir={direction}>
        <Loader size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6" dir={direction} data-testid="invoice-create-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          {t('invoiceCreate.title')}
        </h1>
        <p className="text-slate-500 mt-1">
          {t('invoiceCreate.subtitle')}
        </p>
      </div>

      {/* Limit Banner */}
      {usage && (usage.invoice_limit_exceeded || usage.ai_limit_exceeded) && (
        <LimitBanner
          invoiceLimitExceeded={usage.invoice_limit_exceeded}
          aiLimitExceeded={usage.ai_limit_exceeded}
        />
      )}

      {/* Saved draft banner */}
      {hasDraft && (
        <Card padding="md" className="bg-amber-50 border-amber-200 flex items-center justify-between gap-4 flex-wrap">
          <p className="text-sm text-amber-800">
            {direction === 'rtl' ? 'لديك مسودة محفوظة.' : 'You have a saved draft.'}
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handleRestoreDraft} data-testid="restore-draft-button">
              {direction === 'rtl' ? 'استعادة' : 'Restore'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleDiscardDraft} data-testid="discard-draft-button">
              {direction === 'rtl' ? 'تجاهل' : 'Discard'}
            </Button>
          </div>
        </Card>
      )}

      {/* Draft saved success */}
      {draftSavedMessage && (
        <Card padding="md" className="bg-emerald-50 border-emerald-200">
          <p className="text-sm text-emerald-800">{t('invoiceCreate.saveDraft')} — {direction === 'rtl' ? 'تم الحفظ.' : 'Draft saved.'}</p>
        </Card>
      )}

      {/* Form */}
      {!result && (
        <form onSubmit={(e) => handleSubmit(e, false)} className="space-y-6" data-testid="invoice-create-form">
          {/* Phase and Environment Selection */}
          <Card padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="phase">
                  {t('invoiceCreate.phase')} <span className="text-red-500">*</span>
                </label>
                <select
                  id="phase"
                  value={phase}
                  onChange={(e) => setPhase(e.target.value as 'PHASE_1' | 'PHASE_2')}
                  disabled={loading || loadingZatcaStatus}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
                  data-testid="phase-select"
                >
                  <option value="PHASE_1">Phase 1</option>
                  <option value="PHASE_2" disabled={!zatcaStatus?.connected}>
                    Phase 2 {!zatcaStatus?.connected && '(ZATCA not connected)'}
                  </option>
                </select>
                {phase === 'PHASE_2' && !zatcaStatus?.connected && (
                  <p className="text-sm text-amber-600 mt-1">
                    Phase 2 requires ZATCA connection. Please configure ZATCA in the{' '}
                    <button
                      type="button"
                      onClick={() => navigate('/zatca-setup')}
                      className="text-emerald-600 hover:text-emerald-700 underline"
                    >
                      ZATCA Setup
                    </button>
                    {' '}page.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="environment">
                  {t('invoiceCreate.environment')} <span className="text-red-500">*</span>
                </label>
                <select
                  id="environment"
                  value={environment}
                  onChange={(e) => setEnvironment(e.target.value as 'SANDBOX' | 'PRODUCTION')}
                  disabled={loading}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
                  data-testid="environment-select"
                >
                  <option value="SANDBOX">Sandbox</option>
                  <option value="PRODUCTION">Production</option>
                </select>
              </div>
            </div>
          </Card>

          {/* Invoice Metadata */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              {t('invoiceCreate.invoiceInfo')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="invoiceNumber">
                  {t('invoiceCreate.invoiceNumber')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="invoiceNumber"
                  type="text"
                  value={invoiceNumber}
                  onChange={(e) => {
                    setInvoiceNumber(e.target.value);
                    if (formErrors.invoiceNumber) {
                      const newErrors = { ...formErrors };
                      delete newErrors.invoiceNumber;
                      setFormErrors(newErrors);
                    }
                  }}
                  disabled={loading}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed ${
                    formErrors.invoiceNumber ? 'border-red-300' : 'border-slate-300'
                  }`}
                  placeholder={direction === 'rtl' ? 'INV-2024-001' : 'INV-2024-001'}
                  data-testid="invoice-number-input"
                />
                {formErrors.invoiceNumber && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.invoiceNumber}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="invoiceDate">
                  {t('invoiceCreate.invoiceDate')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="invoiceDate"
                  type="datetime-local"
                  value={invoiceDate}
                  onChange={(e) => {
                    setInvoiceDate(e.target.value);
                    if (formErrors.invoiceDate) {
                      const newErrors = { ...formErrors };
                      delete newErrors.invoiceDate;
                      setFormErrors(newErrors);
                    }
                  }}
                  disabled={loading}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed ${
                    formErrors.invoiceDate ? 'border-red-300' : 'border-slate-300'
                  }`}
                  data-testid="invoice-date-input"
                />
                {formErrors.invoiceDate && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.invoiceDate}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="invoiceType">
                  {t('invoiceCreate.invoiceType')}
                </label>
                <input
                  id="invoiceType"
                  type="text"
                  value={invoiceType}
                  onChange={(e) => setInvoiceType(e.target.value)}
                  disabled={loading}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
                  placeholder="388"
                  data-testid="invoice-type-input"
                />
              </div>
            </div>
          </Card>

          {/* Seller Details */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              {t('invoiceCreate.sellerInfo')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="sellerName">
                  {t('invoiceCreate.sellerName')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="sellerName"
                  type="text"
                  value={sellerName}
                  onChange={(e) => {
                    setSellerName(e.target.value);
                    if (formErrors.sellerName) {
                      const newErrors = { ...formErrors };
                      delete newErrors.sellerName;
                      setFormErrors(newErrors);
                    }
                  }}
                  disabled={loading}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed ${
                    formErrors.sellerName ? 'border-red-300' : 'border-slate-300'
                  }`}
                  placeholder={direction === 'rtl' ? 'اسم الشركة' : 'Company Name'}
                  data-testid="seller-name-input"
                />
                {formErrors.sellerName && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.sellerName}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="sellerTaxNumber">
                  {t('invoiceCreate.sellerTaxNumber')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="sellerTaxNumber"
                  type="text"
                  value={sellerTaxNumber}
                  onChange={(e) => {
                    setSellerTaxNumber(e.target.value);
                    if (formErrors.sellerTaxNumber) {
                      const newErrors = { ...formErrors };
                      delete newErrors.sellerTaxNumber;
                      setFormErrors(newErrors);
                    }
                  }}
                  disabled={loading}
                  maxLength={15}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed ${
                    formErrors.sellerTaxNumber ? 'border-red-300' : 'border-slate-300'
                  }`}
                  placeholder="123456789012345"
                  data-testid="seller-tax-number-input"
                />
                {formErrors.sellerTaxNumber && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.sellerTaxNumber}</p>
                )}
                <p className="mt-1 text-xs text-slate-500">
                  {t('invoiceCreate.digits15')}
                </p>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="sellerAddress">
                  {t('invoiceCreate.sellerAddress')}
                </label>
                <textarea
                  id="sellerAddress"
                  value={sellerAddress}
                  onChange={(e) => setSellerAddress(e.target.value)}
                  disabled={loading}
                  rows={2}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
                  placeholder={direction === 'rtl' ? 'العنوان الكامل' : 'Full Address'}
                  data-testid="seller-address-input"
                />
              </div>
            </div>
          </Card>

          {/* Buyer Details */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              {t('invoiceCreate.buyerInfo')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="buyerName">
                  {t('invoiceCreate.buyerName')}
                </label>
                <input
                  id="buyerName"
                  type="text"
                  value={buyerName}
                  onChange={(e) => setBuyerName(e.target.value)}
                  disabled={loading}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
                  placeholder={direction === 'rtl' ? 'اسم المشتري' : 'Buyer Name'}
                  data-testid="buyer-name-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="buyerTaxNumber">
                  {t('invoiceCreate.buyerTaxNumber')}
                </label>
                <input
                  id="buyerTaxNumber"
                  type="text"
                  value={buyerTaxNumber}
                  onChange={(e) => setBuyerTaxNumber(e.target.value)}
                  disabled={loading}
                  maxLength={15}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
                  placeholder="123456789012345"
                  data-testid="buyer-tax-number-input"
                />
                <p className="mt-1 text-xs text-slate-500">
                  {t('invoiceCreate.digits15Optional')}
                </p>
              </div>
            </div>
          </Card>

          {/* Line Items */}
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-900">
                {t('invoiceCreate.lineItems')}
              </h2>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={addLineItem}
                disabled={loading}
                data-testid="add-line-item-button"
              >
                {t('invoiceCreate.addItem')}
              </Button>
            </div>

            <div className="space-y-4">
              {lineItems.map((item, index) => (
                <div
                  key={index}
                  className="p-4 border border-slate-200 rounded-lg bg-slate-50"
                  data-testid={`line-item-${index}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-sm font-medium text-slate-700">
                      {t('invoiceCreate.item')} {index + 1}
                    </h3>
                    {lineItems.length > 1 && (
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() => removeLineItem(index)}
                        disabled={loading}
                        data-testid={`remove-line-item-${index}`}
                      >
                        {t('common.delete')}
                      </Button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
                    <div className="lg:col-span-2">
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        {t('invoiceCreate.itemName')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={item.name}
                        onChange={(e) => handleLineItemChange(index, 'name', e.target.value)}
                        disabled={loading}
                        className={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 ${
                          formErrors[`lineItem_${index}_name`] ? 'border-red-300' : 'border-slate-300'
                        }`}
                        data-testid={`line-item-${index}-name`}
                      />
                      {formErrors[`lineItem_${index}_name`] && (
                        <p className="mt-0.5 text-xs text-red-600">{formErrors[`lineItem_${index}_name`]}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        {t('invoiceCreate.quantity')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={item.quantity}
                        onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                        disabled={loading}
                        className={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 ${
                          formErrors[`lineItem_${index}_quantity`] ? 'border-red-300' : 'border-slate-300'
                        }`}
                        data-testid={`line-item-${index}-quantity`}
                      />
                      {formErrors[`lineItem_${index}_quantity`] && (
                        <p className="mt-0.5 text-xs text-red-600">{formErrors[`lineItem_${index}_quantity`]}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        {t('invoiceCreate.unitPrice')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => handleLineItemChange(index, 'unit_price', parseFloat(e.target.value) || 0)}
                        disabled={loading}
                        className={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 ${
                          formErrors[`lineItem_${index}_unit_price`] ? 'border-red-300' : 'border-slate-300'
                        }`}
                        data-testid={`line-item-${index}-unit-price`}
                      />
                      {formErrors[`lineItem_${index}_unit_price`] && (
                        <p className="mt-0.5 text-xs text-red-600">{formErrors[`lineItem_${index}_unit_price`]}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        {t('invoiceCreate.taxRate')} % <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={item.tax_rate}
                        onChange={(e) => handleLineItemChange(index, 'tax_rate', parseFloat(e.target.value) || 0)}
                        disabled={loading}
                        className={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 ${
                          formErrors[`lineItem_${index}_tax_rate`] ? 'border-red-300' : 'border-slate-300'
                        }`}
                        data-testid={`line-item-${index}-tax-rate`}
                      />
                      {formErrors[`lineItem_${index}_tax_rate`] && (
                        <p className="mt-0.5 text-xs text-red-600">{formErrors[`lineItem_${index}_tax_rate`]}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        {t('invoiceCreate.category')} <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={item.tax_category}
                        onChange={(e) => handleLineItemChange(index, 'tax_category', e.target.value)}
                        disabled={loading}
                        className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        data-testid={`line-item-${index}-tax-category`}
                      >
                        <option value="S">Standard (S)</option>
                        <option value="Z">Zero-rated (Z)</option>
                        <option value="E">Exempt (E)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        {t('invoiceCreate.discount')}
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={item.discount || 0}
                        onChange={(e) => handleLineItemChange(index, 'discount', parseFloat(e.target.value) || 0)}
                        disabled={loading}
                        className={`w-full px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 ${
                          formErrors[`lineItem_${index}_discount`] ? 'border-red-300' : 'border-slate-300'
                        }`}
                        data-testid={`line-item-${index}-discount`}
                      />
                      {formErrors[`lineItem_${index}_discount`] && (
                        <p className="mt-0.5 text-xs text-red-600">{formErrors[`lineItem_${index}_discount`]}</p>
                      )}
                    </div>
                  </div>

                  {/* Line item totals */}
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <div className="flex justify-between text-xs text-slate-600">
                      <span>{t('invoiceCreate.subtotal')}:</span>
                      <span className="font-medium">
                        {((item.quantity * item.unit_price) - (item.discount || 0)).toFixed(2)} {t('invoiceCreate.currency')}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs text-slate-600">
                      <span>{t('invoiceCreate.tax')}:</span>
                      <span className="font-medium">
                        {(((item.quantity * item.unit_price) - (item.discount || 0)) * (item.tax_rate / 100)).toFixed(2)} {t('invoiceCreate.currency')}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm font-semibold text-slate-900 mt-1">
                      <span>{t('invoiceCreate.total')}:</span>
                      <span>
                        {((item.quantity * item.unit_price) - (item.discount || 0) + ((item.quantity * item.unit_price) - (item.discount || 0)) * (item.tax_rate / 100)).toFixed(2)} {t('invoiceCreate.currency')}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {formErrors.lineItems && (
              <p className="mt-2 text-sm text-red-600">{formErrors.lineItems}</p>
            )}
          </Card>

          {/* Totals Summary */}
          <Card padding="lg" className="bg-emerald-50 border-emerald-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              {t('invoiceCreate.invoiceSummary')}
            </h2>
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-slate-700">
                <span>{t('invoiceCreate.subtotalExclTax')}:</span>
                <span className="font-medium">{totals.taxExclusive.toFixed(2)} {t('invoiceCreate.currency')}</span>
              </div>
              {totals.totalDiscount > 0 && (
                <div className="flex justify-between text-sm text-slate-700">
                  <span>{t('invoiceCreate.totalDiscount')}:</span>
                  <span className="font-medium">-{totals.totalDiscount.toFixed(2)} {t('invoiceCreate.currency')}</span>
                </div>
              )}
              <div className="flex justify-between text-sm text-slate-700">
                <span>{t('invoiceCreate.totalTax')}:</span>
                <span className="font-medium">{totals.taxAmount.toFixed(2)} {t('invoiceCreate.currency')}</span>
              </div>
              <div className="flex justify-between text-lg font-bold text-slate-900 pt-2 border-t border-emerald-300">
                <span>{t('invoiceCreate.totalAmount')}:</span>
                <span>{totals.totalAmount.toFixed(2)} {t('invoiceCreate.currency')}</span>
              </div>
            </div>
          </Card>

          {/* Error Display */}
          {error && (
            <Card padding="md" className="bg-red-50 border-red-200">
              <p className="text-sm text-red-800 break-words">{error}</p>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={(e) => handleSubmit(e as unknown as FormEvent<HTMLFormElement>, true)}
              disabled={loading}
              data-testid="save-draft-button"
            >
              {t('invoiceCreate.saveDraft')}
            </Button>
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              disabled={loading}
              isLoading={loading}
              data-testid="submit-invoice-button"
            >
              {loading ? t('invoiceCreate.processing') : t('invoiceCreate.submit')}
            </Button>
          </div>
        </form>
      )}

      {/* Result Summary */}
      {result && (
        <Card padding="lg" className="bg-emerald-50 border-emerald-200">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                {t('invoiceCreate.processingResult')}
              </h2>
              <Badge variant={result.success ? 'success' : 'danger'}>
                {result.success ? t('invoiceCreate.success') : t('invoiceCreate.failed')}
              </Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">
                  {t('invoiceCreate.invoiceNumber')}:
                </span>
                <span className="font-medium text-slate-900">{result.invoice_number}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">
                  {t('invoiceCreate.phase')}:
                </span>
                <span className="font-medium text-slate-900">{result.mode}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">
                  {t('invoiceCreate.environment')}:
                </span>
                <span className="font-medium text-slate-900">{result.environment}</span>
              </div>
              {result.clearance?.uuid && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">UUID:</span>
                  <span className="font-medium text-slate-900 font-mono text-xs break-all">
                    {result.clearance.uuid}
                  </span>
                </div>
              )}
              {result.qr_code_data?.qr_code && (
                <div className="pt-2">
                  <p className="text-slate-600 mb-2">
                    {t('invoiceCreate.qrCode')}:
                  </p>
                  <div className="bg-white p-4 rounded-lg border border-slate-200 inline-block">
                    <img
                      src={result.qr_code_data.qr_code}
                      alt="QR Code"
                      className="w-32 h-32"
                    />
                  </div>
                </div>
              )}
              {result.errors && result.errors.length > 0 && (
                <div className="pt-2">
                  <p className="text-red-600 font-medium mb-2">
                    {t('invoiceCreate.errors')}:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-red-600">
                    {result.errors.map((err, idx) => (
                      <li key={idx} className="break-words">{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="flex gap-3 pt-4 border-t border-slate-200">
              <Button
                variant="secondary"
                onClick={() => {
                  setResult(null);
                  setInvoiceNumber('');
                  setInvoiceDate(new Date().toISOString().slice(0, 16));
                  setBuyerName('');
                  setBuyerTaxNumber('');
                  setLineItems([
                    {
                      name: '',
                      quantity: 1,
                      unit_price: 0,
                      tax_rate: 15,
                      tax_category: 'S',
                      discount: 0,
                    },
                  ]);
                  setError(null);
                  setFormErrors({});
                }}
                data-testid="create-another-button"
              >
                {t('invoiceCreate.createAnother')}
              </Button>
              <Button variant="primary" onClick={() => navigate('/invoices')} data-testid="view-invoices-button">
                {t('invoiceCreate.viewAllInvoices')}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
