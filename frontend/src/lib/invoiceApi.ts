/**
 * Invoice API functions.
 * 
 * Typed functions for invoice operations.
 */

import { apiGet, apiPost } from './api';
import { InvoiceRequest, InvoiceResponse } from '../types/invoice';
import { InvoiceListResponse, InvoiceDetailResponse } from '../types/invoiceHistory';

/**
 * Creates/processes an invoice.
 */
export const createInvoice = async (data: InvoiceRequest): Promise<InvoiceResponse> => {
  return apiPost<InvoiceResponse>('/api/v1/invoices', data);
};

/**
 * Lists invoices with pagination and filters.
 */
export const listInvoices = async (params?: {
  page?: number;
  limit?: number;
  invoice_number?: string;
  status?: string;
  environment?: string;
  date_from?: string;
  date_to?: string;
}): Promise<InvoiceListResponse> => {
  const queryParams = new URLSearchParams();
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.invoice_number) queryParams.append('invoice_number', params.invoice_number);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.environment) queryParams.append('environment', params.environment);
  if (params?.date_from) queryParams.append('date_from', params.date_from);
  if (params?.date_to) queryParams.append('date_to', params.date_to);

  const query = queryParams.toString();
  return apiGet<InvoiceListResponse>(`/api/v1/invoices${query ? `?${query}` : ''}`);
};

/**
 * Gets invoice details by ID.
 */
export const getInvoice = async (invoiceId: number): Promise<InvoiceDetailResponse> => {
  return apiGet<InvoiceDetailResponse>(`/api/v1/invoices/${invoiceId}`);
};

