"""
Database models base.

Provides the declarative base for all SQLAlchemy models.
All models should import Base from this module.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, Text, Float, Integer
from datetime import datetime

Base = declarative_base()


# Legacy Invoice model REMOVED
# The new Invoice model is in app/models/invoice.py
# This legacy model caused table name conflicts and is no longer needed.
# If you need invoice functionality, use app.models.invoice.Invoice instead.

