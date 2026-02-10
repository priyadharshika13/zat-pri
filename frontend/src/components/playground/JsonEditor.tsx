import React, { useState, useEffect } from 'react';
import { CodeBlock } from '../common/CodeBlock';

interface JsonEditorProps {
  value: Record<string, unknown> | null;
  onChange: (value: Record<string, unknown> | null) => void;
  placeholder?: string;
  readOnly?: boolean;
  className?: string;
}

export const JsonEditor: React.FC<JsonEditorProps> = ({
  value,
  onChange,
  placeholder = '{}',
  readOnly = false,
  className = '',
}) => {
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (value) {
      try {
        setText(JSON.stringify(value, null, 2));
        setError(null);
      } catch {
        setText('');
        setError('Invalid JSON');
      }
    } else {
      setText('');
    }
  }, [value]);

  const handleChange = (newText: string) => {
    setText(newText);
    setError(null);

    if (!newText.trim()) {
      onChange(null);
      return;
    }

    try {
      const parsed = JSON.parse(newText);
      onChange(parsed);
    } catch (e) {
      setError('Invalid JSON');
      // Still allow typing, but mark as error
    }
  };

  if (readOnly) {
    return (
      <div className={className}>
        <CodeBlock
          content={text || placeholder}
          language="json"
        />
      </div>
    );
  }

  return (
    <div className={className}>
      <textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full h-64 font-mono text-sm p-4 border rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          error ? 'border-red-500' : 'border-gray-300'
        }`}
        spellCheck={false}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
};

