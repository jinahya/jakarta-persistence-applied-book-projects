## EXERCISES.yaml header

```
# Registry of the exercises in EXERCISES.asciidoc and the <section>/<NN>_<level>.sql files beside it.
#
# An id is HOG_<SECTION>_<TIER>_<NN>: the table the exercise reads alone, or SCHEMA for one that reads more than one,
# the tier (B for Basic, I for Intermediate, A for Advanced), and a number within that section and tier.
#
# Ids are permanent. A new exercise takes the next unused number of its section and tier; an exercise that moves or
# changes tier keeps its id; an id of a removed exercise is marked `retired: true` and never reused. EXERCISES.asciidoc
# carries each id as the anchor and the prefix of the exercise's heading, and the .sql file carries it in the marker
# above the statement, followed by the title.
#
# `sql` is the file that answers the exercise in SQL; `test` is the test, and its nested class, that answers it in JPQL
# and with the Criteria API, or with a native query where neither can, which `native-only: true` marks. The nested class
# is numbered by the exercise's place in its file, which may change; the id does not.


# ---- head
```

## Header of __/01_basic.sql

```sql
-- #%L
-- heads-of-governments-persistence
-- %%
-- Copyright (C) 2026 Jinahya, Inc.
-- %%
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--      http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
-- #L%
---
--
-- Exercises at the basic level on the whole schema, a problem per query that reads both tables. Each problem states the
-- request it answers, then the SQL that answers it.
--
-- Parameters are bind variables (:name); the sqlite3 shell binds one with `.parameter set :name 'value'`, and an IDE
-- prompts for them when a statement runs.
--
```

## Paging

A query that takes the top n rows writes only what it needs: `LIMIT n` alone for the first rows, `OFFSET m` only for a page past the first, in the form the database runs best; never a clause for its own sake.
