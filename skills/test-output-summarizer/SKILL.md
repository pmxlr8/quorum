---
name: test-output-summarizer
description: Summarize test execution with explicit input/output evidence and regression-focused findings.
---

# Test Output Summarizer

Use after any test run.

## For each test group include
- Command executed
- Scenario input
- Expected result
- Actual result
- Pass/fail
- Regression risk if failing

## Rules
- Do not claim pass without command evidence.
- Highlight behavior regressions before style issues.
