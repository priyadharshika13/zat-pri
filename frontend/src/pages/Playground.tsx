import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { EmptyState } from '../components/common/EmptyState';
import { EndpointSelector, Endpoint } from '../components/playground/EndpointSelector';
import { TemplateSelector } from '../components/playground/TemplateSelector';
import { JsonEditor } from '../components/playground/JsonEditor';
import { ResponseViewer } from '../components/playground/ResponseViewer';
import { getTemplates, executePlaygroundRequest, generateCurlCommand, PlaygroundRequest, PlaygroundResponse } from '../lib/playgroundApi';
import { getApiKey } from '../lib/auth';
import { useLanguage } from '../context/LanguageContext';

export const Playground: React.FC = () => {
  const { direction, t } = useLanguage();
  const [endpoint, setEndpoint] = useState<Endpoint | null>(null);
  const [method, setMethod] = useState<string>('GET');
  const [requestBody, setRequestBody] = useState<Record<string, unknown> | null>(null);
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<PlaygroundResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<Record<string, any>>({});
  const [showTemplates, setShowTemplates] = useState(true);
  const [confirmProduction, setConfirmProduction] = useState(false);
  const [curlCommand, setCurlCommand] = useState<string>('');

  const loadTemplates = useCallback(async () => {
    try {
      const data = await getTemplates();
      setTemplates(data);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  }, []);

  const updateCurlCommand = useCallback(() => {
    if (!endpoint) return;
    const apiKey = getApiKey() || 'YOUR_API_KEY';
    const request: PlaygroundRequest = {
      endpoint: endpoint.path,
      method: method,
      body: requestBody || undefined,
      query_params: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    };
    setCurlCommand(generateCurlCommand(request, apiKey));
  }, [endpoint, method, requestBody, queryParams]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    if (endpoint) {
      setMethod(endpoint.method);
      updateCurlCommand();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint, updateCurlCommand]);

  const handleTemplateSelect = (template: any) => {
    setEndpoint({
      path: template.endpoint,
      method: template.method,
      name: template.name,
      description: template.description,
      category: 'invoices',
    });
    setMethod(template.method);
    setRequestBody(template.body || null);
    setQueryParams(template.query_params || {});
    setConfirmProduction(template.requires_production_confirmation);
    setShowTemplates(false);
  };

  const handleEndpointSelect = (selectedEndpoint: Endpoint) => {
    setEndpoint(selectedEndpoint);
    setMethod(selectedEndpoint.method);
    // Reset body for GET requests
    if (selectedEndpoint.method === 'GET') {
      setRequestBody(null);
    }
    setShowTemplates(false);
  };

  const handleExecute = async () => {
    if (!endpoint) return;

    setLoading(true);
    setResponse(null);

    try {
      const request: PlaygroundRequest = {
        endpoint: endpoint.path,
        method: method,
        body: requestBody || undefined,
        query_params: Object.keys(queryParams).length > 0 ? queryParams : undefined,
        confirm_production: confirmProduction,
      };

      const result = await executePlaygroundRequest(request);
      setResponse(result);
    } catch (error: any) {
      // Create error response
      setResponse({
        status_code: error.status || 500,
        headers: {},
        body: error.detail || { error: error.message || 'Request failed' },
        latency_ms: 0,
        timestamp: new Date().toISOString(),
        source: 'api_playground',
      });
    } finally {
      setLoading(false);
    }
  };


  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const isWriteOperation = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase());
  const requiresProductionConfirmation = requestBody?.environment === 'PRODUCTION' && isWriteOperation;

  return (
    <div className="space-y-6" dir={direction} data-testid="api-playground-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          {t('playground.title')}
        </h1>
        <p className="text-slate-600 mt-1">
          {t('playground.testEndpoints')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Request Configuration */}
        <div className="space-y-6">
          <Card padding="lg">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">
                  {t('playground.requestConfig')}
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowTemplates(!showTemplates)}
                  data-testid="toggle-templates-button"
                >
                  {showTemplates ? t('playground.hide') : t('playground.show')} {t('playground.templates')}
                </Button>
              </div>

              {showTemplates && Object.keys(templates).length > 0 && (
                <div className="border-t border-slate-200 pt-4">
                  <TemplateSelector
                    templates={templates}
                    onSelect={handleTemplateSelect}
                  />
                </div>
              )}

              <div className={showTemplates && Object.keys(templates).length > 0 ? 'border-t border-slate-200 pt-4' : ''}>
                <EndpointSelector
                  value={endpoint}
                  onChange={handleEndpointSelect}
                />
              </div>

              {!endpoint && (
                <div className="pt-4">
                  <EmptyState
                    icon={
                      <svg
                        className="w-12 h-12 text-slate-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                        />
                      </svg>
                    }
                    title={t('playground.selectEndpoint')}
                    description={t('playground.selectEndpointDesc')}
                    className="py-8"
                  />
                </div>
              )}

              {endpoint && (
                <>
                  {/* Query Parameters */}
                  {method === 'GET' && (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-slate-700">
                        {t('playground.queryParamsOptional')}
                      </label>
                      <JsonEditor
                        value={queryParams}
                        onChange={(val) => {
                          if (val) {
                            // Convert Record<string, unknown> to Record<string, string>
                            const converted: Record<string, string> = {};
                            for (const [key, value] of Object.entries(val)) {
                              converted[key] = String(value);
                            }
                            setQueryParams(converted);
                          } else {
                            setQueryParams({});
                          }
                        }}
                        placeholder='{"key": "value"}'
                      />
                    </div>
                  )}

                  {/* Request Body */}
                  {isWriteOperation && (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-slate-700">
                        {t('playground.requestBody')}
                      </label>
                      <JsonEditor
                        value={requestBody}
                        onChange={setRequestBody}
                        placeholder='{"key": "value"}'
                      />
                    </div>
                  )}

                  {/* Production Confirmation */}
                  {requiresProductionConfirmation && (
                    <div className="border border-amber-300 bg-amber-50 rounded-lg p-4" data-testid="production-warning">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={confirmProduction}
                          onChange={(e) => setConfirmProduction(e.target.checked)}
                          className="rounded"
                          data-testid="production-confirm-checkbox"
                        />
                        <span className="text-sm font-medium text-amber-800">
                          {t('playground.productionConfirm')}
                        </span>
                      </label>
                      <p className="text-xs text-amber-700 mt-1">
                        {t('playground.productionWarning')}
                      </p>
                    </div>
                  )}

                  {/* Execute Button */}
                  <Button
                    onClick={handleExecute}
                    disabled={loading || (requiresProductionConfirmation && !confirmProduction)}
                    className="w-full"
                    isLoading={loading}
                    data-testid="execute-request-button"
                  >
                    {loading ? t('playground.executing') : t('playground.executeRequest')}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {/* cURL Command */}
          {endpoint && curlCommand && (
            <Card padding="lg">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-700">
                    {t('playground.curlCommand')}
                  </h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(curlCommand)}
                    data-testid="copy-curl-button"
                  >
                    {t('common.copy')}
                  </Button>
                </div>
                <pre className="text-xs bg-slate-50 p-3 rounded border border-slate-200 overflow-x-auto font-mono">
                  {curlCommand}
                </pre>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Response */}
        <div>
          <Card padding="lg">
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">
                {t('playground.response')}
              </h2>
              <ResponseViewer
                response={response}
                onCopy={() => response && copyToClipboard(JSON.stringify(response.body, null, 2))}
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

