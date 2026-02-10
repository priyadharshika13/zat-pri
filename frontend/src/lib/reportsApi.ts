/**
 * Reports API functions.
 * Used for dashboard stats and reports page.
 */

import { apiGet } from './api';

export interface StatusBreakdownItem {
  status: string;
  count: number;
}

export interface StatusBreakdownResponse {
  breakdown: StatusBreakdownItem[];
  total_invoices: number;
}

export interface RevenueSummaryResponse {
  total_revenue: number;
  total_tax: number;
  net_revenue: number;
  cleared_invoice_count: number;
  total_invoice_count: number;
}

export interface InvoiceReportItem {
  invoice_number: string;
  status: string;
  phase: string;
  total_amount: number;
  tax_amount: number;
  created_at: string;
}

export interface InvoiceReportResponse {
  invoices: InvoiceReportItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface VATSummaryItem {
  date: string;
  total_tax_amount: number;
  total_invoice_amount: number;
  invoice_count: number;
}

export interface VATSummaryResponse {
  summary: VATSummaryItem[];
  total_tax_amount: number;
  total_invoice_amount: number;
  total_invoice_count: number;
  date_from: string | null;
  date_to: string | null;
  group_by: string;
}

export const getStatusBreakdown = async (): Promise<StatusBreakdownResponse> => {
  return apiGet<StatusBreakdownResponse>('/api/v1/reports/status-breakdown');
};

export const getRevenueSummary = async (): Promise<RevenueSummaryResponse> => {
  return apiGet<RevenueSummaryResponse>('/api/v1/reports/revenue-summary');
};

export const getInvoiceReport = async (params?: {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  status?: string;
  phase?: string;
}): Promise<InvoiceReportResponse> => {
  const queryParams = new URLSearchParams();
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.date_from) queryParams.append('date_from', params.date_from);
  if (params?.date_to) queryParams.append('date_to', params.date_to);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.phase) queryParams.append('phase', params.phase);
  const query = queryParams.toString();
  return apiGet<InvoiceReportResponse>(`/api/v1/reports/invoices${query ? `?${query}` : ''}`);
};

export const getVATSummary = async (params?: {
  date_from?: string;
  date_to?: string;
  group_by?: 'day' | 'month';
}): Promise<VATSummaryResponse> => {
  const queryParams = new URLSearchParams();
  if (params?.date_from) queryParams.append('date_from', params.date_from);
  if (params?.date_to) queryParams.append('date_to', params.date_to);
  if (params?.group_by) queryParams.append('group_by', params.group_by);
  const query = queryParams.toString();
  return apiGet<VATSummaryResponse>(`/api/v1/reports/vat-summary${query ? `?${query}` : ''}`);
};
