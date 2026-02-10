"""
Database CRUD operations.

Provides create, read, update, delete operations for invoice data.
Handles database interactions and query construction.
Does not contain business logic or validation rules.

NOTE: This module uses the legacy Invoice model from app.db.models.
For new code, use app.models.invoice.Invoice and InvoiceService instead.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

# NOTE: Legacy CRUD functions - consider migrating to InvoiceService
# For now, we'll keep this for backward compatibility but it may not work
# with the new Invoice model structure. New code should use InvoiceService.
try:
    from app.models.invoice import Invoice  # New Invoice model
except ImportError:
    # Fallback if new model not available
    Invoice = None


def create_invoice(db: Session, invoice_data: dict) -> Invoice:
    """
    Creates a new invoice record.
    
    Args:
        db: Database session
        invoice_data: Invoice data dictionary
        
    Returns:
        Created invoice model
    """
    db_invoice = Invoice(**invoice_data)
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


def get_invoice(db: Session, invoice_number: str) -> Optional[Invoice]:
    """
    Retrieves invoice by invoice number.
    
    Args:
        db: Database session
        invoice_number: Invoice number
        
    Returns:
        Invoice model or None
    """
    return db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()


def get_invoices(db: Session, skip: int = 0, limit: int = 100) -> List[Invoice]:
    """
    Retrieves list of invoices.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of invoice models
    """
    return db.query(Invoice).offset(skip).limit(limit).all()


def update_invoice(db: Session, invoice_number: str, update_data: dict) -> Optional[Invoice]:
    """
    Updates invoice record.
    
    Args:
        db: Database session
        invoice_number: Invoice number
        update_data: Update data dictionary
        
    Returns:
        Updated invoice model or None
    """
    invoice = get_invoice(db, invoice_number)
    if invoice:
        for key, value in update_data.items():
            setattr(invoice, key, value)
        db.commit()
        db.refresh(invoice)
    return invoice

