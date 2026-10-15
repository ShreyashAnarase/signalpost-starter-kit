# Chat assignment: packaging and evaluator reliability

Follow ../parallel-chat-plan.md, including its exact file ownership. Complete
this offline; do not make source requests or edit production runner/pipeline.

Read ../submission-packaging.md and ../dated-events-progress.md. Portable evidence
works offline; relocated package-as-refresh-input is explicitly unsupported.
Existing research deadlines do not cover all preprocessing and packaging.

1. Review the evaluator wrapper and packaging/audit paths for demonstrated
   failures: subprocess errors, invalid options/input, partial writes, mismatched
   batches, corrupt/missing bytes, path escapes and preservation of source data.
2. Add a supported explicit whole-evaluator timeout covering its subprocesses and
   packaging if feasible within owned files. Preserve real exit status and stop
   only processes started by the wrapper, including worker descendants. A timeout
   is a failure, never a successful or official run. Defaults must not invent the
   organizer's budget. If complete termination needs runner changes, report the
   dependency before editing coordinator-owned files.
3. Verify new DOM/JSON-LD event locators survive packaging and relocation. Keep
   cited prior evidence and reject tampering. Do not claim metadata/claim truth
   is verified merely because bytes and locators pass.
4. Validate timeout/error behavior with deterministic offline subprocess
   fixtures, including an actual sleeping child and descendant when relevant.
   Verify successful arbitrary-batch offline execution still works.

Acceptance: demonstrated bugs fixed without weakening checks; owned tests pass;
timeout and failed subprocess outcomes distinguish failed/partial artifacts;
documentation states exact resource and refresh limits. Do not solve unsupported
refresh by silently disabling history validation.

Use out/packaging-reliability/ for artifacts. Save
docs/task-results/packaging-reliability.md and report any remaining runner-level
dependency for the coordinator.
