"""
Reporting service for invoice and VAT analytics.

Provides read-only reporting operations with tenant isolation.
Uses efficient aggregation queries for performance.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, extract

from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.auth import TenantContext
from app.schemas.reporting import (
    InvoiceReportItem,
    VATSummaryItem,
    StatusBreakdownItem
)
from app.core.constants import InvoiceMode, Environment

logger = logging.getLogger(__name__)


class ReportingService:
    """
    Service for generating invoice and VAT reports.
    
    CRITICAL: All operations enforce tenant isolation.
    No cross-tenant access is possible.
    """
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes reporting service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request (enforces isolation)
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def get_invoice_report(
        self,
        page: int = 1,
        page_size: int = 50,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[InvoiceStatus] = None,
        phase: Optional[InvoiceMode] = None
    ) -> Tuple[List[InvoiceReportItem], int]:
        """
        Gets paginated invoice report with filtering.
        
        CRITICAL: All queries are automatically filtered by tenant_id.
        No cross-tenant access is possible.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            date_from: Filter by start date
            date_to: Filter by end date
            status: Filter by invoice status
            phase: Filter by invoice phase
            
        Returns:
            Tuple of (list of InvoiceReportItem, total count)
        """
        # Enforce max page size
        page_size = min(page_size, 100)
        offset = (page - 1) * page_size
        
        # Build base query with tenant isolation and explicit ordering
        # CRITICAL: Use secondary ordering by id to ensure deterministic results
        # when multiple invoices share the same created_at timestamp (common in
        # high-volume scenarios or fast batch inserts). This prevents pagination
        # instability and ensures consistent ordering across SQLite and PostgreSQL.
        query = (
            self.db.query(Invoice)
            .filter(Invoice.tenant_id == self.tenant_context.tenant_id)
            .order_by(Invoice.created_at.desc(), Invoice.id.desc())
        )
        
        # Apply filters
        if date_from:
            query = query.filter(Invoice.created_at >= date_from)
        
        if date_to:
            # Include the entire end date
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Invoice.created_at <= date_to_end)
        
        if status:
            query = query.filter(Invoice.status == status)
        
        if phase:
            query = query.filter(Invoice.phase == phase)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination (ordering already applied above)
        query = query.offset(offset).limit(page_size)
        
        invoices = query.all()
        
        # Convert to report items
        report_items = [
            InvoiceReportItem(
                invoice_number=inv.invoice_number,
                status=inv.status,
                phase=inv.phase,
                total_amount=inv.total_amount,
                tax_amount=inv.tax_amount,
                created_at=inv.created_at
            )
            for inv in invoices
        ]
        
        logger.debug(
            f"Invoice report: tenant_id={self.tenant_context.tenant_id}, "
            f"page={page}, page_size={page_size}, total={total}, returned={len(report_items)}"
        )
        
        return report_items, total
    
    def get_vat_summary(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        group_by: str = "day"
    ) -> Tuple[List[VATSummaryItem], float, float, int]:
        """
        Gets VAT summary aggregated by day or month.
        
        CRITICAL: All queries are automatically filtered by tenant_id.
        Uses efficient aggregation queries for performance.
        
        Args:
            date_from: Filter by start date
            date_to: Filter by end date
            group_by: Aggregation period ("day" or "month")
            
        Returns:
            Tuple of (summary items, total_tax_amount, total_invoice_amount, total_invoice_count)
        """
        # Validate group_by
        if group_by not in ["day", "month"]:
            raise ValueError("group_by must be 'day' or 'month'")
        
        # Build base query with tenant isolation
        query = (
            self.db.query(Invoice)
            .filter(Invoice.tenant_id == self.tenant_context.tenant_id)
        )
        
        # Apply date filters
        if date_from:
            query = query.filter(Invoice.created_at >= date_from)
        
        if date_to:
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Invoice.created_at <= date_to_end)
        
        # Build aggregation query
        if group_by == "day":
            # Group by date (YYYY-MM-DD)
            date_expr = func.date(Invoice.created_at).label("date")
            
            # Aggregate query
            agg_query = query.with_entities(
                date_expr,
                func.sum(Invoice.tax_amount).label("total_tax"),
                func.sum(Invoice.total_amount).label("total_amount"),
                func.count(Invoice.id).label("invoice_count")
            ).group_by(date_expr).order_by(date_expr.desc())
            
            results = agg_query.all()
            
            # Convert to summary items
            summary_items = [
                VATSummaryItem(
                    date=str(row.date),
                    total_tax_amount=float(row.total_tax or 0.0),
                    total_invoice_amount=float(row.total_amount or 0.0),
                    invoice_count=int(row.invoice_count or 0)
                )
                for row in results
            ]
        else:  # month
            # Group by year and month separately, format in Python
            # This approach works across SQLite and PostgreSQL
            year_expr = extract('year', Invoice.created_at).label("year")
            month_expr = extract('month', Invoice.created_at).label("month")
            
            # Aggregate query
            agg_query = query.with_entities(
                year_expr,
                month_expr,
                func.sum(Invoice.tax_amount).label("total_tax"),
                func.sum(Invoice.total_amount).label("total_amount"),
                func.count(Invoice.id).label("invoice_count")
            ).group_by(year_expr, month_expr).order_by(year_expr.desc(), month_expr.desc())
            
            results = agg_query.all()
            
            # Convert to summary items with formatted date (YYYY-MM)
            # Handle both integer and float results from extract()
            summary_items = [
                VATSummaryItem(
                    date=f"{int(float(row.year))}-{int(float(row.month)):02d}",
                    total_tax_amount=float(row.total_tax or 0.0),
                    total_invoice_amount=float(row.total_amount or 0.0),
                    invoice_count=int(row.invoice_count or 0)
                )
                for row in results
            ]
        
        # Calculate totals
        total_tax = sum(item.total_tax_amount for item in summary_items)
        total_amount = sum(item.total_invoice_amount for item in summary_items)
        total_count = sum(item.invoice_count for item in summary_items)
        
        logger.debug(
            f"VAT summary: tenant_id={self.tenant_context.tenant_id}, "
            f"group_by={group_by}, items={len(summary_items)}"
        )
        
        return summary_items, total_tax, total_amount, total_count
    
    def get_status_breakdown(self) -> Tuple[List[StatusBreakdownItem], int]:
        """
        Gets invoice status breakdown.
        
        CRITICAL: All queries are automatically filtered by tenant_id.
        Uses efficient aggregation query.
        
        Returns:
            Tuple of (breakdown items, total invoice count)
        """
        # Build aggregation query with tenant isolation and explicit ordering
        query = (
            self.db.query(
                Invoice.status,
                func.count(Invoice.id).label("count")
            )
            .filter(Invoice.tenant_id == self.tenant_context.tenant_id)
            .group_by(Invoice.status)
            .order_by(Invoice.status)
        )
        
        results = query.all()
        
        # Convert to breakdown items
        breakdown_items = [
            StatusBreakdownItem(
                status=row.status,
                count=int(row.count)
            )
            for row in results
        ]
        
        # Calculate total
        total = sum(item.count for item in breakdown_items)
        
        logger.debug(
            f"Status breakdown: tenant_id={self.tenant_context.tenant_id}, "
            f"total={total}"
        )
        
        return breakdown_items, total
    
    def get_revenue_summary(self) -> Tuple[float, float, float, int, int]:
        """
        Gets revenue summary for the tenant.
        
        CRITICAL: All queries are automatically filtered by tenant_id.
        Only counts CLEARED invoices for revenue.
        
        Returns:
            Tuple of (total_revenue, total_tax, net_revenue, cleared_count, total_count)
        """
        # Build base query with tenant isolation
        query = (
            self.db.query(Invoice)
            .filter(Invoice.tenant_id == self.tenant_context.tenant_id)
        )
        
        # Get totals for all invoices
        total_query = query.with_entities(
            func.sum(Invoice.total_amount).label("total_revenue"),
            func.sum(Invoice.tax_amount).label("total_tax"),
            func.count(Invoice.id).label("total_count")
        )
        
        total_result = total_query.first()
        total_revenue = float(total_result.total_revenue or 0.0)
        total_tax = float(total_result.total_tax or 0.0)
        total_count = int(total_result.total_count or 0)
        
        # Get cleared invoices only
        cleared_query = query.filter(
            Invoice.status == InvoiceStatus.CLEARED
        ).with_entities(
            func.sum(Invoice.total_amount).label("cleared_revenue"),
            func.count(Invoice.id).label("cleared_count")
        )
        
        cleared_result = cleared_query.first()
        cleared_revenue = float(cleared_result.cleared_revenue or 0.0)
        cleared_count = int(cleared_result.cleared_count or 0)
        
        # Net revenue = total revenue - total tax
        net_revenue = total_revenue - total_tax
        
        logger.debug(
            f"Revenue summary: tenant_id={self.tenant_context.tenant_id}, "
            f"total_revenue={total_revenue}, cleared_count={cleared_count}"
        )
        
        return total_revenue, total_tax, net_revenue, cleared_count, total_count

