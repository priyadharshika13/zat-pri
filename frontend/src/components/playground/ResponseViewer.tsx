import React from 'react';
import { CodeBlock } from '../common/CodeBlock';
import { Badge } from '../common/Badge';

interface ResponseViewerProps {
  response: {
    status_code: number;
    headers: Record<string, string>;
    body: unknown;
    latency_ms: number;
    timestamp: string;
  } | null;
  onCopy?: () => void;
}

export const ResponseViewer: React.FC<ResponseViewerProps> = ({ response, onCopy }) => {
  if (!response) {
    return (
      <div className="border border-slate-200 rounded-lg p-6 bg-slate-50 text-center text-slate-500" data-testid="response-empty-state">
        <svg
          className="w-12 h-12 text-slate-400 mx-auto mb-2"
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
        <p>No response yet. Execute a request to see results here.</p>
      </div>
    );
  }

  const isSuccess = response.status_code >= 200 && response.status_code < 300;
  const isError = response.status_code >= 400;

  const statusColor = isSuccess
    ? 'bg-green-100 text-green-800'
    : isError
    ? 'bg-red-100 text-red-800'
    : 'bg-yellow-100 text-yellow-800';

  const bodyText = typeof response.body === 'string'
    ? response.body
    : JSON.stringify(response.body, null, 2);

  return (
    <div className="space-y-4" data-testid="response-viewer">
      {/* Status and Metadata */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge className={statusColor} data-testid="response-status">
            {response.status_code} {getStatusText(response.status_code)}
          </Badge>
          <span className="text-sm text-slate-600">
            {response.latency_ms.toFixed(0)} ms
          </span>
          <span className="text-sm text-slate-500">
            {new Date(response.timestamp).toLocaleTimeString()}
          </span>
        </div>
        {onCopy && (
          <button
            onClick={onCopy}
            className="text-sm text-emerald-600 hover:text-emerald-800 font-medium"
            data-testid="copy-response-button"
          >
            Copy Response
          </button>
        )}
      </div>

      {/* Headers */}
      {Object.keys(response.headers).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-700 mb-2">Headers</h4>
          <CodeBlock
            content={JSON.stringify(response.headers, null, 2)}
            language="json"
          />
        </div>
      )}

      {/* Body */}
      <div>
        <h4 className="text-sm font-semibold text-slate-700 mb-2">Response Body</h4>
        <CodeBlock
          content={bodyText}
          language="json"
        />
      </div>
    </div>
  );
};

function getStatusText(status: number): string {
  const statusTexts: Record<number, string> = {
    200: 'OK',
    201: 'Created',
    204: 'No Content',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
  };
  return statusTexts[status] || 'Unknown';
}

