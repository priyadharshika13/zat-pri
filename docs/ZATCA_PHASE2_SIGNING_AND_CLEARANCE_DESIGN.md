# ZATCA Phase-2 Signing and Clearance — Audit-Grade Design

**Document type:** Compliance design and enforcement specification  
**Audience:** Developers, auditors, certification reviewers  
**Constraint:** Phase-1 logic remains untouched. No unsigned or fake-signed invoice may ever reach ZATCA.

---

## 1. Executive summary

This document defines how Phase-2 e-Invoicing **must** behave to satisfy ZATCA regulatory and certification expectations. It is written from the perspective of a ZATCA reviewer: the system must demonstrate **legal validity**, **non-repudiation**, and **audit traceability** for every Phase-2 invoice submitted to clearance. The design is strict by intention—no “best effort” or fallback that could send non-compliant data to ZATCA.

---

## 2. Regulatory context: why these rules exist

### 2.1 Legal validity (VAT Law and E-Invoicing Regulation)

- In Saudi Arabia, e-invoices that are **cleared** with ZATCA have legal effect for VAT and commercial records.
- Only **digitally signed** invoices, using a key/certificate bound to the **taxpayer (seller)**, are considered valid for clearance.
- **Unsigned or placeholder-signed** XML has no legal standing. Submitting it to ZATCA would:
  - Violate the e-invoicing regulation.
  - Create risk of rejection, penalties, or failed certification.
- **Rule:** Every byte sent to the ZATCA clearance API must be signed with a **real** private key and certificate for the correct tenant and environment.

### 2.2 Non-repudiation

- The taxpayer must not be able to deny having issued the invoice. This is achieved by:
  - Signing with a **private key** only they possess.
  - Using a **certificate** issued (or recognized) by ZATCA that binds identity to that key.
- If the system ever uses a **shared**, **test**, or **placeholder** signature for clearance:
  - Non-repudiation is broken.
  - An auditor would treat the submission as non-compliant.
- **Rule:** No shared keys, no placeholder signatures, and no “sandbox-only” signing path that could be misused or confused with production.

### 2.3 Audit traceability

- ZATCA and internal audits must be able to:
  - Trace each cleared invoice to the **tenant** that submitted it.
  - Verify that the **correct certificate** (per tenant, per environment) was used.
  - Confirm that **only cryptographically valid** signed XML was sent to ZATCA.
- If certificate resolution is **global** (one key for all tenants) or **best-effort** (fallback to placeholder), traceability and isolation are compromised.
- **Rule:** Certificate resolution must be **per request, per tenant, per environment**. Fail explicitly when assets are missing; never substitute another tenant’s cert or a placeholder.

---

## 3. Phase-2 signing architecture (strict)

### 3.1 Principles

| Principle | Requirement |
|-----------|-------------|
| **Real signing only** | Every Phase-2 invoice is signed with a real private key and certificate (.pem). No placeholder or “fake” signature may ever be used for the payload sent to ZATCA. |
| **Per-tenant mandatory** | Each taxpayer (tenant) has its own certificate and private key. The system must resolve and use **only** that tenant’s assets for signing. |
| **Environment separation** | Sandbox and Production use different certificate directories and (in production) different ZATCA-issued certs. No production cert in sandbox path, no sandbox cert in production path. |
| **Fail closed** | If signing assets are missing, invalid, or signing fails, the API **must fail** the request. No silent fallback, no “best effort” clearance. |

### 3.2 Certificate layout (mandatory)

```
certs/
├── tenant_<tenant_id>/
│   ├── sandbox/
│   │   ├── privatekey.pem
│   │   └── certificate.pem
│   └── production/
│       ├── privatekey.pem
│       └── certificate.pem
```

- **tenant_id** is the authenticated tenant (e.g. from API key). No other tenant_id may be used for resolution.
- **sandbox** and **production** are the only allowed environment segments. Paths must be resolved from **request** (e.g. `request.environment` or equivalent), not from a single global config.
- Optional: global fallback paths (e.g. `SIGNING_KEY_PATH` / `SIGNING_CERTIFICATE_PATH`) may be used **only** when the design explicitly allows a “single-tenant” or dev mode and it is **documented and auditable**. For multi-tenant production, **per-tenant paths are mandatory**.

### 3.3 Resolution rules (per request)

1. **Resolve certificate paths once per Phase-2 request:**
   - Inputs: authenticated `tenant_id`, target `environment` (SANDBOX or PRODUCTION).
   - Output: paths to `privatekey.pem` and `certificate.pem` for that tenant and environment.
2. **No global caching of “current” cert:** Resolution must use `tenant_id` and `environment` from the **current request**, not from a previous request or a global default.
3. **If resolution fails** (files missing, path outside allowed tree, or invalid env): **do not** attempt clearance. Return **503** (see Section 6).

---

## 4. Hard enforcement rules

### 4.1 No unsigned or placeholder-signed XML to ZATCA

- **Rule:** Only XML that has been signed with the **real** private key and certificate for the requesting tenant and environment may be passed to the ZATCA clearance API.
- **Implications:**
  - Any code path that can call `submit_clearance` / `submit_for_clearance` must receive XML that the system has just signed with real keys (or that has been verified as such in a single, auditable flow).
  - There must be **no** code path where:
    - Unsigned XML is sent to clearance, or
    - Placeholder/fake/test signatures are sent to clearance.
- **Sandbox:** If the business decision is to allow “test” or “sandbox” certificates for sandbox clearance, that is acceptable **only** if the signature is still **cryptographically real** (real key + cert in `certs/tenant_<id>/sandbox/`). Placeholder or algorithmically fake signatures must **never** be sent to ZATCA, including in sandbox.

### 4.2 Missing or invalid signing assets → fail immediately

- **Rule:** If, for the requesting tenant and environment, the private key or certificate is missing, unreadable, or invalid, the system must **not** sign and **not** call clearance.
- **Behavior:** Fail the request **immediately** (e.g. right after resolution or at the start of signing). Do not attempt retries with different keys or fallback to another tenant’s cert.
- **HTTP status:** **503 Service Unavailable** with a clear, non-sensitive message (e.g. “Signing is not available for this tenant/environment. Please upload or configure the required certificate and key.”). See Section 6.

### 4.3 503 for signing unavailability (not 500)

- **Rule:** When the failure is due to **signing configuration** (missing/invalid key or cert, or signing service unavailable), the API must return **503**, not 500.
- **Reason:** 500 implies an unexpected server error. Unavailable or misconfigured signing is a **known** operational state that the client (or operator) can remedy (e.g. upload certs, fix paths). Using 503 allows monitoring and runbooks to treat “signing unavailable” distinctly from generic server errors.

---

## 5. Clearance boundary

### 5.1 Single crossing point

- **Rule:** There must be a **single**, well-defined boundary where XML is passed to the ZATCA clearance client (e.g. `submit_clearance(signed_xml=...)` or equivalent).
- **Contract:** The only XML that may cross this boundary is XML that:
  1. Was generated for the current invoice (UBL, schema-compliant).
  2. Was **just** signed in this request with the **resolved** tenant key and certificate for the requested environment.
  3. Has not been altered after signing.
- **No fallback:** There must be no “if signing fails, submit anyway” or “use placeholder for sandbox” path that still calls the clearance API. If signing fails or is skipped, the flow must **not** reach the clearance call.

### 5.2 Validation before clearance (defence in depth)

- Before calling ZATCA, the system should validate (as already partially present):
  - Digital signature element is present and non-empty.
  - Signature algorithm and structure are as expected (e.g. RSA-SHA256, enveloped).
- Optional but recommended: verify that the certificate used for signing matches the resolved tenant/environment (e.g. thumbprint or path) so that no misrouted cert can be used. This is an extra check; the primary guarantee is that **only the real-signing path** feeds the clearance call.

---

## 6. Tenant isolation and security

### 6.1 One tenant’s certificate never used for another

- **Rule:** Certificate paths must be derived **only** from the authenticated tenant’s identity (e.g. `tenant_id` from API key or session). No other tenant’s path may be used.
- **Implementation:** Use a function like `get_tenant_cert_paths(tenant_id, environment)` that:
  - Takes **only** the current request’s `tenant_id` and `environment`.
  - Returns paths that lie under `certs/tenant_<tenant_id>/<environment>/`.
  - Validates that resolved paths stay under the allowed base and contain the expected `tenant_<id>` segment (path traversal protection).
- **No global “current” cert:** Do not hold a single global or request-agnostic cert; resolve per request.

### 6.2 Certificate paths resolved per request

- **Rule:** Path resolution must happen **per Phase-2 request**, using that request’s tenant and environment.
- **Rationale:** Caching or reusing “the last used” cert could lead to tenant A’s invoice being signed with tenant B’s key if requests are interleaved or configuration is shared. Per-request resolution keeps the model simple and auditable.

---

## 7. High-level Phase-2 workflow

The following flow must be enforced. Phase-1 is out of scope and remains unchanged.

```
Request (Phase-2 invoice)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. AUTH & TENANT RESOLUTION                                       │
│    Resolve tenant_id from API key / auth. Validate subscription   │
│    and write permission.                                          │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. RESOLVE SIGNING ASSETS (per request)                          │
│    get_tenant_cert_paths(tenant_id, request.environment)          │
│    → If missing/invalid: return 503, stop. No clearance.          │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. GENERATE UBL XML                                              │
│    Generate unsigned UBL 2.1 XML for this invoice.                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. SIGN (real key + cert only)                                   │
│    Sign XML with resolved tenant key and certificate.             │
│    → If signing fails: return 503, stop. No clearance.            │
│    → No placeholder, no fallback to unsigned/fake.               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. PRE-CLEARANCE VALIDATION                                      │
│    Validate signature present, structure correct, VAT math OK.    │
│    → If validation fails: return 400, stop. No clearance.          │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. CLEARANCE BOUNDARY (single call)                              │
│    submit_clearance(signed_xml=signed_xml, ...)                   │
│    Only this signed_xml may be sent. No other path.               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (clearance result)
```

- Steps 2 and 4 are **mandatory** and **fail-closed**: any failure means **no** call to ZATCA and a **503** for signing unavailability.
- Step 6 is the **only** place where XML is sent to ZATCA, and it receives only the XML produced by step 4 (and validated in step 5).

---

## 8. Error-handling contract (422 vs 403 vs 503)

Aligned with ZATCA and API best practices:

| HTTP | When to use | Example |
|------|-------------|--------|
| **422 Unprocessable Entity** | Request body is invalid or fails schema/validation (e.g. missing required field, invalid VAT number, future invoice date). | Missing `uuid`, invalid `seller_tax_number`, validation errors from UBL/business rules. |
| **403 Forbidden** | Authenticated but not allowed to perform this action (e.g. subscription limits, no production access, write action denied). | Expired subscription, production not allowed for plan, write disabled. |
| **503 Service Unavailable** | Signing or clearance dependency is unavailable or misconfigured. **Do not** use 500 for “key/cert missing or invalid”. | Tenant cert/key missing for this environment; signing failed due to key/cert; (optional) ZATCA gateway unreachable for clearance. |
| **500 Internal Server Error** | Reserved for **unexpected** server-side errors (e.g. bug, unexpected exception). **Not** for “certificate not found” or “signing failed” — those are 503. | Unhandled exception in non-signing logic (e.g. DB error, serialization error). |

- **Signing:** All “signing not possible” or “signing failed” outcomes (missing/invalid assets, crypto errors) → **503**.
- **Clearance:** If the design treats “ZATCA gateway down” as retryable and distinguishable, 503 is appropriate; if not, 502/504 may be used. Important: **never** send unsigned or placeholder-signed XML regardless of status code.

---

## 9. Sandbox vs production behavior

| Aspect | Sandbox | Production |
|--------|---------|------------|
| **Certificate source** | `certs/tenant_<id>/sandbox/`. May be test/self-signed or ZATCA sandbox certs. | `certs/tenant_<id>/production/`. Must be ZATCA-issued production certs. |
| **Signing algorithm** | Same as production (e.g. RSA-SHA256, C14N). **No** placeholder or fake signature for the payload sent to ZATCA. | Same; real signing only. |
| **Clearance endpoint** | ZATCA sandbox clearance API. | ZATCA production clearance API. |
| **Failure behavior** | Same as production: missing/invalid cert or key → 503; no unsigned/placeholder to ZATCA. | Same. |
| **Placeholder / “dev” mode** | **Not** allowed for any payload sent to ZATCA. Allowed only for **local** flows that **never** call clearance (e.g. “preview” or “validate only” endpoints that do not submit). | Not allowed anywhere. |

- **Summary:** Sandbox and production differ only by **which** certs and **which** ZATCA endpoint are used. The **rules** (real signing only, per-tenant resolution, 503 on missing/invalid assets, no unsigned/placeholder to ZATCA) apply in both.

---

## 10. Summary: what a ZATCA auditor would expect

1. **Every** Phase-2 clearance submission is signed with a **real** private key and certificate.
2. Certificates are **per tenant** and **per environment**; resolution is **per request**; no cross-tenant use.
3. **No** unsigned or placeholder-signed XML is ever sent to ZATCA; the only path to clearance goes through the real-signing flow.
4. Missing or invalid signing assets result in **immediate failure** and **503**, not 500 or silent fallback.
5. A **single, well-defined** clearance boundary; only cryptographically valid, just-signed XML crosses it.
6. **Sandbox** uses real (test/sandbox) certs and real signing; no “fake” signature for sandbox clearance.
7. **Phase-1** is unchanged; all strict rules apply only to Phase-2 signing and clearance.

This design is intended to be **production-ready**, **auditable**, and **certification-safe** from a ZATCA compliance perspective. Implementation should follow this specification so that the system behaves as a ZATCA reviewer would expect.
