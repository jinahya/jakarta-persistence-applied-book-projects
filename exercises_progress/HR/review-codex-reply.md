1. **hold** — `NULLS LAST` still assigns rank 1 to missing salaries in an all-null partition, and can include them among the top three ranks when fewer than three recorded salary levels exist. The diagnostic check does not prevent either case.

2. **hold** — The trigger’s `SYSDATE` records the change time; it does not establish that the current assignment starts the following day. Keep the start unknown unless the exercise explicitly defines a next-day convention and labels the date as inferred.

3. **hold** — JOBS_B_04 detects missing bounds but does not prevent separate averages from combining different sets of jobs. Averaging each complete band’s midpoint remains the correct calculation for the stated measure.

4. **agree** — The newest-hires exercise covers `FETCH FIRST` with deterministic ordering and a configurable limit, making the salary-based exercise redundant.

5. **agree** — An explicit `Not recorded` grade preserves total headcount and avoids misclassifying missing salaries as `High`.