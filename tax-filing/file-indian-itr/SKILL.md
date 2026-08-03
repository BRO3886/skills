---
name: file-indian-itr
description: "Prepare, reconcile, validate, file, and e-verify an Indian income-tax return from a user-provided local document directory. Use when a user asks to collect tax documents, check whether anything is missing, choose the applicable ITR and tax regime, reconcile Form 16/AIS/TIS/26AS/bank/broker records, enter a return on the official Income Tax e-Filing portal, resolve validation errors, submit after explicit approval, or preserve the acknowledgement receipt."
---

# File Indian ITR

Prepare an evidence-backed Indian income-tax return from one local intake directory, then file it through the official portal with explicit taxpayer control over declarations, OTPs, and final submission.

## Load the references

- Read [references/intake-checklist.md](references/intake-checklist.md) before inventorying files or interviewing the user.
- Read [references/calculation-and-reconciliation.md](references/calculation-and-reconciliation.md) before selecting the ITR, tax regime, or figures.
- Read [references/portal-computer-use.md](references/portal-computer-use.md) before operating any browser or desktop UI.

## Apply these constraints

- Treat tax filing as high-stakes financial and legal work. Verify current rules for the relevant assessment year from primary official sources. Do not rely on remembered thresholds, rates, form eligibility, due dates, or portal labels.
- Use the official Income Tax e-Filing portal unless the user explicitly selects another provider. Do not route the user to ClearTax or another intermediary by default.
- Keep source documents local. Do not upload them to third parties or transmit sensitive data to a destination the user did not authorize.
- Keep the intake directory outside public or shared repositories. Never stage, commit, or publish taxpayer documents, extracted data, manifests, screenshots, or credentials.
- Never inspect browser cookies, password stores, local storage, session databases, or hidden credentials.
- Never invent an amount, classification, date, employer type, schedule, disclosure, tax credit, or required portal value. Resolve uncertainty from evidence or ask the user.
- Do not treat AIS/TIS or portal prefill as authoritative. Reconcile it with primary records.
- Do not call a return filed merely because a draft was saved or a validation passed. Require the portal’s filed-and-verified success state and a readable acknowledgement receipt.
- Keep PAN, Aadhaar, bank numbers, contact details, OTPs, and addresses out of routine progress messages. Mask them unless the user needs an exact identifier confirmed.

## Workflow

### 1. Establish authority and scope

Confirm:

- whose return is being filed and that the taxpayer authorizes the work;
- financial year and assessment year;
- original, revised, updated, belated, or defective-return response;
- official-portal filing versus preparation-only help;
- whether the user authorizes entering the supplied financial and identity data into the official portal.

The taxpayer must control login credentials, CAPTCHA, identity consent, OTP/EVC/DSC, the legal declaration, and any other authentication-only step.

### 2. Create one intake boundary

Ask the user to place every potentially relevant document for the financial year in one local directory. Include documents that may prove a zero, exemption, deduction, loss, or disclosure—not only obvious income statements.

Run:

```bash
python3 scripts/inventory_intake.py /absolute/path/to/intake
```

Use `--format json` when a machine-readable manifest helps. The script classifies filename hints only; inspect the contents before drawing conclusions.

Do not begin portal entry from a partial trickle of files. First inventory the directory, identify unreadable/password-protected files, detect duplicates, and build a source matrix.

If AIS, TIS, Form 26AS, or another official portal artifact is missing, ask the user to download it into the intake directory or, with authorization, download it from the logged-in official portal and save it there.

### 3. Run the completeness interview

Ask the applicability questions in the intake checklist even when no matching file exists. A missing file does not prove the income, asset, loss, deduction, or disclosure is absent.

Group the questions so the user can answer them in one pass. Follow up only on positive, uncertain, inconsistent, or incomplete answers. Record each category as:

- applicable with evidence;
- applicable but evidence missing;
- explicitly not applicable;
- unresolved.

Do not proceed while a material category remains unresolved.

### 4. Extract and reconcile

Read every relevant PDF, spreadsheet, CSV, statement, and receipt. Preserve exact source values before rounding. Build a worksheet with:

- source artifact and period;
- taxpayer/entity/account;
- income head and statutory section when known;
- gross amount, exemption, deduction, expenses, and taxable amount;
- TDS/TCS/tax paid;
- transaction or accrual date;
- portal schedule and field;
- discrepancy and resolution.

Cross-check the worksheet against AIS, TIS, Form 26AS, Form 16/16A, bank records, broker tax reports, prior returns, and challans. Investigate mismatches instead of forcing figures to match prefill.

### 5. Determine the return contract

Using current official guidance, decide and explain:

- applicable ITR form;
- residential and ordinarily-resident status;
- filing section and due-date status;
- old versus new regime, including a comparison where choice exists;
- schedules required;
- losses available for set-off or carry-forward;
- special-rate income;
- tax credits, interest, fee, payable amount, or refund;
- disclosures and forms that must be filed separately.

Escalate to a qualified tax professional when the facts exceed reliable handling—for example unclear residency, treaty positions, foreign trusts, disputed ownership, complex business books, valuation disputes, or unresolved notices. Do not conceal the gap with guesses.

### 6. Present a pre-entry review

Before editing the portal, give the user a compact calculation summary:

- gross income by head;
- exemptions and deductions;
- total income;
- normal-rate and special-rate tax;
- rebate, surcharge, cess, interest, and fee;
- TDS/TCS/tax payments;
- expected payable or refund;
- capital losses set off or carried forward;
- unresolved assumptions, if any.

Obtain approval for portal entry when it was not already explicit.

### 7. Enter through controlled computer use

Follow the portal computer-use reference. Prefer semantic DOM/accessibility controls over pixels. After every meaningful action:

1. observe current state;
2. identify the exact control from fresh state;
3. act;
4. wait for navigation/loading;
5. observe again;
6. verify the intended value or state.

Confirm every selected schedule. Remove inapplicable schedules and empty placeholder rows instead of fabricating values to satisfy validation.

### 8. Validate in layers

Run all validation stages exposed by the portal:

1. schedule completeness and recomputation;
2. internal validation;
3. preview review;
4. upload-level validation;
5. submit-level validation.

For every error:

- copy the exact field and message;
- trace it to the source evidence and dependent schedules;
- correct the root field;
- re-confirm all affected schedules;
- re-check totals and tax;
- rerun every downstream validation.

Any edit after declaration invalidates the prior declaration. Require the taxpayer to review and check it again.

### 9. Submit and e-verify

At action time:

- have the taxpayer personally check the legal declaration;
- state the final total income and payable/refund;
- obtain explicit confirmation immediately before irreversible submission;
- prefer immediate e-verification unless the taxpayer chooses another valid method;
- hand off Aadhaar consent and OTP/EVC/DSC entry to the taxpayer;
- obtain a final “submit” instruction when the portal warns that the return can no longer be modified.

Do not expose or retain OTPs.

### 10. Prove completion

After submission:

- verify the portal explicitly says the return was successfully filed and verified;
- download the acknowledgement receipt;
- read the receipt and confirm taxpayer name, masked or exact PAN as appropriate, form, assessment year, filing section, filing date, total income, tax payable/refund, verification mode, and acknowledgement number;
- report the receipt path and acknowledgement number;
- distinguish filed-but-unverified from filed-and-verified.

If the receipt cannot be downloaded or parsed, report the coverage gap and verify filing status from the portal’s filed-returns view before claiming completion.

## Stop conditions

Stop and ask rather than infer when:

- the assessment year or taxpayer identity is ambiguous;
- authorization to file for another person is unclear;
- a relevant document is missing, unreadable, or outside the stated period;
- source records materially disagree;
- form eligibility or residency is uncertain;
- portal tax differs from the reconciled calculation;
- a new tax payment is required;
- the portal asks for an unexpected declaration, consent, or disclosure;
- authentication or CAPTCHA requires the taxpayer;
- final submission lacks explicit action-time approval.
