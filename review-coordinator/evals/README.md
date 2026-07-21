# review-coordinator evals

Two kinds of eval, matching the two failure modes of a skill: does it *load* when it should (triggering), and does it *behave* correctly when it does (routing + output contract).

## Run the deterministic suite

```bash
python3 evals/run_evals.py   # exit 0 = all pass
```

Covers, with no model calls:
- **tier 1 — routing:** `fixtures/routing.json` asserts changed-files → planned lens set.
- **tier 2 — verdict schema:** validates a good and a bad sample verdict.
- **tier 2b — triggering-scorer math:** checks the scorer computes rates correctly off a recorded sample.

## Triggering eval (needs model runs)

This is the §5 method from *Skill creation best practices*: does the skill fire on real review requests and stay quiet on near-misses?

1. **Generate trigger decisions.** For each query in `fixtures/triggering.json`, present a judge agent with ONLY the installed skills' `name` + `description` (the same context the router sees at startup) and the query, and ask: "Which skill, if any, fires? Does `review-coordinator` fire — yes/no?" Repeat ~3× per query (triggering is nondeterministic). A practical way to run it: spawn one isolated judge subagent per trial.
2. **Record** the booleans in a results file keyed by query id, e.g. `{"st1":[true,true,false], ...}`.
3. **Score:**
   ```bash
   python3 evals/score_triggering.py my_results.json
   ```
   should-trigger passes at rate > 0.5; should-not passes at rate < 0.5. The **val** accuracy is the honest number (the train split is for tuning the description).

## Growing the suite (tier 3 — recall@known-defects)

When a real bug slips past the coordinator, add it: capture the pre-fix diff and assert the coordinator flags that bug as blocking. Seeds: PR #515's `createdAt` precision drift, the original key-timestamp drift. This is how the tracked error rate grows from actual escapes rather than guesses.
