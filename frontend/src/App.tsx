import React, { useState } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { PageWrapper } from './components/layout/PageWrapper';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { RootRedirect } from './components/auth/RootRedirect';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Plans } from './pages/Plans';
import { Billing } from './pages/Billing';
import { InvoiceCreate } from './pages/InvoiceCreate';
import { Invoices } from './pages/Invoices';
import { InvoiceDetail } from './pages/InvoiceDetail';
import { Playground } from './pages/Playground';
import { ZatcaSetup } from './pages/ZatcaSetup';
import { AiInsights } from './pages/AiInsights';
import { Webhooks } from './pages/Webhooks';
import { Reports } from './pages/Reports';
import { ApiKeys } from './pages/ApiKeys';
import { ErrorBoundary } from './components/common/ErrorBoundary';

function App() {
  const [activeMenu, setActiveMenu] = useState<string>('dashboard');

  const handleMenuClick = (menuId: string) => {
    setActiveMenu(menuId);
  };

  return (
    <HashRouter>
      <ErrorBoundary>
        <LanguageProvider>
          <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/plans" element={<Plans />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu={activeMenu}
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <Dashboard />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/invoices/create"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="create-invoice"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <InvoiceCreate />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/invoices/:invoiceId"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="invoices"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <InvoiceDetail />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/invoices"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="invoices"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <Invoices />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/ai-insights"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="ai-insights"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <AiInsights />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/api-playground"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="api-playground"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <Playground />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/webhooks"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="webhooks"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <Webhooks />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="reports"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <Reports />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/api-keys"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="api-keys"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <ApiKeys />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/billing"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="billing"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <Billing />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          <Route
            path="/zatca-setup"
            element={
              <ProtectedRoute>
                <PageWrapper
                  activeMenu="zatca-setup"
                  onMenuClick={handleMenuClick}
                  environment="sandbox"
                  apiUsage={{ used: 750, limit: 1000 }}
                >
                  <ZatcaSetup />
                </PageWrapper>
              </ProtectedRoute>
            }
          />

          {/* Default redirect - uses RootRedirect component for reactive auth check */}
          <Route path="/" element={<RootRedirect />} />
          
          {/* Catch-all route for unmatched paths */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </LanguageProvider>
      </ErrorBoundary>
    </HashRouter>
  );
}

export default App;

