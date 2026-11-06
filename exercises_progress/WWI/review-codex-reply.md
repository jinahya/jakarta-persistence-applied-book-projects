1. **agree** — `NOT EXISTS (... INTERSECT ...)` gives the same NULL-safe comparison: two NULLs count as equal, while a change to or from NULL is detected. Apply it to the accompanying native query too.

2. **agree** — The four additions answer distinct questions from Claude’s exercises and add useful coverage. Renumbering resolves the identifier collisions without losing that value.

3. **hold** — The tie-break fixes ordering, but leaves the calculation’s assumptions unchecked: the inner join drops orders without lines, and `SUM` ignores products with NULL expected prices. Keep the fixture checks or explicitly define and implement how those cases should be handled.