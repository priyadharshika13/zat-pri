export type InvoiceStatus = 'cleared' | 'rejected' | 'pending' | 'SUBMITTED' | 'CLEARED' | 'REJECTED' | 'ERROR';
export type InvoicePhase = 1 | 2 | 'PHASE_1' | 'PHASE_2';
export type Environment = 'sandbox' | 'production' | 'SANDBOX' | 'PRODUCTION';
export type InvoiceMode = 'PHASE_1' | 'PHASE_2';

export interface Invoice {
  id: string;
  invoiceNumber: string;
  phase: InvoicePhase;
  status: InvoiceStatus;
  date: string;
  sellerName: string;
  buyerName?: string;
  totalAmount: number;
  taxAmount: number;
  environment: Environment;
  uuid?: string;
  qrCodeData?: string;
  errors?: string[];
}

// Invoice Request/Response types matching backend schemas
export interface LineItem {
  name: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  tax_category: string;
  discount?: number;
}

export interface InvoiceRequest {
  mode: InvoiceMode;
  environment: 'SANDBOX' | 'PRODUCTION';
  invoice_number: string;
  invoice_date: string; // ISO datetime string
  invoice_type?: string;
  seller_name: string;
  seller_tax_number: string;
  seller_address?: string;
  buyer_name?: string;
  buyer_tax_number?: string;
  line_items: LineItem[];
  total_discount?: number;
  total_tax_exclusive: number;
  total_tax_amount: number;
  total_amount: number;
  uuid?: string;
  previous_invoice_hash?: string;
}

export interface QRCodeData {
  seller_name: string;
  seller_tax_number: string;
  invoice_date: string;
  invoice_total: number;
  invoice_tax: number;
  qr_code: string;
}

export interface XMLData {
  xml_content: string;
  signed_xml?: string;
}

export interface ClearanceResponse {
  status: string;
  uuid?: string;
  qr_code?: string;
  reporting_status?: string;
}

export interface InvoiceResponse {
  success: boolean;
  invoice_number: string;
  mode: InvoiceMode;
  environment: 'SANDBOX' | 'PRODUCTION';
  qr_code_data?: QRCodeData;
  xml_data?: XMLData;
  clearance?: ClearanceResponse;
  processed_at: string; // ISO datetime string
  errors?: string[];
  validation_result?: unknown;
}

export interface DashboardStats {
  totalInvoices: number;
  cleared: number;
  rejected: number;
  pending: number;
  aiPredictionsUsed: number;
}

export interface AIInsight {
  id: string;
  type: 'prediction' | 'precheck' | 'root_cause' | 'readiness' | 'trend';
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  timestamp: string;
}

