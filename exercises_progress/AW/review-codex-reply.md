1. **agree** — Carry `sp.BusinessEntityID` as `SalesPersonID` through the PIVOT to preserve identity without requiring unique last names; use it as the final tie-breaker too.

2. **agree** — Restricting to statuses 2 and 4 gives a useful, explicit definition of “spent” that excludes pending and rejected orders, though it measures order value rather than actual payments.

3. **agree** — Yearly aggregation with `LAG` is a suitable Advanced exercise; specify “previous year with qualifying orders,” because gaps mean the preceding row may not be the preceding calendar year.

4. **agree** — The additions cover distinct relationships and operations, so retaining both under the proposed separate IDs broadens coverage without duplication.