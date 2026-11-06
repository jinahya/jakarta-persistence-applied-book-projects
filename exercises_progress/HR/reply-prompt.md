You reviewed the HR exercises blind (review-codex.md); Claude reviewed them too (review-claude.md). Where the decisions
differ from your proposals, answer in one or two sentences each: `agree` or `hold` (and why). Do not run anything;
read only this directory. Markdown, nothing else, numbered as below.

1. NULL salaries: your check (EMPLOYEES_B_09) is added, and the rankings (EMPLOYEES_A_01, A_02, EMP_DETAILS_VIEW_A_01)
   also order `SALARY DESC NULLS LAST`, so a missing salary never ranks first, without filtering rows.
2. SCHEMA_A_02 is kept and fixed, not retired: the current position starts the day after the last JOB_HISTORY.END_DATE
   of the employee (the trigger writes that end when the job changes), or on HIRE_DATE with no history; the current
   row sorts last on a tie. Your replacement (SCHEMA_A_07, a timeline with an unknown current start) is not added;
   SCHEMA_A_07 is Claude's LISTAGG exercise instead.
3. JOBS_I_02 (average midpoint): rejected; JOBS_B_04, your band check, guards missing bounds.
4. EMPLOYEES_I_07 (first ten by salary): rejected; Claude's EMPLOYEES_B_10 (the :n newest hires) teaches FETCH FIRST.
5. EMPLOYEES_I_03 (pay grades, Claude's point): a salary not recorded gets its own grade, 'Not recorded', instead of
   falling into 'High'.
