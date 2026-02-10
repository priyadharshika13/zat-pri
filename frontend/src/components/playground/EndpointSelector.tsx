import React from 'react';

export interface Endpoint {
  path: string;
  method: string;
  name: string;
  description: string;
  category: 'invoices' | 'ai' | 'plans' | 'health' | 'system';
}

const AVAILABLE_ENDPOINTS: Endpoint[] = [
  {
    path: '/api/v1/invoices',
    method: 'POST',
    name: 'Process Invoice',
    description: 'Submit invoice for ZATCA compliance (Phase 1 or Phase 2)',
    category: 'invoices',
  },
  {
    path: '/api/v1/invoices',
    method: 'GET',
    name: 'List Invoices',
    description: 'Get list of processed invoices',
    category: 'invoices',
  },
  {
    path: '/api/v1/ai/readiness-score',
    method: 'GET',
    name: 'AI Readiness Score',
    description: 'Get ZATCA compliance readiness score using AI',
    category: 'ai',
  },
  {
    path: '/api/v1/ai/explain-zatca-error',
    method: 'POST',
    name: 'AI Error Explanation',
    description: 'Get AI-powered explanation for ZATCA error code',
    category: 'ai',
  },
  {
    path: '/api/v1/ai/precheck-advisor',
    method: 'POST',
    name: 'AI Pre-check Advisor',
    description: 'Get AI-powered pre-check analysis for invoice',
    category: 'ai',
  },
  {
    path: '/api/v1/plans/current',
    method: 'GET',
    name: 'Get Current Subscription',
    description: 'Get current subscription details and limits',
    category: 'plans',
  },
  {
    path: '/api/v1/plans/usage',
    method: 'GET',
    name: 'Get Usage Summary',
    description: 'Get current usage statistics',
    category: 'plans',
  },
  {
    path: '/api/v1/health',
    method: 'GET',
    name: 'Health Check',
    description: 'Check API health and system status',
    category: 'health',
  },
];

interface EndpointSelectorProps {
  value: Endpoint | null;
  onChange: (endpoint: Endpoint) => void;
}

export const EndpointSelector: React.FC<EndpointSelectorProps> = ({ value, onChange }) => {
  const [category, setCategory] = React.useState<string>('all');

  const categories = ['all', ...new Set(AVAILABLE_ENDPOINTS.map(e => e.category))];

  const filteredEndpoints = category === 'all'
    ? AVAILABLE_ENDPOINTS
    : AVAILABLE_ENDPOINTS.filter(e => e.category === category);

  return (
    <div className="space-y-4" data-testid="endpoint-selector">
      {/* Category Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Category
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Endpoint List */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Endpoint
        </label>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {filteredEndpoints.map((endpoint) => (
            <button
              key={`${endpoint.method}-${endpoint.path}`}
              onClick={() => onChange(endpoint)}
              className={`w-full text-left p-3 border rounded-lg transition-colors ${
                value?.path === endpoint.path && value?.method === endpoint.method
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-1 bg-gray-100 rounded">
                      {endpoint.method}
                    </span>
                    <span className="font-medium text-gray-900">{endpoint.name}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{endpoint.description}</p>
                  <p className="text-xs text-gray-500 mt-1 font-mono">{endpoint.path}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export { AVAILABLE_ENDPOINTS };

