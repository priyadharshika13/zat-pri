import React, { useState, FormEvent, useEffect } from 'react';
import { useNavigate, Navigate, useLocation } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { useLanguage } from '../context/LanguageContext';
import { API_BASE_URL } from '../lib/api';
import { setApiKey as setStoredApiKey, setUserData, isAuthed } from '../lib/auth';
import { Loader } from '../components/common/Loader';

export const Login: React.FC = () => {
  const { direction, t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serverReachable, setServerReachable] = useState<boolean | null>(null);

  // Redirect if already authenticated - use Navigate component for immediate redirect
  // This prevents the component from rendering if user is already authenticated
  const from = (location.state as any)?.from?.pathname || '/dashboard';
  
  if (isAuthed()) {
    return <Navigate to={from} replace />;
  }

  // Check server reachability on mount
  useEffect(() => {
    const checkServer = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/system/health`);
        setServerReachable(response.ok);
      } catch {
        setServerReachable(false);
      }
    };
    checkServer();
  }, []);

  const handleVerify = async () => {
    if (!apiKey.trim()) {
      setError(t('login.enterApiKey'));
      return;
    }

    setError(null);
    setVerifying(true);

    try {
      // First verify server is reachable
      const healthResponse = await fetch(`${API_BASE_URL}/api/v1/system/health`);
      if (!healthResponse.ok) {
        throw new Error('Server unreachable');
      }

      // Then verify API key by calling authenticated endpoint
      const response = await fetch(`${API_BASE_URL}/api/v1/plans/usage`, {
        headers: {
          'X-API-Key': apiKey,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error(t('login.invalidApiKey'));
        }
        throw new Error(`HTTP ${response.status}`);
      }

      // API key is valid - store it and redirect
      setStoredApiKey(apiKey);
      setUserData({
        email: email || undefined,
        company_name: companyName || undefined,
      });

      // Redirect to dashboard
      navigate('/dashboard');
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : t('login.invalidApiKey');
      setError(errorMessage);
    } finally {
      setVerifying(false);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    await handleVerify();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4" dir={direction} data-testid="login-page">
      <Card className="w-full max-w-md" padding="lg">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            {t('login.title')}
          </h1>
          <p className="text-slate-600 text-sm">
            {t('login.subtitle')}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {serverReachable === false && (
          <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
            <p className="text-sm text-amber-800">
              {t('login.serverUnreachable')}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="companyName" className="block text-sm font-medium text-slate-700 mb-1">
              {t('login.companyName')}
            </label>
            <input
              id="companyName"
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              disabled={verifying}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
              placeholder={direction === 'rtl' ? 'اسم الشركة' : 'Company Name'}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
              {t('login.email')}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={verifying}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
              placeholder={direction === 'rtl' ? 'example@company.com' : 'example@company.com'}
            />
          </div>

          <div>
            <label htmlFor="apiKey" className="block text-sm font-medium text-slate-700 mb-1">
              {t('login.apiKey')} <span className="text-red-500">*</span>
            </label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              disabled={verifying}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed font-mono text-sm"
              placeholder="sk-..."
            />
            <p className="text-xs text-slate-500 mt-1">
              {t('login.apiKeyPlaceholder')}
            </p>
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full"
            disabled={verifying || !apiKey.trim()}
          >
            {verifying ? (
              <div className="flex items-center justify-center gap-2">
                <Loader size="sm" />
                <span>{t('login.verifying')}</span>
              </div>
            ) : (
              t('login.verify')
            )}
          </Button>
        </form>
      </Card>
    </div>
  );
};

