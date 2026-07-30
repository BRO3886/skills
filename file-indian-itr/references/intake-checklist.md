# ITR intake and completeness checklist

## Contents

1. Intake-directory rule
2. Filing identity and baseline facts
3. Universal tax records
4. Income and asset categories
5. Deductions, losses, and tax credits
6. Disclosure and special-situation questions
7. Completeness interview
8. Evidence-status matrix

## 1. Intake-directory rule

Ask the user to create one directory for the financial year and put every potentially applicable source artifact in it before detailed analysis.

Keep this directory outside any public or shared source repository. Never commit its files, inventory, extracted values, or screenshots.

Good contents include:

- original PDFs, XLSX/CSV reports, statements, certificates, challans, notices, and prior acknowledgements;
- exports directly from employers, banks, brokers, registrars, and the Income Tax portal;
- a plain-text note listing facts that have no document;
- documents that support a deduction, exemption, loss, foreign disclosure, or zero balance.

Do not request passwords, OTPs, browser exports, cookies, or credential files. Ask the user to unlock a password-protected document locally or provide the password interactively only when the harness can use it without persisting or exposing it.

Prefer filenames that identify source and period without adding more sensitive data than necessary:

```text
form16-employer-a-fy2025-26.pdf
ais-ay2026-27.pdf
form26as-ay2026-27.pdf
bank-interest-hdfc-fy2025-26.pdf
broker-capital-gains-fy2025-26.xlsx
home-loan-interest-fy2025-26.pdf
prior-itr-ack-ay2025-26.pdf
```

Inventory before interpretation:

```bash
python3 scripts/inventory_intake.py /absolute/path/to/intake
```

The inventory’s category is a filename hint, not evidence. Inspect file contents.

## 2. Filing identity and baseline facts

Collect or confirm:

- taxpayer’s full legal name, PAN, date of birth, and status;
- taxpayer authorization when another person is coordinating;
- financial year and assessment year;
- current and secondary communication address;
- primary email and mobile registered on the portal;
- Aadhaar linkage and access to the Aadhaar-linked mobile;
- all bank accounts held during the year, their validation status, and refund nomination;
- original/revised/belated/updated/defective filing context;
- last filed return and acknowledgement;
- residential-status day counts and relevant prior-year presence;
- employment, retirement, business, and profession status;
- current portal access without sharing credentials.

Do not infer residence from an address or nationality. Ask the statutory presence and tie-breaker questions required for that assessment year.

## 3. Universal tax records

Request current downloads for the target assessment year:

- AIS;
- TIS;
- Form 26AS;
- prior-year ITR acknowledgement and computation;
- notices, defective-return messages, or pending compliance items;
- advance-tax and self-assessment-tax challans;
- Form 16A or other TDS certificates not included in salary Form 16;
- proof of TCS;
- Form 10E, Form 10-IEA, Form 67, or other separately filed forms when applicable.

AIS/TIS indicates what the department knows. Form 26AS supports tax-credit reconciliation. Neither replaces the underlying income records.

When an official report is absent and the user has authorized portal use, download it from the official portal into the same intake directory before reconciliation.

## 4. Income and asset categories

### Salary, pension, and employment benefits

Ask about every employer and pension payer:

- Form 16 for each employer;
- payslips, final settlement, bonus, arrears, gratuity, leave encashment, and pension;
- allowances or exemptions;
- perquisites;
- employer NPS contribution;
- ESOP/RSU allotment, exercise, sale, or deferred tax;
- foreign employer or overseas payroll;
- relief under section 89 and Form 10E.

Confirm employer nature from evidence. Do not leave required dropdowns blank or invent categories.

### House property

Ask about every owned, co-owned, inherited, let-out, deemed-let-out, or sold property:

- ownership share and possession dates;
- self-occupied versus let-out periods;
- rent, tenant details where required, and vacancy;
- municipal taxes actually paid;
- home-loan interest certificate and principal;
- lender, loan dates, and property details;
- pre-construction interest;
- co-owner and co-borrower allocation;
- brought-forward house-property loss.

### Listed shares, mutual funds, and other securities

Ask about every broker, demat account, registrar, and mutual-fund platform:

- tax capital-gains report;
- realised P&L;
- complete tradebook or transaction statement;
- demat/CAS statement;
- buy and sell dates, quantity, sale value, cost, expenses, and STT;
- grandfathering/FMV data where applicable;
- bonus, split, merger, demerger, rights, buyback, delisting, or other corporate action;
- intraday and F&O activity;
- dividends and income distributions;
- securities held through foreign brokers.

Do not assume “nothing else” means no second broker. Ask explicitly.

### Property, jewellery, and other capital assets

Ask about:

- sale or transfer deeds;
- stamp-duty value;
- purchase and improvement evidence;
- transfer expenses;
- valuation reports;
- inherited/gift history and previous-owner cost;
- exemption investment or deposit evidence;
- compulsory acquisition or insurance proceeds.

### Bank, deposit, and other-source income

Ask about every bank, cooperative bank, post office, wallet, and deposit:

- savings-account interest;
- FD/RD/term-deposit interest, including accrued interest;
- recurring or sweep deposits;
- joint accounts and beneficial ownership;
- family pension;
- interest on income-tax refund;
- gifts, awards, winnings, commission, or miscellaneous receipts;
- minor child or spouse income requiring clubbing;
- dividend statements from all sources.

Bank statements may be needed even when no interest certificate exists.

### Business and profession

Any business, freelancing, consulting, commission, partnership, intraday, or F&O activity may change the form and accounting requirements. Request:

- books, ledger, P&L, and balance sheet;
- invoices and expense evidence;
- GST returns and turnover reconciliation;
- presumptive-tax records;
- cash, receivables, payables, inventory, and fixed assets;
- audit report and tax-audit details;
- partnership/LLP interest, remuneration, and share of profit;
- depreciation schedule;
- brought-forward business losses and unabsorbed depreciation.

Do not force business income into ITR-1 or ITR-2.

### Virtual digital assets

Ask about crypto, tokens, NFTs, staking, mining, airdrops, gifts, and transfers across every exchange and wallet:

- transaction exports;
- rupee values and dates;
- TDS under applicable VDA provisions;
- wallet-to-wallet transfers;
- fees and cost records;
- foreign-exchange accounts.

Verify current rules on loss set-off and expenses.

### Foreign income and assets

Ask every resident taxpayer explicitly about:

- foreign bank, brokerage, retirement, custodial, and payment accounts;
- foreign shares, RSUs/ESOPs, mutual funds, insurance, trusts, entities, and real estate;
- beneficial ownership, beneficiary status, and signing authority;
- foreign salary, interest, dividend, rent, pension, and capital gains;
- foreign taxes paid and treaty relief;
- Form 67, tax-residency certificate, and foreign statements;
- peak balances and acquisition dates required by Schedule FA.

An Indian payroll or Indian address does not rule out foreign assets.

### Agricultural and exempt income

Ask about:

- agricultural income and land records;
- PPF and other exempt interest;
- tax-free maturity proceeds;
- exempt allowances;
- share of partnership-firm profit;
- gifts and exempt capital receipts.

Exempt income may still require disclosure.

## 5. Deductions, losses, and tax credits

Collect potentially applicable evidence even when the new regime is expected:

- provident fund, life insurance, tuition, ELSS, principal repayment, and other section 80C items;
- NPS contributions by taxpayer and employer;
- medical insurance, preventive check-up, and senior-citizen medical spending;
- donations with receipt, donee identifiers, payment mode, and qualifying percentage;
- education-loan interest;
- eligible home-loan deductions;
- disability and dependent-disability evidence;
- specified-disease treatment evidence;
- rent paid and landlord details where required;
- savings/deposit interest deductions;
- eligible electric-vehicle loan interest;
- any other current Chapter VI-A claim.

For losses and credits, request:

- prior returns and computations;
- Schedule CFL/BFLA history;
- capital-loss transaction evidence;
- house-property and business losses;
- MAT/AMT credit where relevant;
- all TDS/TCS certificates and challans;
- foreign-tax-credit support.

Loss carry-forward can depend on filing timeliness. Verify current rules.

## 6. Disclosure and special-situation questions

Ask whether the taxpayer:

- was a director in any company;
- held unlisted equity shares;
- was a partner or member of a firm, LLP, AOP, or trust;
- had assets or liabilities requiring Schedule AL;
- is governed by the Portuguese Civil Code;
- claims relief under a tax treaty or sections 89, 90, 90A, 91, or 115H;
- is a representative assessee;
- is an FPI;
- received deferred ESOP tax from an eligible startup;
- had foreign assets, foreign income, or foreign signing authority;
- had income of a spouse or minor child requiring clubbing;
- made political or electoral-trust contributions;
- received a notice or has a pending refund adjustment;
- must file because of prescribed high-value transactions despite otherwise low income;
- has any source not covered by the categories above.

Verify thresholds and form fields for the target assessment year. Do not hard-code them into the interview.

## 7. Completeness interview

After inventory, ask a grouped question like:

> I found the files listed below. For this financial year, did you have anything else in any of these categories: another employer or pension; another bank/FD/RD; another broker, demat, mutual fund, F&O, intraday, or crypto account; rent or property ownership/sale; freelance/business/partnership income; dividends, gifts, winnings, or other receipts; foreign income/assets/accounts/signing authority; ESOP/RSU activity; prior losses; deductions/donations/loans/insurance; tax challans/TDS/TCS; company directorship or unlisted shares; notices or revised-return context?

Then ask the statutory status and disclosure questions not answered by documents:

- days in India and relevant prior-year presence;
- original/revised/belated/updated filing;
- tax-regime history and business-income constraints;
- all bank accounts and refund nomination;
- foreign-asset/signing-authority declaration;
- directorship, unlisted shares, representative assessee, and special-status questions.

Require explicit “none” or “not applicable” answers. Silence is unresolved.

## 8. Evidence-status matrix

Maintain a compact table:

| Category | Applicable? | Evidence | Period covered | Reconciled? | Missing/decision |
|---|---|---|---|---|---|
| Salary | Yes | Form 16 employer A | Full FY | Yes | None |
| Savings interest | Yes | Bank statement | Full FY | Yes | None |
| Foreign assets | No, user confirmed | User statement | FY | N/A | None |
| Deductions | Unresolved | None | FY | No | Ask user |

Do not begin final filing with any material “Unresolved” row.
