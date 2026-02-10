import React from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import { Invoice } from '../../types/invoice';
import { useLanguage } from '../../context/LanguageContext';

interface InvoiceTableProps {
  invoices: Invoice[];
  onView?: (invoice: Invoice) => void;
  onEdit?: (invoice: Invoice) => void;
  onDelete?: (invoice: Invoice) => void;
  isLoading?: boolean;
}

export const InvoiceTable: React.FC<InvoiceTableProps> = ({
  invoices,
  onView,
  onEdit,
  onDelete,
  isLoading = false,
}) => {
  const { direction, t } = useLanguage();

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString(direction === 'rtl' ? 'ar-SA' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-2" />
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          </div>
        </div>
      </Card>
    );
  }

  if (invoices.length === 0) {
    return (
      <Card>
        <div className="text-center py-12">
          <p className="text-slate-500">{direction === 'rtl' ? 'لا توجد فواتير' : 'No invoices found'}</p>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="overflow-x-auto" dir={direction}>
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="ps-6 pe-6 py-3 text-start text-xs font-semibold text-slate-700 uppercase tracking-wider">
                {t('invoice.number')}
              </th>
              <th className="ps-6 pe-6 py-3 text-start text-xs font-semibold text-slate-700 uppercase tracking-wider">
                {t('invoice.phase')}
              </th>
              <th className="ps-6 pe-6 py-3 text-start text-xs font-semibold text-slate-700 uppercase tracking-wider">
                {t('invoice.status')}
              </th>
              <th className="ps-6 pe-6 py-3 text-start text-xs font-semibold text-slate-700 uppercase tracking-wider">
                {t('invoice.date')}
              </th>
              <th className="ps-6 pe-6 py-3 text-start text-xs font-semibold text-slate-700 uppercase tracking-wider">
                {t('invoice.actions')}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {invoices.map((invoice) => (
              <tr key={invoice.id} className="hover:bg-slate-50 transition-colors">
                <td className="ps-6 pe-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-slate-900">{invoice.invoiceNumber}</div>
                  {invoice.sellerName && (
                    <div className="text-sm text-slate-500">{invoice.sellerName}</div>
                  )}
                </td>
                <td className="ps-6 pe-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Phase {invoice.phase}
                  </span>
                </td>
                <td className="ps-6 pe-6 py-4 whitespace-nowrap">
                  <InvoiceStatusBadge status={invoice.status} />
                </td>
                <td className="ps-6 pe-6 py-4 whitespace-nowrap text-sm text-slate-500">
                  {formatDate(invoice.date)}
                </td>
                <td className="ps-6 pe-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    {onView && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => onView(invoice)}
                      >
                        {t('common.view')}
                      </Button>
                    )}
                    {onEdit && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => onEdit(invoice)}
                      >
                        {t('common.edit')}
                      </Button>
                    )}
                    {onDelete && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => onDelete(invoice)}
                      >
                        {t('common.delete')}
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

