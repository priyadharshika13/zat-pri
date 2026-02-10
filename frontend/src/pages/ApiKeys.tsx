import React, { useState, useEffect } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { EmptyState } from '../components/common/EmptyState';
import { useLanguage } from '../context/LanguageContext';
import { listApiKeys, createApiKey, deleteApiKey, maskApiKey, type ApiKeyResponse } from '../lib/apiKeysApi';
import { apiGet } from '../lib/api';

interface TenantMe {
  id: number;
  company_name: string;
  vat_number: string;
}

export const ApiKeys: React.FC = () => {
  const { direction, t } = useLanguage();
  const [keys, setKeys] = useState<ApiKeyResponse[]>([]);
  const [tenant, setTenant] = useState<TenantMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [keysRes, tenantRes] = await Promise.all([
        listApiKeys(),
        apiGet<TenantMe>('/api/v1/tenants/me').catch(() => null),
      ]);
      setKeys(keysRes);
      setTenant(tenantRes);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    if (!tenant) return;
    setSubmitting(true);
    try {
      const created = await createApiKey(tenant.id, { is_active: true });
      setCreatedKey(created.api_key);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create API key');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(direction === 'rtl' ? 'إلغاء هذا المفتاح؟ لن يتمكن من الوصول مرة أخرى.' : 'Revoke this key? It will no longer work.')) return;
    try {
      await deleteApiKey(id);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to revoke key');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6" dir={direction} data-testid="api-keys-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {direction === 'rtl' ? 'مفاتيح API' : 'API Keys'}
          </h1>
          <p className="text-slate-500 mt-1">
            {direction === 'rtl' ? 'إنشاء وإدارة مفاتيح الوصول للتكاملات.' : 'Create and manage access keys for integrations.'}
          </p>
        </div>
        {tenant && (
          <Button
            variant="primary"
            onClick={() => {
              setCreatedKey(null);
              setShowCreateModal(true);
            }}
            disabled={submitting}
            data-testid="api-keys-create-button"
          >
            {direction === 'rtl' ? 'إنشاء مفتاح' : 'Create key'}
          </Button>
        )}
      </div>

      {error && (
        <Card padding="md" className="bg-red-50 border-red-200">
          <p className="text-sm text-red-800">{error}</p>
        </Card>
      )}

      {loading ? (
        <Card padding="md">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-slate-200 rounded w-3/4" />
            <div className="h-4 bg-slate-200 rounded w-1/2" />
          </div>
        </Card>
      ) : keys.length === 0 ? (
        <EmptyState
          title={direction === 'rtl' ? 'لا توجد مفاتيح' : 'No API keys'}
          description={direction === 'rtl' ? 'أنشئ مفتاحًا للوصول إلى الواجهة برمجيًا.' : 'Create a key to access the API programmatically.'}
          actionLabel={tenant ? (direction === 'rtl' ? 'إنشاء مفتاح' : 'Create key') : undefined}
          onAction={tenant ? () => setShowCreateModal(true) : undefined}
        />
      ) : (
        <div className="space-y-4">
          {keys.map((k) => (
            <Card key={k.id} padding="md" className="border border-slate-200">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="min-w-0">
                  <code className="text-sm text-slate-700 bg-slate-100 px-2 py-1 rounded">
                    {maskApiKey(k.api_key)}
                  </code>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant={k.is_active ? 'success' : 'default'}>
                      {k.is_active ? (direction === 'rtl' ? 'نشط' : 'Active') : (direction === 'rtl' ? 'معطل' : 'Inactive')}
                    </Badge>
                    <span className="text-xs text-slate-500">
                      {direction === 'rtl' ? 'أنشئ في' : 'Created'} {new Date(k.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                <Button variant="danger" size="sm" onClick={() => handleDelete(k.id)}>
                  {direction === 'rtl' ? 'إلغاء' : 'Revoke'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setCreatedKey(null);
        }}
        title={direction === 'rtl' ? 'إنشاء مفتاح API' : 'Create API key'}
      >
        <div className="space-y-4">
          {createdKey ? (
            <>
              <p className="text-sm text-amber-800 bg-amber-50 p-3 rounded">
                {direction === 'rtl' ? 'انسخ المفتاح الآن. لن نتمكن من عرضه مرة أخرى.' : 'Copy the key now. We won’t show it again.'}
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-sm bg-slate-100 p-2 rounded break-all">{createdKey}</code>
                <Button variant="secondary" size="sm" onClick={() => copyToClipboard(createdKey)}>
                  Copy
                </Button>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-600">
              {direction === 'rtl' ? 'سيتم إنشاء مفتاح عشوائي جديد لـ' : 'A new random key will be created for'} {tenant?.company_name ?? 'your tenant'}.
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreateModal(false); setCreatedKey(null); }}>
              {createdKey ? 'Done' : 'Cancel'}
            </Button>
            {!createdKey && (
              <Button variant="primary" onClick={handleCreate} disabled={submitting}>
                {submitting ? '...' : 'Create'}
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
};
