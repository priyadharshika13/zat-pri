# ZATCA AI API - Subscription Plans

This document outlines all available subscription plans, their features, limits, and use cases.

## Overview

The ZATCA AI API platform offers **5 subscription tiers** designed to meet different business needs:

1. **Free Sandbox** - Limited forever plan for testing
2. **Trial** - 7-day trial plan (auto-assigned on signup)
3. **Starter** - Basic paid plan for small businesses
4. **Pro** - Advanced paid plan for growing businesses
5. **Enterprise** - Custom limits plan for large organizations

---

## Plan Comparison

| Feature | Free Sandbox | Trial | Starter | Pro | Enterprise |
|---------|-------------|-------|---------|-----|------------|
| **Monthly Invoice Limit** | 10 | 50 | 500 | 5,000 | Unlimited |
| **Monthly AI Limit** | 5 | 20 | 100 | 1,000 | Unlimited |
| **Rate Limit (per minute)** | 10 | 30 | 60 | 120 | 300 |
| **Phase 1 (Simplified)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Phase 2 (Standard)** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **AI Explanations** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Production Access** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Priority Support** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Custom Limits** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Dedicated Support** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Plan Details

### 1. Free Sandbox

**Target Audience:** Developers, testers, and individuals exploring the platform

**Limits:**
- **Monthly Invoice Limit:** 10 invoices
- **Monthly AI Limit:** 5 AI requests
- **Rate Limit:** 10 requests per minute

**Features:**
- ✅ Phase 1 (Simplified) invoicing
- ❌ Phase 2 (Standard) invoicing
- ❌ AI-powered explanations
- ❌ Production environment access

**Use Cases:**
- Initial platform exploration
- Development and testing
- Learning ZATCA compliance
- Proof of concept projects

**Restrictions:**
- Sandbox environment only
- Limited to Phase 1 invoicing
- No production access
- No AI features

---

### 2. Trial

**Target Audience:** New users evaluating the platform

**Limits:**
- **Monthly Invoice Limit:** 50 invoices
- **Monthly AI Limit:** 20 AI requests
- **Rate Limit:** 30 requests per minute
- **Duration:** 7 days (auto-assigned on signup)

**Features:**
- ✅ Phase 1 (Simplified) invoicing
- ✅ Phase 2 (Standard) invoicing
- ✅ AI-powered explanations
- ❌ Production environment access

**Use Cases:**
- Full feature evaluation
- Testing Phase 2 compliance
- Testing AI features
- Pre-production testing

**Restrictions:**
- Sandbox environment only
- No production access
- Limited to 7 days
- Auto-converts to Free Sandbox after expiration

---

### 3. Starter

**Target Audience:** Small businesses and startups

**Limits:**
- **Monthly Invoice Limit:** 500 invoices
- **Monthly AI Limit:** 100 AI requests
- **Rate Limit:** 60 requests per minute

**Features:**
- ✅ Phase 1 (Simplified) invoicing
- ✅ Phase 2 (Standard) invoicing
- ✅ AI-powered explanations
- ✅ Production environment access

**Use Cases:**
- Small businesses processing < 500 invoices/month
- Startups launching e-invoicing
- Businesses needing production access
- Companies requiring AI insights

**Benefits:**
- Production-ready
- Full ZATCA compliance (Phase 1 & 2)
- AI-powered invoice analysis
- Suitable for small to medium operations

---

### 4. Pro

**Target Audience:** Growing businesses and established companies

**Limits:**
- **Monthly Invoice Limit:** 5,000 invoices
- **Monthly AI Limit:** 1,000 AI requests
- **Rate Limit:** 120 requests per minute

**Features:**
- ✅ Phase 1 (Simplified) invoicing
- ✅ Phase 2 (Standard) invoicing
- ✅ AI-powered explanations
- ✅ Production environment access
- ✅ Priority support

**Use Cases:**
- Medium to large businesses
- High-volume invoice processing
- Companies requiring priority support
- Businesses needing extensive AI analysis

**Benefits:**
- 10x invoice capacity vs Starter
- 10x AI capacity vs Starter
- 2x rate limit vs Starter
- Priority customer support
- Ideal for scaling operations

---

### 5. Enterprise

**Target Audience:** Large organizations with high-volume needs

**Limits:**
- **Monthly Invoice Limit:** Unlimited
- **Monthly AI Limit:** Unlimited
- **Rate Limit:** 300 requests per minute

**Features:**
- ✅ Phase 1 (Simplified) invoicing
- ✅ Phase 2 (Standard) invoicing
- ✅ AI-powered explanations
- ✅ Production environment access
- ✅ Priority support
- ✅ Custom limits (negotiable)
- ✅ Dedicated support

**Use Cases:**
- Large enterprises
- High-volume invoice processing
- Organizations requiring custom solutions
- Companies needing dedicated support

**Benefits:**
- Unlimited invoices and AI requests
- Highest rate limits (300/min)
- Custom limit negotiation
- Dedicated account manager
- Priority support with SLA
- Tailored solutions

---

## Feature Definitions

### Phase 1 (Simplified)
- Basic ZATCA compliance for simplified tax invoices
- Suitable for B2C transactions
- Lower complexity requirements

### Phase 2 (Standard)
- Full ZATCA compliance for standard tax invoices
- Required for B2B transactions
- Includes cryptographic signing and QR codes
- More complex validation requirements

### AI Explanations
- AI-powered analysis of invoice compliance
- Automated error detection and suggestions
- Intelligent troubleshooting recommendations
- Natural language explanations of ZATCA requirements

### Production Access
- Access to production ZATCA environment
- Real invoice submission to ZATCA
- Production-grade security and compliance
- Required for live business operations

### Priority Support
- Faster response times
- Priority ticket handling
- Extended support hours
- Direct access to technical team

### Custom Limits
- Negotiable invoice and AI limits
- Tailored to business needs
- Flexible rate limits
- Custom feature requests

### Dedicated Support
- Dedicated account manager
- Custom onboarding
- Regular check-ins
- Proactive issue resolution

---

## Plan Selection Guide

### Choose **Free Sandbox** if:
- You're just exploring the platform
- You need < 10 invoices/month
- You're in development/testing phase
- You don't need production access

### Choose **Trial** if:
- You're evaluating the platform
- You want to test all features
- You need 7 days to decide
- You're preparing for production

### Choose **Starter** if:
- You process < 500 invoices/month
- You're a small business
- You need production access
- You want full ZATCA compliance

### Choose **Pro** if:
- You process 500-5,000 invoices/month
- You're a growing business
- You need priority support
- You require extensive AI analysis

### Choose **Enterprise** if:
- You process > 5,000 invoices/month
- You need unlimited capacity
- You require custom solutions
- You want dedicated support

---

## Rate Limits Explained

Rate limits control how many API requests you can make per minute:

- **10/min (Free Sandbox):** Suitable for manual testing
- **30/min (Trial):** Good for automated testing
- **60/min (Starter):** Adequate for small businesses
- **120/min (Pro):** Suitable for medium businesses
- **300/min (Enterprise):** High-volume operations

**Note:** Rate limits apply to all API endpoints. Exceeding limits will result in HTTP 429 (Too Many Requests) responses.

---

## Usage Tracking

All plans track:
- **Invoice Usage:** Number of invoices processed this month
- **AI Usage:** Number of AI requests made this month
- **Rate Limit Status:** Current requests per minute

Usage is reset monthly on your billing cycle date.

---

## Plan Upgrades & Downgrades

### Upgrading
- Upgrades take effect immediately
- Prorated billing may apply
- Higher limits available immediately

### Downgrading
- Downgrades take effect at end of billing period
- Usage must be within new plan limits
- Features may be restricted

### Trial Expiration
- Trial automatically converts to Free Sandbox
- No data loss
- Upgrade anytime to maintain access

---

## API Endpoints

### Get All Plans
```
GET /api/v1/plans
```

### Get Current Subscription
```
GET /api/v1/plans/current
```

### Get Usage
```
GET /api/v1/plans/usage
```

---

## Technical Implementation

Plans are defined in:
- **Backend:** `backend/app/services/plan_seed_service.py`
- **Model:** `backend/app/models/subscription.py`
- **Frontend:** `frontend/src/pages/Billing.tsx`

Plans are automatically seeded on first deployment or in development environments.

---

## Support

For questions about plans or to request Enterprise custom limits:
- **Starter/Pro:** Use in-app support or email
- **Enterprise:** Contact your dedicated account manager
- **All Plans:** Check documentation at `/docs`

---

## Notes

- All limits are **monthly** and reset on your billing cycle
- **0 = Unlimited** (Enterprise plan only)
- Rate limits are **per minute**, not per second
- Production access requires valid ZATCA credentials
- AI features require active AI service configuration
- All plans include basic API access and documentation

