You reviewed the FutonManufacturing exercises blind (review-codex.md); Claude reviewed them too (review-claude.md).
Where the decisions differ from your proposals, answer in one or two sentences each: `agree` or `hold` (and why). Do
not run anything; read only this directory. Markdown, nothing else, numbered as below.

1. I_05: your outer join from SalesChannel and tie-break, with Claude's point that cancelled orders are not sales; the
   cancellation filter goes into the join's condition. Your UnknownNetAmounts column is not kept.
2. Quotations: Claude's (accepted quotes not yet turned into an order, B_08) taken over yours (accepted quotes with the
   resulting order, the representative and territory).
3. Purchase lines to receive: yours (B_07) over Claude's; returns: both kept, Claude's share returned (I_08) and your
   quantities and refunds by reason (I_09).
4. Production, a subject no exercise had: your open schedule (B_10) and materials still to issue (I_11) with Claude's
   late completions (B_09) and scrap rate per work center (I_10), under a new "Production" heading.
