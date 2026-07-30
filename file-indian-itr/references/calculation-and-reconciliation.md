# Calculation and reconciliation

## Contents

1. Current-law gate
2. Evidence hierarchy
3. Reconciliation worksheet
4. Form and regime selection
5. Salary and other-source calculations
6. Capital gains and losses
7. Tax, rebate, and credits
8. Portal error patterns
9. Pre-submission invariants

## 1. Current-law gate

Before calculating:

1. Map the financial year to the assessment year.
2. Verify the applicable Act, notified ITR forms, instructions, validation rules, rates, deductions, rebates, holding periods, exemptions, and due dates.
3. Prefer primary official sources:
   - Income Tax Department and e-Filing portal;
   - CBDT notifications, circulars, utilities, schemas, and validation rules;
   - Finance Act, Finance Bill memorandum, and official Budget documents.
4. Record the source URL/title and effective assessment year for every load-bearing rule.
5. Treat blogs, tax platforms, search snippets, and remembered rules as leads only.

Do not carry a prior year’s standard deduction, section 87A threshold, capital-gains rate, exemption limit, or ITR eligibility into a new year without verification.

## 2. Evidence hierarchy

Use the most direct evidence for each fact:

| Fact | Primary evidence | Reconciliation evidence |
|---|---|---|
| Salary and employer details | Form 16, payslips, settlement | AIS/TIS, portal prefill, Form 26AS |
| TDS/TCS credit | Form 26AS, certificates | AIS/TIS, challans |
| Bank interest | Bank interest certificate or full statement | AIS/TIS |
| Dividend | Registrar/broker/company statement | AIS/TIS |
| Capital gains | Broker tax report plus tradebook/CAS | AIS/TIS, contract notes |
| Property income/sale | Agreements, deeds, lender/municipal records | AIS/TIS |
| Foreign asset/income | Foreign institution statements and tax records | Payroll/broker summaries |
| Prior loss | Filed prior ITR and acknowledgement | Current prefill |

AIS/TIS can contain duplicates, stale reports, category errors, or per-source rounding. Portal prefill is assistance, not a substitute for reconciliation.

## 3. Reconciliation worksheet

Preserve source precision. For each line capture:

```text
source | account/entity | description | statutory head | section
gross | exempt | deductible expense | cost | taxable | TDS/TCS
transaction/accrual date | portal schedule/field | exact value | filed value
```

Apply rounding only where the form or statute requires it. Do not round each micro-transaction and then sum unless the form explicitly does so. Explain a portal-prefill mismatch caused by per-source rounding; do not alter the evidence-backed total merely to match it.

For each source, check:

- correct taxpayer and PAN;
- complete financial-year date range;
- duplicate or missing pages/sheets;
- cash versus accrual treatment where relevant;
- gross versus net reporting;
- TDS/TCS shown separately from income;
- transaction expenses and corporate actions;
- exact sign for income, loss, tax paid, payable, and refund.

## 4. Form and regime selection

Use current official eligibility rules. Test all disqualifiers, not only income level.

Check:

- resident/RNOR/non-resident status;
- salary/pension and number of house properties;
- capital gains and VDA;
- business/profession, intraday, and F&O;
- foreign income/assets/signing authority;
- directorship and unlisted shares;
- agricultural and exempt income;
- brought-forward losses;
- special-rate or treaty income;
- representative assessee and other special status.

Compare old and new regimes using the same reconciled facts. Include:

- deductions/exemptions allowed in each;
- slab tax and special-rate tax;
- rebate eligibility and marginal relief;
- surcharge and cess;
- loss treatment;
- business-income restrictions and any separately required option form.

Explain the recommendation and preserve the user’s choice.

## 5. Salary and other-source calculations

For salary:

1. Reconcile every employer separately.
2. Separate section 17(1) salary, perquisites, and profits in lieu.
3. Reconcile exempt allowances and relief claims.
4. Apply the officially verified standard deduction exactly once.
5. Keep employer NPS and ESOP/deferred-tax facts distinct.

For other sources:

1. Aggregate exact savings and deposit interest across all institutions.
2. Report gross dividend; keep TDS separate.
3. Identify family pension, refund interest, gifts, winnings, and clubbed income.
4. Apply deductions only when currently allowed and evidenced.

Standard deduction and section 87A rebate are different stages:

- the standard deduction reduces salary income before total-income tax is calculated;
- section 87A, when eligible, reduces computed income tax afterward.

Verify the assessment-year amounts and whether special-rate income is excluded from rebate.

## 6. Capital gains and losses

For every disposal:

1. Verify asset type, acquisition date, disposal date, quantity, consideration, cost, and transfer expenses.
2. Apply current holding-period, rate, grandfathering, STT, and exemption rules.
3. Reconcile splits, bonuses, mergers, demergers, rights, and inherited/gifted cost.
4. Aggregate by the form’s statutory bucket only after transaction classification is correct.
5. Apply current-year and brought-forward set-off rules in the required order.
6. Reconcile Schedule CG, 112A/115AD/VDA, CYLA, BFLA, CFL, and SI.

Quarterly accrual Table F must match the post-set-off amount referenced from BFLA and the actual disposal/accrual dates. Example only: if listed-equity LTCG disposals occurred on 29 October, gross LTCG is 1,263, and a permitted current-year STCL of 495 is set off, the remaining 768 belongs in the 16 September–15 December column for the applicable LTCG row. Re-verify the section, rate, and set-off rule for the target year before using the example.

Do not carry a loss forward when CYLA/BFLA has fully absorbed it. Do not discard a valid carry-forward loss merely because current tax is zero.

## 7. Tax, rebate, and credits

Recompute independently:

```text
normal-rate income tax
+ special-rate income tax
- eligible rebate
+ surcharge
+ cess
+ interest and filing fee
- TDS/TCS/advance/self-assessment tax/other credit
= payable or refund
```

Check that:

- total income matches the sum of heads after set-off;
- special-rate income is not silently taxed at slab rates;
- rebate does not erase tax that is legally outside its scope;
- TDS/TCS is claimed only when supported and mapped to reported income;
- tax payments use the correct PAN, assessment year, minor/major head, and amount;
- the portal’s tax equals the independent computation.

If the portal tax differs, stop. Trace the difference to a field, rule, timing, or rounding decision before submission.

## 8. Portal error patterns

Treat validation messages as evidence, not instructions to invent data.

Common patterns:

- **Required dropdown blank:** edit the underlying entity and select the evidence-backed category.
- **Zero-value detail row with an invalid “NA” token:** delete the empty row when the item is genuinely absent; do not create a fake nature/value pair.
- **Quarterly capital-gain mismatch:** allocate the BFLA post-set-off amount to Table F using actual dates; make the row sum exact.
- **Unexpected ESOP/deferred-tax validation:** remove the inapplicable schedule instead of inventing employer/startup details.
- **Dependent schedule stale after an edit:** re-confirm CG/CYLA/BFLA/CFL/SI/TI/TTI or other downstream schedules and rerun validations.
- **Declaration reset:** require the taxpayer to review and check it again.
- **Prefill differs by a small amount:** compare exact aggregation and portal rounding; document the reason.

## 9. Pre-submission invariants

Before the taxpayer declares:

- every applicable category has evidence or an explicit, documented answer;
- every selected schedule is applicable and confirmed;
- no placeholder schedule or zero detail row creates a false disclosure;
- total income and head-wise income reconcile;
- losses set off and carried forward reconcile across all schedules;
- tax credits reconcile to Form 26AS/certificates/challans;
- payable/refund matches independent computation;
- bank account is validated/nominated as needed;
- internal and upload-level validation show zero errors;
- preview displays the intended name, PAN, AY, form, filing section, regime, income, tax, and disclosures.
