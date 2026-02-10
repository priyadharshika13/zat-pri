import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';

interface CodeBlockProps {
  content: string;
  language?: string;
  filename?: string;
  onDownload?: () => void;
  showCopy?: boolean;
  maxHeight?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  content,
  language,
  filename,
  onDownload,
  showCopy = true,
  maxHeight = '500px',
}) => {
  const { direction } = useLanguage();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    if (onDownload) {
      onDownload();
    } else if (filename) {
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="relative" dir={direction}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-100 border-b border-slate-200 rounded-t-lg">
        <div className="flex items-center gap-2">
          {language && (
            <span className="text-xs font-medium text-slate-600 uppercase">{language}</span>
          )}
          {filename && (
            <span className="text-xs text-slate-500 font-mono">{filename}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onDownload || filename ? (
            <button
              onClick={handleDownload}
              className="px-2 py-1 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded transition-colors"
              title={direction === 'rtl' ? 'تحميل' : 'Download'}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
          ) : null}
          {showCopy && (
            <button
              onClick={handleCopy}
              className="px-2 py-1 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded transition-colors"
              title={copied ? (direction === 'rtl' ? 'تم النسخ' : 'Copied!') : (direction === 'rtl' ? 'نسخ' : 'Copy')}
            >
              {copied ? (
                <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Code Content */}
      <div
        className="bg-slate-900 text-slate-100 p-4 rounded-b-lg overflow-auto"
        style={{ maxHeight }}
      >
        <pre className="text-xs font-mono whitespace-pre-wrap break-words">
          <code>{content}</code>
        </pre>
      </div>
    </div>
  );
};

