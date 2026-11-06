## EXERCISES.yaml header

```
# Registry of the exercises in EXERCISES.asciidoc and the <section>/<NN>_<level>.sql files beside it.
#
# An id is WWI_<SECTION>_<TIER>_<NN>: the section is the schema the exercise is filed under, though it may read the
# tables of other schemas too; the tier is B for Basic, I for Intermediate and A for Advanced; and the number is within
# that section and tier. A database of several schemas takes its sections from the schemas, not from the tables.
#
# Ids are permanent. A new exercise takes the next unused number of its section and tier; an exercise that moves or
# changes tier keeps its id; an id of a removed exercise is marked `retired: true` and never reused. EXERCISES.asciidoc
# carries each id as the anchor and the prefix of the exercise's heading, and the .sql file repeats it in the marker
# above the statement.
#
# `sql` is the file that answers the exercise in SQL; `test` is the integration test, and its nested class, that
# answers it in JPQL and with the Criteria API. `native-only: true` marks an exercise only SQL can answer; its `test`,
# if it has one, sends the SQL as a native query.

# ---- application
```

## Header of _Application/01_basic.sql

```sql
-- #%L
-- sqlserver-samples-persistence-wideworldimporters
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
-- Exercises at the Basic level on the Application schema of WideWorldImporters.
--
-- These are the SQL solutions of the 'Application' section of EXERCISES.asciidoc, which also states each problem in
-- full and gives its JPQL solutions. Each problem below repeats the request it answers.
--
-- A parameter is a local variable, DECLAREd right above the query that reads it; run the two together.
--
```

## Paging

A query that takes the top n rows writes only what it needs: `LIMIT n` alone for the first rows, `OFFSET m` only for a page past the first, in the form the database runs best; never a clause for its own sake.
