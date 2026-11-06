You reviewed the WideWorldImporters exercises blind (review-codex.md); Claude reviewed them too (review-claude.md).
Every one of your items was taken; where both proposed something, one was chosen or both kept. Answer in one or two
sentences each: `agree` or `hold` (and why). Do not run anything; read only this directory. Markdown, nothing else.

1. SALES_A_02: Claude's `NOT EXISTS (SELECT then INTERSECT SELECT now)` over your three-way condition; same result.
2. Your adds kept beside Claude's, under new ids where they collided: PURCHASING_A_02 (three most overdue orders per
   supplier), SALES_I_06 (deals applying to a customer and an item), APPLICATION_B_03 (a country's cities),
   WAREHOUSE_I_04 (incoming and outgoing movements).
3. Your PURCHASING_I_01 fixture checks (orders without lines, NULL expected prices) are not added; only the tie-break.
