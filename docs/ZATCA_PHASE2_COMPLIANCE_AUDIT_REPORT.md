# ZATCA Phase-2 Compliance Audit Report

**Date:** 2026-01-31  
**Last Updated:** 2026-01-31 (post-remediation)  
**Auditor Role:** Senior ZATCA Phase-2 Compliance Auditor & Backend Architect  
**Scope:** Saudi ZATCA e-invoicing (Fatoora) implementation — sandbox approval & production readiness  
**Context:** Commercial SaaS/API use in Saudi Arabia

---

## Executive Summary

| Overall Compliance Status | **READY FOR SANDBOX** *(pending ZATCA SDK/validator run)* |
|--------------------------|-----------------------------------------------------------|
| Risk Level | **LOW–MEDIUM** |
| Sandbox Submission Ready | **YES** — critical blockers (PIH, base64, UTC, C14N, first-invoice) remediated |
| Production CSID Blockers | **REDUCED** — pre-sign cert expiry and optional (Language, CSR subject) remain |

The implementation has a solid base: OAuth, certificate-key verification, Phase-1/Phase-2 QR (TLV), VAT logic, retry/error handling, and tenant isolation. **Previously identified critical gaps have been remediated:** PIH is emitted in UBL XML, clearance request sends base64-encoded invoice, Issue Date/Time are normalized to UTC, W3C C14N is used for signing when lxml is available, and first-invoice PIH is optional (omit when absent). **Remaining:** Run ZATCA Compliance SDK/validator on generated invoices; add pre-sign certificate expiry check and optional Language/CSR improvements before production.

---

## 1. XML & UBL 2.1 Compliance

| Check | Result | Evidence / Notes |
|-------|--------|------------------|
| Invoice XML structure vs ZATCA UBL 2.1 | **PASS** | `xml_generator.py`: Root `<Invoice>`, namespaces `Invoice-2`, `CommonAggregateComponents-2`, `CommonBasicComponents-2` per UBL 2.1. |
| Mandatory: Seller VAT | **PASS** | `AccountingSupplierParty` → `PartyTaxScheme` → `CompanyID` (seller_tax_number). |
| Mandatory: Buyer VAT | **PASS** | Optional in UBL; `AccountingCustomerParty` with `CompanyID` when `buyer_tax_number` provided. |
| Mandatory: UUID | **PASS** | `cbc:UUID` in header when `request.uuid` present; Phase-2 validation requires UUID, so it is always set for Phase-2. |
| Mandatory: Issue Date (UTC) | **PASS** | `xml_generator` uses `normalize_invoice_date_to_utc(request.invoice_date)`; `IssueDate` and `IssueTime` are formatted from UTC. |
| Mandatory: Previous Invoice Hash | **PASS** | `_generate_pih_reference()` emits `cac:AdditionalDocumentReference` with `cbc:ID` = "PIH" and `cbc:EmbeddedDocumentBinaryObject` (64 hex) when `previous_invoice_hash` is present; omitted for first invoice. |
| VAT totals (15%) & invoice line items | **PASS** | `TaxTotal` with `TaxSubtotal`, `TaxableAmount`, `TaxAmount`, `TaxCategory` (S), `Percent` (15). Line items have `TaxTotal`/`TaxSubtotal`; totals derived from line items. |
| Digital signature structure | **PASS** | XMLDSig `Signature`, `SignedInfo`, `CanonicalizationMethod` (C14N URI), `SignatureMethod` (RSA-SHA256), `Reference` (URI=""), `DigestMethod` (SHA-256), `SignatureValue`, `X509Certificate`. |
| Canonicalization | **PASS** | When lxml is available, `_canonicalize_xml_for_signing()` uses W3C C14N (`_canonicalize_xml_c14n()`); Signature element excluded before digest. Fallback to line-based when lxml not installed (e.g. sandbox placeholder). |

**Verdict (1):** **PASS** — PIH in XML, Issue Date UTC, and C14N implemented.

---

## 2. ZATCA SDK Validation

| Check | Result | Evidence / Notes |
|-------|--------|------------------|
| Simulate ZATCA CLI validation | **NOT IMPLEMENTED** | No in-repo ZATCA SDK/CLI or schema validation step. Cannot simulate SDK result. |
| Schema / signature / QR errors | **N/A** | Recommend running ZATCA Compliance SDK/validator (e.g. `zatca validate`) on a generated signed XML and QR. |
| SDK-level acceptance | **PENDING VERIFICATION** | PIH, base64, UTC, and C14N are in place; run official ZATCA validator to confirm. |

**Verdict (2):** **N/A** — No SDK simulation in codebase; **recommend** running ZATCA Compliance SDK/CLI on generated invoices to confirm acceptance.

---

## 3. Phase-1 & Phase-2 Requirements

| Check | Result | Evidence / Notes |
|-------|--------|------------------|
| Phase-1 QR (TLV) | **PASS** | `phase1/qr_service.py`: Tags 1–5 (Seller Name, Seller VAT, Timestamp ISO 8601 with Z, Invoice Total, VAT Amount). TLV format Tag(1) + Length(1) + Value. |
| Phase-2 QR | **PASS** | `phase2/qr_service.py`: Tags 1–7 (same 1–5 + XML Hash, Digital Signature). Entire TLV base64-encoded for QR. Signature as UTF-8 bytes (base64 string). |
| Phase-2 clearance & reporting | **PASS** | Clearance and reporting flows implemented; OAuth; retries; 401 refresh. |
| Hash chaining logic | **PASS** | PIH emitted in XML via `_generate_pih_reference()` when `previous_invoice_hash` is present; chain verifiable by ZATCA. |
| First-invoice handling | **PASS** | `previous_invoice_hash` is optional for Phase-2; when omitted or empty, no PIH block is emitted (first invoice). Validator only checks PIH format when provided. |
| Invoice sequence integrity | **PARTIAL** | Invoice number uniqueness and PIH validation; PIH in XML. Invoice Counter Value (ICV) in XML — confirm against ZATCA spec if required. |

**Verdict (3):** **PASS** — Hash chaining and first-invoice handling implemented.

---

## 4. Sandbox Clearance API Validation

| Check | Result | Evidence / Notes |
|-------|--------|------------------|
| Authorization header | **PASS** | `sandbox.py`: `_get_auth_headers()` uses OAuth service; `Authorization: {token_type} {access_token}`. |
| Clearance-Status header | **PASS** | Used in `report_invoice` when `clearance_status` provided. |
| Language header | **IMPROVEMENT NEEDED** | No `Accept-Language` or `Language` in sandbox client. ZATCA may expect language for messages. |
| Base64 invoice payload | **PASS** | `submit_for_clearance` sends `invoice` as `base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")` in both sandbox and production clients. |
| CLEARED / REJECTED handling | **PASS** | Response parsed for `clearanceStatus`, `clearanceUUID`, `qrCode`; 4xx mapped to REJECTED with error message; retries on 5xx/timeout. |
| Error handling & retry | **PASS** | Exponential backoff, max retries, 401 → token refresh and retry; timeouts and server errors retried. |

**Verdict (4):** **PASS** — Base64 clearance payload implemented; **IMPROVEMENT NEEDED** for Language header (optional).

---

## 5. VAT Logic Validation

| Check | Result | Evidence / Notes |
|-------|--------|------------------|
| 15% VAT for standard rate | **PASS** | `Phase2Validator.REQUIRED_VAT_RATE = 15.0`; standard (S) items must use 15%. |
| Zero-rated / exempt | **PASS** | Tax categories Z and E; validator enforces 0% for Z and E. |
| Rounding & consistency | **PASS** | Line `tax_amount = taxable_amount * (tax_rate/100)`; totals from line items; tolerance 0.01 in validator; invoice_service overrides payload totals from calculated sums. |
| VAT totals vs line items | **PASS** | `_validate_data_consistency` and pre-clearance checks ensure totals match sum of line VAT and taxable amounts. |

**Verdict (5):** **PASS**.

---

## 6. Security & Cryptography

| Check | Result | Evidence / Notes |
|-------|--------|------------------|
| CSR (VAT, CR, CN, device) | **PARTIAL** | `zatca_service.py`: CSR has CN, O, OU, C, etc. ZATCA often expects specific subject (e.g. VAT number or device/serial in CN). No enforced ZATCA subject structure. |
| Certificate usage (sandbox vs production) | **PASS** | SANDBOX uses placeholder signature; PRODUCTION uses real RSA-SHA256 with cert/key from config. |
| Certificate–private key verification | **PASS** | `certificate_service._verify_certificate_private_key_match` compares RSA public numbers (modulus, exponent). |
| Key storage | **PASS** | Tenant-isolated paths; file permissions 600. |
| Key rotation | **PASS** | New certificate upload deactivates previous certificate. |
| Certificate expiry before sign | **IMPROVEMENT NEEDED** | Expiry checked on upload; no pre-signing expiry check — risk of signing with expired cert. |

**Verdict (6):** **PASS** for usage and verification; **IMPROVEMENT NEEDED** for CSR subject rules and pre-sign expiry check.

---

## 7. Readiness Assessment

| Question | Answer |
|----------|--------|
| Ready for ZATCA sandbox compliance submission? | **YES.** PIH in XML, base64 clearance payload, Issue Date/Time UTC, W3C C14N for signing, and first-invoice PIH (optional) are implemented. Run ZATCA SDK/validator and submit a test invoice to sandbox to confirm. |
| Blockers for production CSID usage? | **REDUCED.** Remaining: pre-sign certificate expiry check; optional Language header and ZATCA-specific CSR subject. |
| Recommended improvements before go-live? | See Section 8 checklist (remaining actions). |

---

## 8. Final Verdict & Checklist

### Overall Compliance Status: **READY FOR SANDBOX** *(pending ZATCA SDK/validator run)*

### Risk Level: **LOW–MEDIUM**

- **Remediated:** PIH in XML, base64 clearance payload, Issue Date UTC, W3C C14N for signing, first-invoice PIH (optional).
- **Remaining:** Pre-sign certificate expiry check; optional Language header and CSR subject; run ZATCA SDK/validator and sandbox clearance test.

### Completed Actions (remediation applied)

1. **PIH in UBL XML** — `xml_generator._generate_pih_reference()`; `cac:AdditionalDocumentReference` with `cbc:ID` = "PIH" and `cbc:EmbeddedDocumentBinaryObject` (64 hex); omitted when `previous_invoice_hash` absent (first invoice).
2. **Clearance API payload** — Sandbox and production send `invoice` as base64-encoded signed XML.
3. **Issue Date/Time UTC** — `normalize_invoice_date_to_utc()` in `time_utils`; header uses it in `xml_generator`.
4. **Canonicalization** — W3C C14N via `_canonicalize_xml_c14n()` (lxml) when available; Signature excluded before digest.
5. **First-invoice PIH** — `previous_invoice_hash` optional for Phase-2; no PIH block when omitted.

### Exact Checklist of Remaining Actions

1. **Run ZATCA Compliance SDK/validator** on a generated signed invoice (and QR) to confirm schema/signature/QR acceptance.
2. **Submit a test invoice to ZATCA sandbox** (first invoice + one with PIH) and confirm CLEARED response.
3. **Pre-sign certificate expiry (MEDIUM)** — In `CryptoService.sign` (production path), before signing, load cert and check `not_valid_after_utc`; reject or raise if expired.
4. **Optional** — Add `Accept-Language` or `Language` header for clearance/reporting if required by ZATCA; align CSR subject with ZATCA if specified; run ZATCA SDK/CLI in CI.

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-31 | Compliance Audit | Initial structured audit (8 sections, verdict, checklist). |
| 1.1 | 2026-01-31 | Compliance Audit | Post-remediation update: PIH in XML, base64 clearance, UTC dates, C14N, first-invoice handling; status READY FOR SANDBOX; checklist updated. |
