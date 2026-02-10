/**
 * Invoice history type definitions.
 * 
 * Matches backend InvoiceListResponse and InvoiceDetailResponse schemas.
 */

export type InvoiceStatus = 'SUBMITTED' | 'CLEARED' | 'REJECTED' | 'ERROR';

export interface InvoiceListItem {
  id: number;
  invoice_number: string;
  uuid?: string | null;
  hash?: string | null;
  environment: string;
  status: InvoiceStatus;
  zatca_response_code?: string | null;
  created_at: string; // ISO datetime string
}

export interface InvoiceListResponse {
  invoices: InvoiceListItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface InvoiceDetailResponse {
  id: number;
  invoice_number: string;
  uuid?: string | null;
  hash?: string | null;
  environment: string;
  status: InvoiceStatus;
  zatca_response_code?: string | null;
  created_at: string; // ISO datetime string
  phase?: 'PHASE_1' | 'PHASE_2' | null;
  // Note: Request payload, XML, and full ZATCA response are not stored in backend
  // These fields are optional and may be populated if backend is extended
  request_payload?: Record<string, unknown> | null;
  xml_content?: string | null;
  zatca_response?: Record<string, unknown> | null;
  qr_code_data?: string | null; // Base64 QR code image
}

