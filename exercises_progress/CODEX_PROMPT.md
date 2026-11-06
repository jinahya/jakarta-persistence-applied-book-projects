You are reviewing the SQL exercises of one schema of a sample database, for a book on Jakarta Persistence. Work only
from the files in this directory:

- `exercises.asciidoc` — the current exercises of this unit: each has an id, a title, the request it answers, and the
  SQL that answers it. Output blocks were removed.
- `exercises.yaml` — the registry of the same exercises, retired ones too (`retired: true`).
- `conventions.md` — the module's rules for exercises and SQL.
- `ddl/` — the database's own DDL, as its source publishes it. This is the truth about tables, columns, keys and types.

Do not run anything. Do not start a database, a container, or any program; do not look outside this directory. Read
the files and think.

Your task: propose what should change, so that the exercises of this unit are correct, useful and well spread.

- **fix**: an exercise whose SQL does not answer its request, or is wrong for the DDL (a column or table that does not
  exist, a wrong join, a wrong type assumption, NULL handling, an ambiguous or unstable ORDER BY, paging not in the
  optimal form the database permits), or whose request is unclear. A fix keeps the id only if the request stays the
  same question; otherwise it is a remove plus an add.
- **add**: a question a real user of this data would ask that no exercise covers yet: a table, a column, a key, a join
  path, or a SQL feature of the level that is missing. Prefer what the DDL makes interesting (foreign keys, constraints,
  hierarchies, dates, nullable columns, views).
- **remove**: an exercise that duplicates another, asks nothing a user would ask, or cannot be answered from the DDL.

Levels and sections: take them from the exercises as they are; the module decides what each level holds (an
Intermediate exercise may use a window function, for one). Never move an exercise to another tier or section: the id
names both. Keep every level of every section populated, and put an add where the existing exercises of the module
would put it.

Assumptions: where the data holds a fact the DDL does not enforce (a value unique within a group, a column never
empty), the exercises may rely on it; propose a check that guards the fact rather than a workaround in every exercise.
Keep the module's own conventions over a stricter reading (how it counts centuries, how it takes a name as a person).

Ids: `<PREFIX>_<SECTION>_<B|I|A>_<NN>`. Never reuse an id, retired ones included. A new exercise takes the next unused
`NN` of its section and tier.

Write your answer as Markdown, and nothing else, in this shape, one block per item:

```
### <fix|add|remove> <ID>
- section: <SECTION>   tier: <Basic|Intermediate|Advanced>
- title: <short title>
- why: <one or two sentences>
- request: <the request, as the user would say it>      (fix and add only)
- sql:                                                  (fix and add only)
    <the SQL, in the database's dialect, formatted like the existing ones>
```

Start with the fixes, then the adds, then the removes. If an exercise needs no change, do not mention it. Be concrete
and brief; at most 15 items, the most valuable first.
