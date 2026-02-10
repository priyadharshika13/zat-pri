import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Language = 'en' | 'ar';
export type Direction = 'ltr' | 'rtl';

interface LanguageContextType {
  language: Language;
  direction: Direction;
  toggleLanguage: () => void;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// Translation dictionary
const translations: Record<Language, Record<string, string>> = {
  en: {
    // Navigation
    'nav.dashboard': 'Dashboard',
    'nav.createInvoice': 'Create Invoice',
    'nav.invoices': 'Invoices',
    'nav.aiInsights': 'AI Insights',
    'nav.apiPlayground': 'API Playground',
    'nav.billing': 'Billing',
    'nav.webhooks': 'Webhooks',
    'nav.reports': 'Reports',
    'nav.apiKeys': 'API Keys',
    'nav.zatcaSetup': 'ZATCA Setup',
    'nav.plans': 'Plans',
    
    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.totalInvoices': 'Total Invoices',
    'dashboard.cleared': 'Cleared',
    'dashboard.rejected': 'Rejected',
    'dashboard.pending': 'Pending',
    'dashboard.aiPredictions': 'AI Predictions Used',
    'dashboard.recentInvoices': 'Recent Invoices',
    'dashboard.aiInsights': 'AI Insights Summary',
    'dashboard.clearanceChart': 'Invoice Clearance Chart',
    
    // Invoice
    'invoice.number': 'Invoice Number',
    'invoice.phase': 'Phase',
    'invoice.status': 'Status',
    'invoice.date': 'Date',
    'invoice.actions': 'Actions',
    'invoice.status.cleared': 'Cleared',
    'invoice.status.rejected': 'Rejected',
    'invoice.status.pending': 'Pending',
    
    // Common
    'common.view': 'View',
    'common.edit': 'Edit',
    'common.delete': 'Delete',
    'common.loading': 'Loading...',
    
    // Topbar
    'topbar.environment.sandbox': 'Sandbox',
    'topbar.environment.production': 'Production',
    'topbar.apiUsage': 'API Usage',
    
    // System Status
    'system.status': 'System Status',
    'system.zatca': 'ZATCA API',
    'system.ai': 'AI Service',
    'system.uptime': 'Uptime',
    'system.version': 'Version',
    'system.lastChecked': 'Last checked',
    'system.connected': 'Connected',
    'system.disconnected': 'Disconnected',
    'system.enabled': 'Enabled',
    'system.disabled': 'Disabled',
    'system.error': 'Error',
    
    // API Usage
    'usage.title': 'API Usage',
    'usage.zatca': 'ZATCA Submissions',
    'usage.ai': 'AI Calls',
    'usage.thisMonth': 'This month',
    
    // Environment Banner
    'banner.sandbox': 'Sandbox Mode',
    'banner.sandbox.desc': 'Invoices are NOT legally valid',
    'banner.production': 'Production Mode',
    'banner.production.desc': 'ZATCA submissions are LIVE',
    
    // Plans & Billing
    'plans.title': 'Plans & Pricing',
    'plans.subtitle': 'Choose the plan that fits your needs',
    'plans.choosePlan': 'Choose Plan',
    'plans.upgrade': 'Upgrade',
    'plans.getApiKey': 'Get API Key',
    'plans.needApiKey': 'Need an API Key?',
    'plans.contactUs': 'Contact us to get an API key and start using the service',
    'plans.noPlans': 'No plans available',
    'plans.recommended': 'Recommended',
    'plans.currentPlan': 'Current Plan',
    'plans.invoicesPerMonth': 'Invoices/month',
    'plans.aiCallsPerMonth': 'AI calls/month',
    'plans.rateLimit': 'Rate limit/min',
    'plans.features': 'Features',
    
    // Billing
    'billing.title': 'Billing & Subscription',
    'billing.subtitle': 'Manage your subscription and usage',
    'billing.currentPlan': 'Current Plan',
    'billing.billingPeriod': 'Billing Period',
    'billing.invoiceUsage': 'Invoice Usage',
    'billing.aiUsage': 'AI Usage',
    'billing.invoicesSent': 'Invoices Sent',
    'billing.aiCalls': 'AI Calls',
    'billing.used': 'used',
    'billing.unlimited': 'Unlimited',
    'billing.noLimit': 'No limit',
    'billing.limitExceeded': 'Limit exceeded',
    'billing.rateLimit': 'Rate Limit',
    'billing.rateLimitDesc': 'Limits are applied according to your plan',
    'billing.upgradeTitle': 'Upgrade Your Plan',
    'billing.upgradeDesc': 'Get more invoices and AI calls',
    'billing.viewPlans': 'View Plans',
    'billing.noSubscription': 'No Active Subscription',
    'billing.noSubscriptionDesc': 'Choose a plan to start using the service',
    'billing.status.active': 'Active',
    'billing.status.trial': 'Trial',
    'billing.status.expired': 'Expired',
    'billing.status.suspended': 'Suspended',
    'billing.trialDaysRemaining': 'Trial days remaining',
    
    // Limit Banner
    'limitBanner.message': "You've reached your plan limit. Upgrade to continue.",
    'limitBanner.message.invoice': "You've reached your invoice limit. Upgrade to continue.",
    'limitBanner.message.ai': "You've reached your AI limit. Upgrade to continue.",
    'limitBanner.message.both': "You've reached your plan limits for invoices and AI. Upgrade to continue.",
    
    // Login
    'login.title': 'Login',
    'login.subtitle': 'Enter your credentials to access your account',
    'login.companyName': 'Company Name (optional)',
    'login.email': 'Email (optional)',
    'login.apiKey': 'API Key',
    'login.apiKeyPlaceholder': 'Enter your API key to access the dashboard',
    'login.verify': 'Verify & Login',
    'login.verifying': 'Verifying...',
    'login.invalidApiKey': 'Invalid API key',
    'login.enterApiKey': 'Please enter an API key',
    'login.serverUnreachable': 'Server unreachable. Please check your connection.',
    
    // Invoice Create
    'invoiceCreate.title': 'Create New Invoice',
    'invoiceCreate.subtitle': 'Fill out the form below to create a new invoice',
    'invoiceCreate.phase': 'Phase',
    'invoiceCreate.environment': 'Environment',
    'invoiceCreate.invoiceInfo': 'Invoice Information',
    'invoiceCreate.invoiceNumber': 'Invoice Number',
    'invoiceCreate.invoiceDate': 'Invoice Date',
    'invoiceCreate.invoiceType': 'Invoice Type',
    'invoiceCreate.sellerInfo': 'Seller Information',
    'invoiceCreate.sellerName': 'Seller Name',
    'invoiceCreate.sellerTaxNumber': 'Tax Number',
    'invoiceCreate.sellerAddress': 'Seller Address',
    'invoiceCreate.buyerInfo': 'Buyer Information',
    'invoiceCreate.buyerName': 'Buyer Name',
    'invoiceCreate.buyerTaxNumber': 'Tax Number',
    'invoiceCreate.lineItems': 'Line Items',
    'invoiceCreate.addItem': '+ Add Item',
    'invoiceCreate.item': 'Item',
    'invoiceCreate.itemName': 'Name',
    'invoiceCreate.quantity': 'Quantity',
    'invoiceCreate.unitPrice': 'Unit Price',
    'invoiceCreate.taxRate': 'Tax Rate',
    'invoiceCreate.taxCategory': 'Tax Category',
    'invoiceCreate.discount': 'Discount',
    'invoiceCreate.remove': 'Remove',
    'invoiceCreate.totals': 'Totals',
    'invoiceCreate.taxExclusive': 'Tax Exclusive',
    'invoiceCreate.taxAmount': 'Tax Amount',
    'invoiceCreate.totalAmount': 'Total Amount',
    'invoiceCreate.totalDiscount': 'Total Discount',
    'invoiceCreate.saveDraft': 'Save Draft',
    'invoiceCreate.submit': 'Submit to ZATCA',
    'invoiceCreate.submitting': 'Submitting...',
    'invoiceCreate.success': 'Invoice created successfully!',
    'invoiceCreate.error': 'Failed to create invoice. Please try again.',
    'invoiceCreate.required': 'required',
    'invoiceCreate.digits15': '15 digits',
    'invoiceCreate.digits15Optional': '15 digits (optional)',
    'invoiceCreate.validation.invoiceNumberRequired': 'Invoice number is required',
    'invoiceCreate.validation.invoiceDateRequired': 'Invoice date is required',
    'invoiceCreate.validation.sellerNameRequired': 'Seller name is required',
    'invoiceCreate.validation.sellerTaxNumberRequired': 'Seller tax number is required',
    'invoiceCreate.validation.sellerTaxNumberLength': 'Tax number must be 15 digits',
    'invoiceCreate.validation.lineItemsRequired': 'At least one line item is required',
    'invoiceCreate.validation.itemNameRequired': 'Item name is required',
    'invoiceCreate.validation.quantityRequired': 'Quantity must be greater than zero',
    'invoiceCreate.validation.priceRequired': 'Price must be greater than or equal to zero',
    'invoiceCreate.validation.taxRateRequired': 'Tax rate must be between 0 and 100',
    'invoiceCreate.validation.discountRequired': 'Discount must be greater than or equal to zero',
    
    // Invoice List
    'invoiceList.title': 'Invoices',
    'invoiceList.total': 'Total invoices',
    'invoiceList.createInvoice': '+ Create Invoice',
    'invoiceList.loading': 'Loading invoices...',
    'invoiceList.error': 'Failed to load invoices',
    'invoiceList.empty': 'No invoices found',
    'invoiceList.emptyDesc': 'Create your first invoice to get started',
    'invoiceList.retry': 'Retry',
    'invoiceList.view': 'View',
    'invoiceList.phase1': 'Phase 1',
    'invoiceList.phase2': 'Phase 2',
    
    // Invoice Detail
    'invoiceDetail.title': 'Invoice Details',
    'invoiceDetail.back': 'Back to Invoices',
    'invoiceDetail.loading': 'Loading invoice...',
    'invoiceDetail.error': 'Failed to load invoice',
    'invoiceDetail.notFound': 'Invoice not found',
    'invoiceDetail.notFoundDesc': 'The invoice you are looking for does not exist',
    'invoiceDetail.summary': 'Summary',
    'invoiceDetail.xml': 'XML',
    'invoiceDetail.response': 'ZATCA Response',
    'invoiceDetail.logs': 'Processing Logs',
    'invoiceDetail.copy': 'Copy',
    'invoiceDetail.copied': 'Copied!',
    'invoiceDetail.download': 'Download',
    'invoiceDetail.explainError': 'Explain Error',
    'invoiceDetail.predictRejection': 'Predict Rejection',
    'invoiceDetail.aiLoading': 'Loading AI explanation...',
    'invoiceDetail.aiError': 'Failed to load AI explanation',
    
    // Invoice Status
    'invoiceStatus.created': 'Created',
    'invoiceStatus.processing': 'Processing',
    'invoiceStatus.cleared': 'Cleared',
    'invoiceStatus.rejected': 'Rejected',
    'invoiceStatus.failed': 'Failed',
    
    // Playground
    'playground.title': 'API Playground',
    'playground.subtitle': 'Test API endpoints interactively',
    'playground.selectEndpoint': 'Select an endpoint to get started',
    'playground.endpoint': 'Endpoint',
    'playground.method': 'Method',
    'playground.requestBody': 'Request Body',
    'playground.queryParams': 'Query Parameters',
    'playground.execute': 'Execute',
    'playground.executing': 'Executing...',
    'playground.response': 'Response',
    'playground.copyCurl': 'Copy cURL',
    'playground.templates': 'Templates',
    'playground.loadTemplates': 'Load Templates',
    
    // Common Actions
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.close': 'Close',
    'common.confirm': 'Confirm',
    'common.retry': 'Retry',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.previous': 'Previous',
    'common.submit': 'Submit',
    'common.reset': 'Reset',
    'common.search': 'Search',
    'common.filter': 'Filter',
    'common.sort': 'Sort',
    'common.export': 'Export',
    'common.import': 'Import',
    'common.download': 'Download',
    'common.upload': 'Upload',
    'common.copy': 'Copy',
    'common.copied': 'Copied!',
    'common.select': 'Select',
    'common.selectAll': 'Select All',
    'common.deselectAll': 'Deselect All',
    'common.yes': 'Yes',
    'common.no': 'No',
    'common.ok': 'OK',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.warning': 'Warning',
    'common.info': 'Info',
    'common.required': 'Required',
    'common.optional': 'Optional',
    'common.page': 'Page',
    'common.of': 'of',
    
    // Errors
    'error.generic': 'An error occurred',
    'error.network': 'Network error. Please check your connection.',
    'error.unauthorized': 'Unauthorized. Please check your API key.',
    'error.forbidden': 'Access forbidden',
    'error.notFound': 'Resource not found',
    'error.serverError': 'Server error. Please try again later.',
    'error.validation': 'Validation error',
    'error.timeout': 'Request timeout. Please try again.',
    
    // Invoice Create - Additional
    'invoiceCreate.item': 'Item',
    'invoiceCreate.subtotal': 'Subtotal',
    'invoiceCreate.tax': 'Tax',
    'invoiceCreate.total': 'Total',
    'invoiceCreate.invoiceSummary': 'Invoice Summary',
    'invoiceCreate.subtotalExclTax': 'Subtotal (excl. tax)',
    'invoiceCreate.totalDiscount': 'Total Discount',
    'invoiceCreate.totalTax': 'Total Tax',
    'invoiceCreate.totalAmount': 'Total Amount',
    'invoiceCreate.processingResult': 'Processing Result',
    'invoiceCreate.success': 'Success',
    'invoiceCreate.failed': 'Failed',
    'invoiceCreate.qrCode': 'QR Code',
    'invoiceCreate.errors': 'Errors',
    'invoiceCreate.createAnother': 'Create Another',
    'invoiceCreate.viewAllInvoices': 'View All Invoices',
    'invoiceCreate.processing': 'Processing...',
    'invoiceCreate.category': 'Category',
    'invoiceCreate.currency': 'SAR',
    
    // Invoice Detail - Additional
    'invoiceDetail.summary': 'Summary',
    'invoiceDetail.requestJson': 'Request JSON',
    'invoiceDetail.zatcaResponse': 'ZATCA Response',
    'invoiceDetail.troubleshooting': 'Troubleshooting',
    'invoiceDetail.responseCode': 'Response Code',
    'invoiceDetail.createdAt': 'Created At',
    'invoiceDetail.originalRequest': 'Original request payload',
    'invoiceDetail.downloadJson': 'Download JSON',
    'invoiceDetail.requestNotAvailable': 'Original request payload is not available in the invoice log. Showing available data only.',
    'invoiceDetail.generatedXml': 'Generated XML content',
    'invoiceDetail.downloadXml': 'Download XML',
    'invoiceDetail.xmlNotAvailable': 'XML content not available',
    'invoiceDetail.xmlNotStored': 'XML is not stored in the invoice log. It may only be available when the invoice is created.',
    'invoiceDetail.invalidQr': 'Invalid QR',
    'invoiceDetail.copyQr': 'Copy QR',
    'invoiceDetail.explainError': 'Explain Error',
    'invoiceDetail.predictRejection': 'Predict Rejection',
    'invoiceDetail.processing': 'Processing...',
    
    // Playground - Additional
    'playground.requestConfig': 'Request Configuration',
    'playground.hide': 'Hide',
    'playground.show': 'Show',
    'playground.templates': 'Templates',
    'playground.queryParamsOptional': 'Query Parameters (optional)',
    'playground.productionConfirm': 'I confirm this is a PRODUCTION action',
    'playground.productionWarning': 'Production write operations require explicit confirmation.',
    'playground.executing': 'Executing...',
    'playground.executeRequest': 'Execute Request',
    'playground.curlCommand': 'cURL Command',
    'playground.response': 'Response',
    'playground.testEndpoints': 'Test API endpoints interactively. All requests use your API key automatically.',
    'playground.selectEndpointDesc': 'Select an endpoint from the list above or use a template to get started',
    
    // Billing - Additional
    'billing.changePlan': 'Change Plan',
    'billing.changePlanDesc': 'You will be redirected to the plans page where you can select a new plan. Changes will be applied to your current subscription.',
    'billing.continue': 'Continue',
    'billing.invoicesSent': 'Invoices Sent',
    'billing.aiCalls': 'AI Calls',
    
    // Dashboard - Additional
    'dashboard.subtitle': 'Overview of invoice performance and compliance',
    
    // Plans
    'plans.viewPlans': 'View Plans',
    'plans.sandboxNote': 'Sandbox access is free. Production requires an active plan.',
    'plans.inquiries': 'For inquiries:',
    'plans.contactSales': 'Contact Sales',
    
    // Topbar
    'topbar.apiKeySession': 'API Key Session',
    'topbar.logout': 'Logout',
    
    // Invoice Detail - Additional
    'invoiceDetail.title': 'Invoice Details',
    'invoiceDetail.notFound': 'Invoice not found',
    'invoiceDetail.notFoundDesc': 'The requested invoice could not be found',
    'invoiceDetail.back': 'Back to Invoices',
    'invoiceDetail.error': 'Failed to load invoice',
    'invoiceDetail.aiError': 'Failed to process AI request',
  },
  ar: {
    // Navigation
    'nav.dashboard': 'لوحة التحكم',
    'nav.createInvoice': 'إنشاء فاتورة',
    'nav.invoices': 'الفواتير',
    'nav.aiInsights': 'رؤى الذكاء الاصطناعي',
    'nav.apiPlayground': 'ملعب API',
    'nav.billing': 'الفواتير والاشتراكات',
    'nav.webhooks': 'الوبهوكات',
    'nav.reports': 'التقارير',
    'nav.apiKeys': 'مفاتيح API',
    'nav.zatcaSetup': 'إعداد ZATCA',
    'nav.plans': 'الخطط',
    
    // Dashboard
    'dashboard.title': 'لوحة التحكم',
    'dashboard.totalInvoices': 'إجمالي الفواتير',
    'dashboard.cleared': 'مقبولة',
    'dashboard.rejected': 'مرفوضة',
    'dashboard.pending': 'قيد الانتظار',
    'dashboard.aiPredictions': 'تنبؤات الذكاء الاصطناعي المستخدمة',
    'dashboard.recentInvoices': 'الفواتير الأخيرة',
    'dashboard.aiInsights': 'ملخص رؤى الذكاء الاصطناعي',
    'dashboard.clearanceChart': 'رسم بياني لاعتماد الفواتير',
    
    // Invoice
    'invoice.number': 'رقم الفاتورة',
    'invoice.phase': 'المرحلة',
    'invoice.status': 'الحالة',
    'invoice.date': 'التاريخ',
    'invoice.actions': 'الإجراءات',
    'invoice.status.cleared': 'مقبولة',
    'invoice.status.rejected': 'مرفوضة',
    'invoice.status.pending': 'قيد الانتظار',
    
    // Common
    'common.view': 'عرض',
    'common.edit': 'تعديل',
    'common.delete': 'حذف',
    'common.loading': 'جاري التحميل...',
    
    // Topbar
    'topbar.environment.sandbox': 'بيئة الاختبار',
    'topbar.environment.production': 'الإنتاج',
    'topbar.apiUsage': 'استخدام API',
    
    // System Status
    'system.status': 'حالة النظام',
    'system.zatca': 'ZATCA API',
    'system.ai': 'خدمة الذكاء الاصطناعي',
    'system.uptime': 'وقت التشغيل',
    'system.version': 'الإصدار',
    'system.lastChecked': 'آخر فحص',
    'system.connected': 'متصل',
    'system.disconnected': 'غير متصل',
    'system.enabled': 'مفعل',
    'system.disabled': 'معطل',
    'system.error': 'خطأ',
    
    // API Usage
    'usage.title': 'استخدام API',
    'usage.zatca': 'إرسالات ZATCA',
    'usage.ai': 'مكالمات الذكاء الاصطناعي',
    'usage.thisMonth': 'هذا الشهر',
    
    // Environment Banner
    'banner.sandbox': 'وضع التجربة',
    'banner.sandbox.desc': 'الفواتير غير صالحة قانونياً',
    'banner.production': 'وضع الإنتاج',
    'banner.production.desc': 'إرسالات ZATCA مباشرة',
    
    // Plans & Billing
    'plans.title': 'الخطط والأسعار',
    'plans.subtitle': 'اختر الخطة المناسبة لاحتياجاتك',
    'plans.choosePlan': 'اختر الخطة',
    'plans.upgrade': 'ترقية',
    'plans.getApiKey': 'احصل على API Key',
    'plans.needApiKey': 'تحتاج إلى API Key؟',
    'plans.contactUs': 'اتصل بنا للحصول على API Key والبدء في استخدام الخدمة',
    'plans.noPlans': 'لا توجد خطط متاحة',
    'plans.recommended': 'موصى به',
    'plans.currentPlan': 'الخطة الحالية',
    'plans.invoicesPerMonth': 'فواتير شهرياً',
    'plans.aiCallsPerMonth': 'مكالمات AI شهرياً',
    'plans.rateLimit': 'معدل الطلبات/دقيقة',
    'plans.features': 'المميزات',
    
    // Billing
    'billing.title': 'الفواتير والاشتراك',
    'billing.subtitle': 'إدارة اشتراكك واستخدامك',
    'billing.currentPlan': 'الخطة الحالية',
    'billing.billingPeriod': 'فترة الفوترة',
    'billing.invoiceUsage': 'استخدام الفواتير',
    'billing.aiUsage': 'استخدام AI',
    'billing.invoicesSent': 'الفواتير المرسلة',
    'billing.aiCalls': 'مكالمات AI',
    'billing.used': 'مستخدم',
    'billing.unlimited': 'غير محدود',
    'billing.noLimit': 'لا يوجد حد',
    'billing.limitExceeded': 'تم تجاوز الحد',
    'billing.rateLimit': 'معدل الطلبات',
    'billing.rateLimitDesc': 'يتم تطبيق الحدود حسب الخطة',
    'billing.upgradeTitle': 'ترقية خطتك',
    'billing.upgradeDesc': 'احصل على المزيد من الفواتير ومكالمات AI',
    'billing.viewPlans': 'عرض الخطط',
    'billing.noSubscription': 'لا يوجد اشتراك نشط',
    'billing.noSubscriptionDesc': 'اختر خطة للبدء في استخدام الخدمة',
    'billing.status.active': 'نشط',
    'billing.status.trial': 'تجريبي',
    'billing.status.expired': 'منتهي',
    'billing.status.suspended': 'معلق',
    'billing.trialDaysRemaining': 'أيام التجربة المتبقية',
    
    // Limit Banner
    'limitBanner.message': 'لقد وصلت إلى حد خطتك. قم بالترقية للمتابعة.',
    'limitBanner.message.invoice': 'لقد وصلت إلى حد الفواتير في خطتك. قم بالترقية للمتابعة.',
    'limitBanner.message.ai': 'لقد وصلت إلى حد AI في خطتك. قم بالترقية للمتابعة.',
    'limitBanner.message.both': 'لقد وصلت إلى حد خطتك في الفواتير و AI. قم بالترقية للمتابعة.',
    
    // Login
    'login.title': 'تسجيل الدخول',
    'login.subtitle': 'أدخل بياناتك للوصول إلى حسابك',
    'login.companyName': 'اسم الشركة (اختياري)',
    'login.email': 'البريد الإلكتروني (اختياري)',
    'login.apiKey': 'مفتاح API',
    'login.apiKeyPlaceholder': 'أدخل مفتاح API الخاص بك للوصول إلى لوحة التحكم',
    'login.verify': 'التحقق وتسجيل الدخول',
    'login.verifying': 'جاري التحقق...',
    'login.invalidApiKey': 'مفتاح API غير صالح',
    'login.enterApiKey': 'يرجى إدخال مفتاح API',
    'login.serverUnreachable': 'لا يمكن الوصول إلى الخادم. يرجى التحقق من الاتصال.',
    
    // Invoice Create
    'invoiceCreate.title': 'إنشاء فاتورة جديدة',
    'invoiceCreate.subtitle': 'املأ النموذج أدناه لإنشاء فاتورة جديدة',
    'invoiceCreate.phase': 'المرحلة',
    'invoiceCreate.environment': 'البيئة',
    'invoiceCreate.invoiceInfo': 'معلومات الفاتورة',
    'invoiceCreate.invoiceNumber': 'رقم الفاتورة',
    'invoiceCreate.invoiceDate': 'تاريخ الفاتورة',
    'invoiceCreate.invoiceType': 'نوع الفاتورة',
    'invoiceCreate.sellerInfo': 'معلومات البائع',
    'invoiceCreate.sellerName': 'اسم البائع',
    'invoiceCreate.sellerTaxNumber': 'الرقم الضريبي',
    'invoiceCreate.sellerAddress': 'عنوان البائع',
    'invoiceCreate.buyerInfo': 'معلومات المشتري',
    'invoiceCreate.buyerName': 'اسم المشتري',
    'invoiceCreate.buyerTaxNumber': 'الرقم الضريبي',
    'invoiceCreate.lineItems': 'عناصر الفاتورة',
    'invoiceCreate.addItem': '+ إضافة عنصر',
    'invoiceCreate.item': 'عنصر',
    'invoiceCreate.itemName': 'الاسم',
    'invoiceCreate.quantity': 'الكمية',
    'invoiceCreate.unitPrice': 'سعر الوحدة',
    'invoiceCreate.taxRate': 'نسبة الضريبة',
    'invoiceCreate.taxCategory': 'فئة الضريبة',
    'invoiceCreate.discount': 'الخصم',
    'invoiceCreate.remove': 'حذف',
    'invoiceCreate.totals': 'الإجماليات',
    'invoiceCreate.taxExclusive': 'قبل الضريبة',
    'invoiceCreate.taxAmount': 'مبلغ الضريبة',
    'invoiceCreate.totalAmount': 'المبلغ الإجمالي',
    'invoiceCreate.totalDiscount': 'إجمالي الخصم',
    'invoiceCreate.saveDraft': 'حفظ المسودة',
    'invoiceCreate.submit': 'إرسال إلى ZATCA',
    'invoiceCreate.submitting': 'جاري الإرسال...',
    'invoiceCreate.success': 'تم إنشاء الفاتورة بنجاح!',
    'invoiceCreate.error': 'فشل إنشاء الفاتورة. يرجى المحاولة مرة أخرى.',
    'invoiceCreate.required': 'مطلوب',
    'invoiceCreate.digits15': '15 رقم',
    'invoiceCreate.digits15Optional': '15 رقم (اختياري)',
    'invoiceCreate.validation.invoiceNumberRequired': 'رقم الفاتورة مطلوب',
    'invoiceCreate.validation.invoiceDateRequired': 'تاريخ الفاتورة مطلوب',
    'invoiceCreate.validation.sellerNameRequired': 'اسم البائع مطلوب',
    'invoiceCreate.validation.sellerTaxNumberRequired': 'الرقم الضريبي للبائع مطلوب',
    'invoiceCreate.validation.sellerTaxNumberLength': 'الرقم الضريبي يجب أن يكون 15 رقم',
    'invoiceCreate.validation.lineItemsRequired': 'يجب إضافة عنصر واحد على الأقل',
    'invoiceCreate.validation.itemNameRequired': 'اسم العنصر مطلوب',
    'invoiceCreate.validation.quantityRequired': 'الكمية يجب أن تكون أكبر من صفر',
    'invoiceCreate.validation.priceRequired': 'السعر يجب أن يكون أكبر من أو يساوي صفر',
    'invoiceCreate.validation.taxRateRequired': 'نسبة الضريبة يجب أن تكون بين 0 و 100',
    'invoiceCreate.validation.discountRequired': 'الخصم يجب أن يكون أكبر من أو يساوي صفر',
    
    // Invoice List
    'invoiceList.title': 'الفواتير',
    'invoiceList.total': 'إجمالي الفواتير',
    'invoiceList.createInvoice': '+ إنشاء فاتورة',
    'invoiceList.loading': 'جاري تحميل الفواتير...',
    'invoiceList.error': 'فشل تحميل الفواتير',
    'invoiceList.empty': 'لا توجد فواتير',
    'invoiceList.emptyDesc': 'قم بإنشاء أول فاتورة للبدء',
    'invoiceList.retry': 'إعادة المحاولة',
    'invoiceList.view': 'عرض',
    'invoiceList.phase1': 'المرحلة 1',
    'invoiceList.phase2': 'المرحلة 2',
    
    // Invoice Detail
    'invoiceDetail.title': 'تفاصيل الفاتورة',
    'invoiceDetail.back': 'العودة إلى الفواتير',
    'invoiceDetail.loading': 'جاري تحميل الفاتورة...',
    'invoiceDetail.error': 'فشل تحميل الفاتورة',
    'invoiceDetail.notFound': 'الفاتورة غير موجودة',
    'invoiceDetail.notFoundDesc': 'الفاتورة التي تبحث عنها غير موجودة',
    'invoiceDetail.summary': 'الملخص',
    'invoiceDetail.xml': 'XML',
    'invoiceDetail.response': 'استجابة ZATCA',
    'invoiceDetail.logs': 'سجلات المعالجة',
    'invoiceDetail.copy': 'نسخ',
    'invoiceDetail.copied': 'تم النسخ!',
    'invoiceDetail.download': 'تحميل',
    'invoiceDetail.explainError': 'شرح الخطأ',
    'invoiceDetail.predictRejection': 'توقع الرفض',
    'invoiceDetail.aiLoading': 'جاري تحميل شرح AI...',
    'invoiceDetail.aiError': 'فشل تحميل شرح AI',
    
    // Invoice Status
    'invoiceStatus.created': 'تم الإنشاء',
    'invoiceStatus.processing': 'قيد المعالجة',
    'invoiceStatus.cleared': 'تم الاعتماد',
    'invoiceStatus.rejected': 'مرفوض',
    'invoiceStatus.failed': 'فشل',
    
    // Playground
    'playground.title': 'ملعب API',
    'playground.subtitle': 'اختبر نقاط نهاية API بشكل تفاعلي',
    'playground.selectEndpoint': 'اختر نقطة نهاية للبدء',
    'playground.endpoint': 'نقطة النهاية',
    'playground.method': 'الطريقة',
    'playground.requestBody': 'نص الطلب',
    'playground.queryParams': 'معاملات الاستعلام',
    'playground.execute': 'تنفيذ',
    'playground.executing': 'جاري التنفيذ...',
    'playground.response': 'الاستجابة',
    'playground.copyCurl': 'نسخ cURL',
    'playground.templates': 'القوالب',
    'playground.loadTemplates': 'تحميل القوالب',
    
    // Common Actions
    'common.save': 'حفظ',
    'common.cancel': 'إلغاء',
    'common.close': 'إغلاق',
    'common.confirm': 'تأكيد',
    'common.retry': 'إعادة المحاولة',
    'common.back': 'رجوع',
    'common.next': 'التالي',
    'common.previous': 'السابق',
    'common.submit': 'إرسال',
    'common.reset': 'إعادة تعيين',
    'common.search': 'بحث',
    'common.filter': 'تصفية',
    'common.sort': 'ترتيب',
    'common.export': 'تصدير',
    'common.import': 'استيراد',
    'common.download': 'تحميل',
    'common.upload': 'رفع',
    'common.copy': 'نسخ',
    'common.copied': 'تم النسخ!',
    'common.select': 'اختر',
    'common.selectAll': 'تحديد الكل',
    'common.deselectAll': 'إلغاء تحديد الكل',
    'common.yes': 'نعم',
    'common.no': 'لا',
    'common.ok': 'موافق',
    'common.error': 'خطأ',
    'common.success': 'نجح',
    'common.warning': 'تحذير',
    'common.info': 'معلومات',
    'common.required': 'مطلوب',
    'common.optional': 'اختياري',
    'common.page': 'صفحة',
    'common.of': 'من',
    
    // Errors
    'error.generic': 'حدث خطأ',
    'error.network': 'خطأ في الشبكة. يرجى التحقق من الاتصال.',
    'error.unauthorized': 'غير مصرح. يرجى التحقق من مفتاح API الخاص بك.',
    'error.forbidden': 'الوصول محظور',
    'error.notFound': 'المورد غير موجود',
    'error.serverError': 'خطأ في الخادم. يرجى المحاولة مرة أخرى لاحقًا.',
    'error.validation': 'خطأ في التحقق',
    'error.timeout': 'انتهت مهلة الطلب. يرجى المحاولة مرة أخرى.',
    
    // Invoice Create - Additional
    'invoiceCreate.item': 'عنصر',
    'invoiceCreate.subtotal': 'المجموع الفرعي',
    'invoiceCreate.tax': 'الضريبة',
    'invoiceCreate.total': 'المجموع',
    'invoiceCreate.invoiceSummary': 'ملخص الفاتورة',
    'invoiceCreate.subtotalExclTax': 'المجموع قبل الضريبة',
    'invoiceCreate.totalDiscount': 'إجمالي الخصم',
    'invoiceCreate.totalTax': 'إجمالي الضريبة',
    'invoiceCreate.totalAmount': 'المجموع الكلي',
    'invoiceCreate.processingResult': 'نتيجة المعالجة',
    'invoiceCreate.success': 'نجح',
    'invoiceCreate.failed': 'فشل',
    'invoiceCreate.qrCode': 'رمز QR',
    'invoiceCreate.errors': 'الأخطاء',
    'invoiceCreate.createAnother': 'إنشاء فاتورة أخرى',
    'invoiceCreate.viewAllInvoices': 'عرض جميع الفواتير',
    'invoiceCreate.processing': 'جاري المعالجة...',
    'invoiceCreate.category': 'الفئة',
    'invoiceCreate.currency': 'ريال',
    
    // Invoice Detail - Additional
    'invoiceDetail.summary': 'الملخص',
    'invoiceDetail.requestJson': 'طلب JSON',
    'invoiceDetail.zatcaResponse': 'استجابة ZATCA',
    'invoiceDetail.troubleshooting': 'استكشاف الأخطاء',
    'invoiceDetail.responseCode': 'رمز الاستجابة',
    'invoiceDetail.createdAt': 'تاريخ الإنشاء',
    'invoiceDetail.originalRequest': 'بيانات الطلب الأصلية',
    'invoiceDetail.downloadJson': 'تحميل JSON',
    'invoiceDetail.requestNotAvailable': 'بيانات الطلب الأصلية غير متوفرة في سجل الفاتورة. يتم عرض البيانات المتاحة فقط.',
    'invoiceDetail.generatedXml': 'محتوى XML المولد',
    'invoiceDetail.downloadXml': 'تحميل XML',
    'invoiceDetail.xmlNotAvailable': 'محتوى XML غير متوفر',
    'invoiceDetail.xmlNotStored': 'XML غير مخزن في سجل الفاتورة. قد يكون متوفراً عند إنشاء الفاتورة فقط.',
    'invoiceDetail.invalidQr': 'QR غير صالح',
    'invoiceDetail.copyQr': 'نسخ QR',
    'invoiceDetail.explainError': 'شرح الخطأ',
    'invoiceDetail.predictRejection': 'التنبؤ بالرفض',
    'invoiceDetail.processing': 'جاري المعالجة...',
    
    // Playground - Additional
    'playground.requestConfig': 'إعدادات الطلب',
    'playground.hide': 'إخفاء',
    'playground.show': 'إظهار',
    'playground.templates': 'القوالب',
    'playground.queryParamsOptional': 'معاملات الاستعلام (اختياري)',
    'playground.productionConfirm': 'أؤكد أن هذا إجراء إنتاج',
    'playground.productionWarning': 'تتطلب عمليات الكتابة في الإنتاج تأكيداً صريحاً.',
    'playground.executing': 'جاري التنفيذ...',
    'playground.executeRequest': 'تنفيذ الطلب',
    'playground.curlCommand': 'أمر cURL',
    'playground.response': 'الاستجابة',
    'playground.testEndpoints': 'اختبر نقاط نهاية API بشكل تفاعلي. جميع الطلبات تستخدم مفتاح API الخاص بك تلقائياً.',
    'playground.selectEndpointDesc': 'اختر نقطة نهاية من القائمة أعلاه أو استخدم قالب للبدء',
    
    // Billing - Additional
    'billing.changePlan': 'تغيير الخطة',
    'billing.changePlanDesc': 'سيتم توجيهك إلى صفحة الخطط حيث يمكنك اختيار خطة جديدة. سيتم تطبيق التغييرات على اشتراكك الحالي.',
    'billing.continue': 'متابعة',
    'billing.invoicesSent': 'الفواتير المرسلة',
    'billing.aiCalls': 'مكالمات AI',
    
    // Dashboard - Additional
    'dashboard.subtitle': 'نظرة عامة على أداء الفواتير والامتثال',
    
    // Plans
    'plans.viewPlans': 'عرض الخطط',
    'plans.sandboxNote': 'الوصول إلى بيئة التجربة مجاني. بيئة الإنتاج تتطلب خطة نشطة.',
    'plans.inquiries': 'للاستفسارات:',
    'plans.contactSales': 'تواصل مع المبيعات',
    
    // Topbar
    'topbar.apiKeySession': 'جلسة API',
    'topbar.logout': 'تسجيل الخروج',
    
    // Invoice Detail - Additional
    'invoiceDetail.title': 'تفاصيل الفاتورة',
    'invoiceDetail.notFound': 'فاتورة غير موجودة',
    'invoiceDetail.notFoundDesc': 'الفاتورة المطلوبة غير موجودة',
    'invoiceDetail.back': 'العودة إلى الفواتير',
    'invoiceDetail.error': 'فشل تحميل الفاتورة',
    'invoiceDetail.aiError': 'فشل معالجة طلب AI',
  },
};

interface LanguageProviderProps {
  children: ReactNode;
}

export const LanguageProvider: React.FC<LanguageProviderProps> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('language') as Language;
    if (saved) return saved;
    // Detect browser language - default to Arabic if browser is Arabic
    const browserLang = navigator.language || (navigator as any).userLanguage || 'en';
    return browserLang.startsWith('ar') ? 'ar' : 'en';
  });

  const direction: Direction = language === 'ar' ? 'rtl' : 'ltr';

  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = language;
    
    // Apply font based on language
    if (language === 'ar') {
      document.documentElement.style.fontFamily = 'Cairo, Tajawal, sans-serif';
    } else {
      document.documentElement.style.fontFamily = 'Inter, sans-serif';
    }
  }, [language, direction]);

  const toggleLanguage = () => {
    const newLang = language === 'en' ? 'ar' : 'en';
    setLanguageState(newLang);
    localStorage.setItem('language', newLang);
  };

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('language', lang);
  };

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, direction, toggleLanguage, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

