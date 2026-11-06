You reviewed the exercises in this directory blind (review-codex.md). Claude reviewed them too (review-claude.md).
Here is where we disagree. For each point, answer in one or two sentences: `agree` (you accept Claude's position) or
`hold` (you keep yours, and why). Do not run anything; read only this directory. Markdown, nothing else.

1. Tier and section moves (HEAD_I_11 and HEAD_I_08 to Advanced, SCHEMA_A_05 and OFFICE_A_01 to Intermediate,
   OFFICE_I_03 to SCHEMA). Claude: rejected. The module puts window functions in Intermediate already (HEAD_I_08,
   I_09, I_10, I_11), and an id names its section and tier, so an exercise cannot move without breaking the id; an
   exercise that reads a second table in a subquery stays under the table it is about (HEAD_I_03, I_12 join office).
2. Id as a tie-break after term_start (HEAD_B_10, HEAD_I_08, HEAD_A_05). Claude: rejected; keep the exercises relying
   on term_start being distinct within a country, and guard that with your add, "Repeated term starts" (accepted, as
   HOG_HEAD_I_18). Your text fix of HEAD_I_08 (the sets overlap only below 2 * :n terms) is accepted.
3. Calendar centuries (SCHEMA_I_05, SCHEMA_A_06). Claude: rejected; the module counts a century the way people say
   "the 1800s", as SCHEMA_A_06 states, and I_05 should say so too, not change.
4. Remove HEAD_I_09. Claude: keep it; it is the plain top-n per group that HEAD_I_08 builds on.
5. HEAD_B_04 to INSTR(LOWER(...)). Claude: rejected; the exercise is about LIKE, its ASCII-only case folding and the
   index a leading wildcard cannot use, and no name holds % or _.
6. SCHEMA_A_05 to LEFT JOIN, and OFFICE_A_02 (rank titles by length). Claude: rejected; a president with no prime
   minister cannot reach the top ten, and five offices ranked by title length is not a question a reader asks.
