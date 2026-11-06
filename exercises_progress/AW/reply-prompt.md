You reviewed the AdventureWorks exercises blind (review-codex.md); Claude reviewed them too (review-claude.md). Where
the decisions differ from your proposals, answer in one or two sentences each: `agree` or `hold` (and why). Do not run
anything; read only this directory. Markdown, nothing else, numbered as below.

1. SALES_A_01: your version (every sales person, 0 for no sales, the fiscal-year bounds, COALESCE) with Claude's point:
   SalesPersonID goes through the PIVOT, so two sales persons of one last name stay apart, instead of a check that
   last names are distinct.
2. PURCHASING_I_01: Claude's (approved and complete orders only, Status 2 and 4, as "spent") over yours (all statuses,
   the request reworded to "order amounts").
3. PURCHASING_A_01: Claude's (yearly spend per vendor against the previous year, LAG, statuses 2 and 4) over yours
   (monthly running totals of 2025).
4. PERSON_B_02 and HUMANRESOURCES_I_03: both reviewers' adds kept, under separate ids (Claude's address types and
   multi-department employees; your contacts and roles as PERSON_B_03, shift lengths as HUMANRESOURCES_I_04).
