import React from 'react';
import { Badge, BadgeVariant } from '../common/Badge';
import { useLanguage } from '../../context/LanguageContext';
import { InvoiceStatus } from '../../types/invoice';

interface InvoiceStatusBadgeProps {
  status: InvoiceStatus;
}

export const InvoiceStatusBadge: React.FC<InvoiceStatusBadgeProps> = ({ status }) => {
  const { t } = useLanguage();
  const statusUpper = status.toUpperCase();

  let variant: BadgeVariant = 'default';
  let label: string;

  switch (statusUpper) {
    case 'CLEARED':
      variant = 'success';
      label = t('invoiceStatus.cleared');
      break;
    case 'REJECTED':
      variant = 'danger';
      label = t('invoiceStatus.rejected');
      break;
    case 'PROCESSING':
    case 'PENDING':
    case 'SUBMITTED':
      variant = 'warning';
      label = t('invoiceStatus.processing');
      break;
    case 'CREATED':
      variant = 'default';
      label = t('invoiceStatus.created');
      break;
    case 'FAILED':
    case 'ERROR':
      variant = 'danger';
      label = t('invoiceStatus.failed');
      break;
    default:
      variant = 'default';
      label = String(status);
  }

  return <Badge variant={variant}>{label}</Badge>;
};

