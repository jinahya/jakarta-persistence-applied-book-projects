You reviewed the demo database's exercises blind, in two batches (1/review-codex.md, 2/review-codex.md). Claude reviewed
the same batches (1/review-claude.md, 2/review-claude.md). Below is where the decisions differ from your proposals.
For each point answer in one or two sentences: `agree` (you accept the decision) or `hold` (you keep yours, and why).
Do not run anything; read only this directory. Markdown, nothing else, numbered as below.

1. A module-wide rule, from both reviews' time-zone findings: a day or a month is a UTC one unless an exercise says it
   is an airport's local one; every date bound on a timestamptz becomes TIMESTAMPTZ '... +00', and every TO_CHAR of one
   reads it AT TIME ZONE 'UTC'. Applied to all ten exercises with such a literal or TO_CHAR, not only those named.
2. TIMETABLE_A_02: your local day at SVO (scheduled_arrival_local) taken over Claude's UTC day.
3. TIMETABLE_I_03: your definition (status 'Arrived' for both counts) taken over Claude's (actual_arrival).
4. SCHEMA_A_03: Claude's count of each airport at its fewest flights, SVO left out, taken over your request that
   describes the old counts (an airport at both lengths, a return to SVO counted): "how many airports are one and two
   routes away" is not answered by counts that repeat airports.
5. SEGMENTS_A_01: Claude's `HAVING ... Economy > 0` in the exercise, over your separate zero-price check
   (SEGMENTS_I_05), since the condition is part of the question.
6. Your SCHEMA adds of batch 1 (whose ids collided with live ones) are taken as new ids: SCHEMA_B_06 (sold segments of
   cancelled flights), SCHEMA_I_10 (outbound and return tickets), SCHEMA_A_06 (passengers still to board); your
   SCHEMA_I_01 (booking totals) is rejected as BOOKINGS_A_01, which now uses outer joins as you proposed.
7. Rejected: SCHEMA_I_09 (Monday services from SVO), overlapping ROUTES_I_06 (routes per weekday, UNNEST); SEATS_I_04
   kept as a regex check only, without the integer-range part.
8. Removes by Claude you did not propose: AIRPORTS_DATA_B_03 (airports whose code starts with SV) and SEGMENTS_I_03
   (SEGMENTS_I_04 with > 2 in place of > 1).
