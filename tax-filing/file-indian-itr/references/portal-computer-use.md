# Harness-neutral portal computer use

## Contents

1. Control-surface selection
2. Observe-act-verify loop
3. Browser and desktop state
4. Sensitive-data and confirmation boundaries
5. Portal filing sequence
6. Validation and recovery
7. Completion proof

## 1. Control-surface selection

Use the strongest available semantic interface:

1. an official API or purpose-built connector, when it supports the filing step and preserves required authentication;
2. browser DOM/accessibility automation in the user’s existing logged-in browser;
3. OS accessibility automation for browser or desktop UI;
4. screenshots with coordinate clicks only when semantic controls are unavailable.

This skill is harness-neutral. Map these capabilities to the host agent’s tools:

- list or attach to existing browser tabs;
- read the DOM or accessibility tree;
- locate controls by role, label, name, and current value;
- click, fill, select, scroll, and wait;
- capture a screenshot when semantic state is incomplete;
- read local files without uploading them elsewhere.

The generic control loop is:

```text
state = observe(current app or tab)
control = find(state, role + exact label + section)
act(control, smallest intended change)
state = observe(current app or tab)
assert intended page/value/status in state
```

Do not substitute a fresh browser when the user asked to use an existing logged-in session. Do not use search-engine results or a third-party tax site to bypass portal authentication.

## 2. Observe-act-verify loop

For each meaningful UI transition:

1. **Observe:** fetch fresh DOM/accessibility state.
2. **Identify:** locate the exact control and confirm surrounding context.
3. **Act:** perform the smallest necessary action.
4. **Wait:** allow navigation, dialogs, recomputation, and loading overlays to finish.
5. **Observe again:** fetch new state rather than assuming success.
6. **Verify:** assert the new value, page heading, schedule status, error count, or success message.

Prefer exact accessible roles and labels. Scope repeated controls to their row, group, dialog, or section. Use coordinates only after reading a screenshot and verifying window geometry.

Never reuse stale accessibility indices, element handles, or coordinates after navigation, modal changes, page recomputation, or a new agent turn. Re-find the control from fresh state.

## 3. Browser and desktop state

- Reuse a working browser connection, but reacquire the tab when the host reports a stale or missing tab binding.
- Find the tab by official domain and page title. Do not inspect cookies, local storage, profiles, passwords, or session databases.
- Treat an empty tab list as a recoverable tab-state issue, not proof that login was lost.
- After relaunch or login, resume the saved draft. Never select “start new filing” when it would delete the draft.
- Keep one canonical filing tab. Avoid parallel edits in multiple tabs.
- Detect loading overlays and wait for them to disappear before reading totals.
- Read dialogs in full. Confirm whether a button validates, submits, deletes, or only navigates.
- When browser automation cannot access authentication UI, ask the user to log in in that browser and tell the agent when ready.
- Never bypass CAPTCHA, security warnings, or identity checks.
- Leave Tax Return Preparer fields blank unless the return was actually prepared by a registered TRP and the taxpayer supplies evidence-backed TRP details.

Use accessibility text first for efficiency. Use screenshots when:

- the accessibility tree omits a control or state;
- labels are duplicated or mistranslated;
- a table’s column association is unclear;
- a canvas/PDF preview must be visually verified;
- coordinate fallback is necessary.

After a coordinate action, immediately re-read semantic state or a screenshot to verify the result.

## 4. Sensitive-data and confirmation boundaries

Tax filing transmits government identifiers and financial information. Before first transmission, ensure the user explicitly authorized:

- the taxpayer;
- the official destination;
- the categories of supplied data;
- filing versus preparation-only scope.

The taxpayer must personally handle:

- passwords and login credentials;
- CAPTCHA;
- Aadhaar validation consent;
- OTP, EVC, or DSC;
- the legal declaration checkbox;
- any unexpected identity or legal consent.

Ask for confirmation at action time:

- before entering sensitive data when destination/scope was not already explicit;
- before any tax payment;
- before accepting an unexpected declaration or consent;
- immediately before irreversible final submission.

An early “file it” request does not remove the need to show the final figures and ask again when the portal warns that the return cannot be modified.

Do not echo OTPs, full Aadhaar, full bank numbers, passwords, or private contact details. Do not save them in scripts, logs, notes, screenshots, or shell history.

## 5. Portal filing sequence

Portal wording changes. Verify current labels, but expect a sequence similar to:

1. taxpayer logs in;
2. choose File Income Tax Return;
3. select assessment year and online mode;
4. resume saved draft or start the authorized filing;
5. confirm status and applicable ITR;
6. select schedules;
7. answer schedule questions;
8. complete and confirm each schedule;
9. review return summary and tax computation;
10. proceed to verification/declaration;
11. taxpayer checks declaration and confirms place/date;
12. run internal validation;
13. open preview and verify key fields;
14. run upload-level validation;
15. proceed to verification;
16. choose verification method;
17. taxpayer completes Aadhaar consent and OTP/EVC/DSC;
18. review submit-level warning;
19. obtain explicit “submit” instruction;
20. submit;
21. verify filed-and-verified success;
22. download and parse acknowledgement receipt.

Do not confuse similarly named stages:

- **Return Summary confirmed** means the draft is complete.
- **Internal Validation successful** means form-level rules passed.
- **Upload Level Validation successful** means the return passed the next validation layer.
- **Submitted successfully** means submission occurred but still inspect the following state.
- **Successfully filed and verified** plus a valid acknowledgement is completion proof.

## 6. Validation and recovery

When validation fails:

1. capture every error in one pass;
2. map each error to its schedule, source evidence, and downstream consumers;
3. return to the schedule without restarting the filing;
4. correct the source field;
5. save and verify it;
6. confirm the schedule;
7. re-confirm affected dependent schedules;
8. rerun internal validation;
9. preview again;
10. rerun upload-level validation.

Useful recovery rules:

- A selected UI value whose accessible name contains an untranslated key or “NA” may still serialize as blank. Inspect/edit or remove the zero row.
- If a required field is absent because the schedule is inapplicable, remove the schedule. Never invent facts.
- Allocate capital gains to the portal’s displayed date columns using source sale dates and the exact post-set-off total.
- After any edit, assume declaration state is stale even if a checkbox appears checked. Require a fresh taxpayer review.
- If session timeout occurs, log in again, choose the same AY and online mode, and resume the saved draft.
- If totals change after a fix, stop and re-reconcile before continuing.

## 7. Completion proof

After final submit:

1. read the portal success message;
2. continue to the filed-and-verified confirmation page;
3. download the acknowledgement;
4. confirm the file exists and is readable;
5. extract and compare:
   - acknowledgement number;
   - filing date/time;
   - taxpayer name and PAN;
   - form and assessment year;
   - filing section;
   - total income;
   - tax payable/refund;
   - verification method;
6. preserve the receipt in the authorized local directory or clearly report its download path.

Report “filed but verification pending” when verification is deferred. Report “filed and verified” only when the portal and acknowledgement both support it.
