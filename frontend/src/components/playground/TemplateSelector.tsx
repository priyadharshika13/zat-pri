import React from 'react';
import { RequestTemplate } from '../../lib/playgroundApi';

interface TemplateSelectorProps {
  templates: Record<string, RequestTemplate>;
  onSelect: (template: RequestTemplate) => void;
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({ templates, onSelect }) => {
  const templateList = Object.entries(templates).map(([key, template]) => ({
    key,
    ...template,
  }));

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Quick Templates</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {templateList.map((template) => (
          <button
            key={template.key}
            onClick={() => onSelect(template)}
            className="w-full text-left p-3 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-2 py-1 bg-gray-100 rounded">
                    {template.method}
                  </span>
                  <span className="font-medium text-gray-900">{template.name}</span>
                  {template.requires_production_confirmation && (
                    <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                      Production
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-1">{template.description}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

