import React, { useState, useEffect } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { EmptyState } from '../components/common/EmptyState';
import { useLanguage } from '../context/LanguageContext';
import {
  listWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  getWebhookLogs,
  type WebhookResponse,
  type WebhookCreateRequest,
  type WebhookEvent,
  type WebhookLogResponse,
} from '../lib/webhooksApi';

const WEBHOOK_EVENTS: WebhookEvent[] = [
  'invoice.cleared',
  'invoice.rejected',
  'invoice.failed',
  'invoice.retry_started',
  'invoice.retry_completed',
];

export const Webhooks: React.FC = () => {
  const { t, direction } = useLanguage();
  const [webhooks, setWebhooks] = useState<WebhookResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [logsWebhookId, setLogsWebhookId] = useState<number | null>(null);
  const [logs, setLogs] = useState<WebhookLogResponse[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [formUrl, setFormUrl] = useState('');
  const [formEvents, setFormEvents] = useState<WebhookEvent[]>(['invoice.cleared']);
  const [formActive, setFormActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadWebhooks = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await listWebhooks();
      setWebhooks(res.webhooks);
      setTotal(res.total);
      setActiveCount(res.active_count);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load webhooks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadLogs = async (webhookId: number) => {
    setLogsWebhookId(webhookId);
    try {
      setLogsLoading(true);
      const data = await getWebhookLogs(webhookId);
      setLogs(data);
    } catch (err: unknown) {
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formUrl.trim()) {
      setFormError('URL is required');
      return;
    }
    if (formEvents.length === 0) {
      setFormError('Select at least one event');
      return;
    }
    setFormError(null);
    setSubmitting(true);
    try {
      await createWebhook({
        url: formUrl.trim(),
        events: formEvents,
        is_active: formActive,
      });
      setShowCreateModal(false);
      resetForm();
      await loadWebhooks();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create webhook');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (id: number) => {
    if (!formUrl.trim()) {
      setFormError('URL is required');
      return;
    }
    if (formEvents.length === 0) {
      setFormError('Select at least one event');
      return;
    }
    setFormError(null);
    setSubmitting(true);
    try {
      await updateWebhook(id, {
        url: formUrl.trim(),
        events: formEvents,
        is_active: formActive,
      });
      setEditingId(null);
      resetForm();
      await loadWebhooks();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to update webhook');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(direction === 'rtl' ? 'حذف هذا الوبهوك؟' : 'Delete this webhook?')) return;
    try {
      await deleteWebhook(id);
      if (logsWebhookId === id) setLogsWebhookId(null);
      await loadWebhooks();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete webhook');
    }
  };

  const resetForm = () => {
    setFormUrl('');
    setFormEvents(['invoice.cleared']);
    setFormActive(true);
    setFormError(null);
  };

  const openEdit = (w: WebhookResponse) => {
    setEditingId(w.id);
    setFormUrl(w.url);
    setFormEvents(w.events as WebhookEvent[]);
    setFormActive(w.is_active);
    setFormError(null);
  };

  const toggleEvent = (event: WebhookEvent) => {
    setFormEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  return (
    <div className="space-y-6" dir={direction} data-testid="webhooks-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {direction === 'rtl' ? 'الوبهوكات' : 'Webhooks'}
          </h1>
          <p className="text-slate-500 mt-1">
            {total} total · {activeCount} active
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => {
            resetForm();
            setShowCreateModal(true);
          }}
          data-testid="webhook-create-button"
        >
          {direction === 'rtl' ? 'إضافة وبهوك' : 'Add Webhook'}
        </Button>
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
            <div className="h-4 bg-slate-200 rounded w-5/6" />
          </div>
        </Card>
      ) : webhooks.length === 0 ? (
        <EmptyState
          title={direction === 'rtl' ? 'لا توجد وبهوكات' : 'No webhooks'}
          description={direction === 'rtl' ? 'أضف عنوان URL لاستقبال إشعارات الفواتير.' : 'Add a URL to receive invoice event notifications.'}
          actionLabel={direction === 'rtl' ? 'إضافة وبهوك' : 'Add Webhook'}
          onAction={() => {
            resetForm();
            setShowCreateModal(true);
          }}
        />
      ) : (
        <div className="space-y-4">
          {webhooks.map((w) => (
            <Card key={w.id} padding="md" className="border border-slate-200">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-slate-900 truncate">{w.url}</span>
                    <Badge variant={w.is_active ? 'success' : 'default'}>
                      {w.is_active ? (direction === 'rtl' ? 'نشط' : 'Active') : (direction === 'rtl' ? 'غير نشط' : 'Inactive')}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {w.events.join(', ')} · failures: {w.failure_count}
                    {w.last_triggered_at && ` · last: ${new Date(w.last_triggered_at).toLocaleString()}`}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => loadLogs(w.id)}>
                    {direction === 'rtl' ? 'سجلات' : 'Logs'}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => openEdit(w)}>
                    {t('common.edit')}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleDelete(w.id)}>
                    {t('common.delete')}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={direction === 'rtl' ? 'إضافة وبهوك' : 'Add Webhook'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">URL</label>
            <input
              type="url"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              placeholder="https://your-server.com/webhook"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Events</label>
            <div className="space-y-2">
              {WEBHOOK_EVENTS.map((ev) => (
                <label key={ev} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formEvents.includes(ev)}
                    onChange={() => toggleEvent(ev)}
                  />
                  <span className="text-sm">{ev}</span>
                </label>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formActive}
              onChange={(e) => setFormActive(e.target.checked)}
            />
            <span className="text-sm">Active</span>
          </label>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleCreate} disabled={submitting}>
              {submitting ? '...' : 'Create'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit modal */}
      <Modal
        isOpen={editingId !== null}
        onClose={() => { setEditingId(null); resetForm(); }}
        title={direction === 'rtl' ? 'تعديل وبهوك' : 'Edit Webhook'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">URL</label>
            <input
              type="url"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Events</label>
            <div className="space-y-2">
              {WEBHOOK_EVENTS.map((ev) => (
                <label key={ev} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formEvents.includes(ev)}
                    onChange={() => toggleEvent(ev)}
                  />
                  <span className="text-sm">{ev}</span>
                </label>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formActive}
              onChange={(e) => setFormActive(e.target.checked)}
            />
            <span className="text-sm">Active</span>
          </label>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setEditingId(null); resetForm(); }}>Cancel</Button>
            <Button
              variant="primary"
              onClick={() => editingId !== null && handleUpdate(editingId)}
              disabled={submitting}
            >
              {submitting ? '...' : 'Save'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Logs modal */}
      <Modal
        isOpen={logsWebhookId !== null}
        onClose={() => setLogsWebhookId(null)}
        title={direction === 'rtl' ? 'سجلات الوبهوك' : 'Webhook Logs'}
      >
        <div className="max-h-[70vh] overflow-y-auto">
          {logsLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : logs.length === 0 ? (
            <p className="text-sm text-slate-500">No delivery logs yet.</p>
          ) : (
            <ul className="space-y-3">
              {logs.map((log) => (
                <li key={log.id} className="p-3 bg-slate-50 rounded-lg text-sm">
                  <div className="flex justify-between items-start gap-2">
                    <span className="font-medium">{log.event}</span>
                    <span className="text-slate-500">
                      {log.response_status != null ? `${log.response_status}` : '—'} · {new Date(log.created_at).toLocaleString()}
                    </span>
                  </div>
                  {log.error_message && (
                    <p className="text-red-600 mt-1">{log.error_message}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Modal>
    </div>
  );
};
