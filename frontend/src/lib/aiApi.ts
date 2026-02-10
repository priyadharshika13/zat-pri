/**
 * AI API functions.
 * 
 * Typed functions for AI-powered endpoints.
 */

import { apiPost } from './api';

export interface ErrorExplanationRequest {
  error_code?: string;
  error_message?: string;
  error_response?: Record<string, unknown>;
  use_ai?: boolean;
  include_arabic?: boolean;
}

export interface ErrorExplanationResponse {
  error_code: string;
  original_error?: string | null;
  human_explanation: string;
  technical_reason: string;
  fix_suggestion: string;
  ai_english_explanation?: string | null;
  ai_arabic_explanation?: string | null;
  ai_fix_steps?: string[] | null;
}

export interface RejectionPredictionRequest {
  invoice_payload: Record<string, unknown>;
  environment: 'SANDBOX' | 'PRODUCTION';
}

export interface RejectionPredictionResponse {
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN';
  confidence: number;
  likely_reasons?: string[];
  advisory_note: string;
}

/**
 * Explains a ZATCA error.
 */
export const explainError = async (
  data: ErrorExplanationRequest
): Promise<ErrorExplanationResponse> => {
  return apiPost<ErrorExplanationResponse>('/api/v1/errors/explain', data);
};

/**
 * Predicts invoice rejection risk.
 */
export const predictRejection = async (
  data: RejectionPredictionRequest
): Promise<RejectionPredictionResponse> => {
  return apiPost<RejectionPredictionResponse>('/api/v1/ai/predict-rejection', data);
};

