# ZATCA Phase-2 Blocker Fix Guide

**Purpose:** Minimal, production-safe corrections to clear the five Phase-2 audit blockers.  
**Audience:** Engineers implementing ZATCA sandbox and production approval.

---

## A. UBL XML Fix — Previous Invoice Hash (PIH)

### A.1 Exact UBL 2.1 structure required by ZATCA

ZATCA requires the Previous Invoice Hash in the invoice XML so the hash chain can be verified. Use **one** `cac:AdditionalDocumentReference` with ID `"PIH"` and the hash in `cbc:EmbeddedDocumentBinaryObject`:

```xml
<cac:AdditionalDocumentReference>
  <cbc:ID>PIH</cbc:ID>
  <cac:Attachment>
    <cbc:EmbeddedDocumentBinaryObject characterSetCode="UTF-8" encodingCode="Base64" filename="previous_invoice_hash.txt" mimeCode="text/plain">
      [BASE64_OF_64_HEX_PIH]
    </cbc:EmbeddedDocumentBinaryObject>
  </cac:Attachment>
</cac:AdditionalDocumentReference>
```

**Important:** Some ZATCA implementations expect the raw 64-character hex string (no Base64). The E-Invoicing Technical Guideline often specifies the hash as **plain text** inside the element. Safer option for maximum compatibility:

```xml
<cac:AdditionalDocumentReference>
  <cbc:ID>PIH</cbc:ID>
  <cac:Attachment>
    <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain" encodingCode="UTF-8">
      [64_HEX_CHARACTERS_LOWERCASE]
    </cbc:EmbeddedDocumentBinaryObject>
  </cac:Attachment>
</cac:AdditionalDocumentReference>
```

Use the **64-character lowercase hex string** directly (no Base64) unless your ZATCA Developer Portal / SDK explicitly requires Base64-encoded PIH.

### A.2 Where it must appear in the Invoice XML

Per UBL 2.1 and ZATCA ordering:

- **After** the main header elements: `cbc:ID`, `cbc:IssueDate`, `cbc:IssueTime`, `cbc:InvoiceTypeCode`, `cbc:UUID` (and `cbc:DocumentCurrencyCode` if present).
- **Before** `cac:AccountingSupplierParty`.

Typical order:

1. `cbc:ID` (invoice number)  
2. `cbc:IssueDate`  
3. `cbc:IssueTime`  
4. `cbc:InvoiceTypeCode`  
5. `cbc:UUID`  
6. **`cac:AdditionalDocumentReference` (PIH)** ← here  
7. `cac:AccountingSupplierParty`  
8. …rest of invoice

So: **immediately after the invoice header block, before the first party (seller).**

### A.3 First-invoice handling

- **Option 1 (recommended): Omit PIH for the first invoice.**  
  For the very first invoice in the chain there is no “previous” invoice. Do **not** emit `cac:AdditionalDocumentReference` with `cbc:ID = "PIH"` for that invoice.  
  - In code: only add the PIH block when `previous_invoice_hash` is present and non-empty.  
  - API: make `previous_invoice_hash` **optional** for Phase-2; when omitted, treat as first invoice and do not add PIH to XML.

- **Option 2: Use a well-known value.**  
  Some implementations use a fixed value for the first invoice (e.g. 64 zero hex `0`×64). Only use this if ZATCA documentation or SDK explicitly requires it; otherwise omit.

**Recommendation:** Omit PIH for the first invoice (Option 1). No `AdditionalDocumentReference` for PIH when there is no previous invoice hash.

---

## B. Clearance Payload Fix — Base64 Invoice

### B.1 Correct ZATCA clearance request body

ZATCA Developer Portal and E-Invoicing Technical Guideline require the **invoice payload to be base64-encoded**. The request body must send the **signed XML as a base64 string**, not raw XML.

**Correct body (sandbox and production):**

```json
{
  "invoice": "<BASE64_ENCODED_SIGNED_XML_STRING>",
  "uuid": "<INVOICE_UUID>"
}
```

- `invoice`: **Base64** encoding of the **entire** signed invoice XML (UTF-8 bytes).  
- `uuid`: Invoice UUID string (unchanged).

### B.2 Base64 encoding requirements

- **Input:** Signed XML string (UTF-8).  
- **Process:** `base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")`.  
- **Output:** No newlines or padding changes unless the API spec says otherwise; standard Base64 is fine.

### B.3 Before / after comparison

**Before (incorrect — raw XML):**

```json
{
  "invoice": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Invoice xmlns=\"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2\">...</Invoice>",
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**After (correct — base64):**

```json
{
  "invoice": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPEludm9pY2UgeG1sbnM9InVybjphb2FzaXM6bmFtZXM6c3BlY2lmaWNhdGlvbjp1Ymw6c2NoZW1hOnhzZDpJbnZvaWNlLTIiPi4uLjwvSW52b2ljZT4=",
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

In code: always send `invoice` as the base64 string; never send raw XML in `invoice`.

---

## C. Issue Date Normalization (UTC)

### C.1 How IssueDate and IssueTime must be generated

- ZATCA expects **UTC** for issue date/time.  
- **IssueDate:** `YYYY-MM-DD` (date in UTC).  
- **IssueTime:** `HH:MM:SS` (time in UTC). Optionally append `Z` in some specs; UBL 2.1 often uses separate date and time; both must represent the same moment in UTC.

### C.2 Safe normalization when client sends local time

1. **If the client sends a timezone-aware datetime:**  
   Convert to UTC: `dt_utc = dt.astimezone(timezone.utc)` (or equivalent). Then format `IssueDate` and `IssueTime` from `dt_utc`.

2. **If the client sends a naive datetime:**  
   - **Option A (recommended):** Treat as UTC only if you document that “all invoice times must be in UTC.” Then use it as-is for formatting.  
   - **Option B:** Treat as server local time and convert to UTC:  
     `dt_utc = dt.replace(tzinfo=server_local_tz).astimezone(timezone.utc)`.

3. **Format in XML:**  
   - `IssueDate`: `dt_utc.strftime("%Y-%m-%d")`  
   - `IssueTime`: `dt_utc.strftime("%H:%M:%S")` (or with `Z` if required: `dt_utc.strftime("%H:%M:%SZ")` — confirm with ZATCA schema).

**Implementation:** Add a small helper, e.g. `normalize_invoice_date_to_utc(dt)`, that returns a UTC datetime (timezone-aware). Use that result for all XML date/time output so IssueDate/IssueTime are always UTC.

---

## D. Canonicalization (W3C C14N)

### D.1 Why W3C Canonical XML is required for ZATCA signatures

- The digest in the signature is computed over a **canonical** form of the document.  
- If canonicalization is not W3C C14N, different serializations (whitespace, attribute order, namespaces) produce different bytes and thus different hashes.  
- ZATCA (and any XMLDSig verifier) will recompute the digest using **W3C Canonical XML 1.0** (C14N). If your signing pipeline uses something else (e.g. “line-based” or “strip whitespace”), the digest will not match and the signature will **fail verification**.

So: **canonicalization before hashing and signing must be W3C C14N** (algorithm: `http://www.w3.org/TR/2001/REC-xml-c14n-20010315`).

### D.2 Correct canonicalization flow before hashing and signing

1. **Input:** Unsigned invoice XML (no `<Signature>` element).  
2. **Canonicalize:** Apply W3C C14N to the **document element** (e.g. `<Invoice>`) **excluding** the `<Signature>` subtree (signature is not part of the signed content).  
   - In practice: build the invoice DOM, then serialize to canonical form using C14N (e.g. `lxml.etree` with `method="c14n"` or equivalent).  
   - The signed content is the invoice without the Signature node.  
3. **Hash:** SHA-256 of the **UTF-8 bytes** of the canonical form.  
4. **Sign:** Sign that hash (e.g. RSA-SHA256); put the result and the cert in the `<Signature>` element.  
5. **Enveloped:** Insert the `<Signature>` into the invoice so the final document is Invoice + Signature.

Important: the **Reference** in XMLDSig points to the document (e.g. `URI=""`) and uses Transform “enveloped-signature” so the Signature is **excluded** when computing the digest. The canonical form that is hashed must be the invoice **without** the Signature element.

### D.3 Common mistakes that cause signature rejection

- **Using non-C14N canonicalization** (e.g. line-based strip, “pretty print”) so the digest does not match what ZATCA computes.  
- **Including the Signature element in the digested content** — must be excluded via enveloped-signature transform.  
- **Wrong namespace handling** — C14N expands namespaces and sorts attributes; ad-hoc string handling usually gets this wrong.  
- **Encoding:** Digest must be over UTF-8 bytes of the canonical form.  
- **Changing the document after computing the digest** (e.g. adding or moving elements) so the digest no longer matches.

Use a proper C14N implementation (e.g. `lxml` C14N) for the byte string that is hashed and signed.

---

## E. Final Verification Checklist

When all of the below are done and verified, you can treat the system as ready for ZATCA SDK validation, sandbox clearance, and Production CSID request.

### E.1 XML and business rules

- [ ] **PIH in XML:** Every non–first invoice has one `cac:AdditionalDocumentReference` with `cbc:ID = "PIH"` and the previous invoice hash (64 hex) in `cbc:EmbeddedDocumentBinaryObject`. First invoice has no PIH block.
- [ ] **PIH position:** PIH block appears after header (ID, IssueDate, IssueTime, InvoiceTypeCode, UUID) and before `cac:AccountingSupplierParty`.
- [ ] **First invoice:** When `previous_invoice_hash` is omitted or empty, no PIH block is emitted; when provided, PIH is emitted and must be valid 64 hex.

### E.2 Clearance API

- [ ] **Base64 payload:** Clearance request body sends `"invoice": "<base64 of signed XML>"` and `"uuid": "<uuid>"` (no raw XML in `invoice`).
- [ ] **Sandbox and production:** Same payload format for both environments (base64 invoice).

### E.3 Date/time

- [ ] **UTC:** IssueDate and IssueTime are derived from a single UTC moment (timezone-aware or normalized to UTC).
- [ ] **Format:** IssueDate `YYYY-MM-DD`, IssueTime `HH:MM:SS` (or per ZATCA schema).

### E.4 Signing and C14N

- [ ] **C14N:** The digest for the signature is computed over the **W3C C14N** form of the invoice (without the Signature element).
- [ ] **Algorithm:** CanonicalizationMethod uses `http://www.w3.org/TR/2001/REC-xml-c14n-20010315`.
- [ ] **No ad-hoc canonicalization** for production signing (no line-based or string-strip canonicalization for the digest).

### E.5 Validation and runtime

- [ ] **ZATCA SDK:** Run ZATCA Compliance SDK/validator on a generated signed invoice; no schema/signature/QR errors.
- [ ] **Sandbox clearance:** Submit a test invoice to sandbox; response is **CLEARED** (no REJECTED due to schema/signature/QR/PIH).
- [ ] **Production readiness:** Cert and key valid; pre-sign certificate expiry check in place; environment separation (sandbox vs production) correct; CSR subject aligned with ZATCA if required.

### E.6 Guarantees when checklist is complete

- **ZATCA SDK validation passes** — XML structure, PIH, signature digest, and QR align with ZATCA rules.  
- **Sandbox clearance returns CLEARED** — Request format (base64 invoice, UUID), PIH, and signature are accepted.  
- **Ready for Production CSID request** — Same XML and API behavior as sandbox, with production cert and correct C14N and UTC handling.

---

## Implementation summary (code changes)

| Blocker | Where | What was done |
|---------|--------|----------------|
| **A. PIH in XML** | `backend/app/services/phase2/xml_generator.py` | Added `_generate_pih_reference()`; emit `cac:AdditionalDocumentReference` with `cbc:ID` = "PIH" and `cbc:EmbeddedDocumentBinaryObject` (64 hex) after header, only when `previous_invoice_hash` is present. |
| **First-invoice** | `backend/app/schemas/invoice.py`, `backend/app/services/phase2/validator.py`, `backend/app/main.py` | Phase-2 no longer requires `previous_invoice_hash`; optional = first invoice. Validator only checks PIH format when provided. |
| **B. Base64 clearance** | `backend/app/integrations/zatca/sandbox.py`, `backend/app/integrations/zatca/production.py` | Clearance request body sends `invoice` as `base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")`. |
| **C. Issue Date UTC** | `backend/app/utils/time_utils.py`, `backend/app/services/phase2/xml_generator.py` | Added `normalize_invoice_date_to_utc(dt)`; header uses it for `IssueDate` and `IssueTime`. |
| **D. C14N** | `backend/app/services/phase2/crypto_service.py`, `backend/requirements.txt` | Added `lxml>=5.0.0`; `_canonicalize_xml_for_signing()` uses `_canonicalize_xml_c14n()` (W3C C14N, Signature excluded) when lxml is available; fallback to line-based for sandbox. |

---

## Document control

| Version | Date       | Description                    |
|---------|------------|--------------------------------|
| 1.0     | 2026-01-31 | Initial fix guide (A–E).      |
| 1.1     | 2026-01-31 | Implementation summary.      |
