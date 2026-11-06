# CLAUDE.md

Guidance for working in `projects/`, the repository `jakarta-persistence-applied-book-projects`, which is itself a git
submodule of the book's repository. Every project here is a git submodule of its own; see `README.md` for the list.

The book's `../CLAUDE.md` delegates everything about the projects to this file; its own rules (the manuscript, disk
truth of code blocks, never reverting uncommitted work destructively, checking for running skills or loops first) still
hold here. A project's own `CLAUDE.md` wins over this file for that project.

## Absolute rules

- **`postgresql-demodb-persistence` is not Hibernate ORM only, uses no H2, and has ITs only.** The provider is the
  `persistence-unit.provider` property; neither the module nor the book says it is Hibernate-only. A test that needs the
  database is an `it` unit `*_PersistenceIT` and runs on PostgreSQL; there is no `test` unit and no H2. See that
  module's `CLAUDE.md`.
- **Unsure, broad, mechanical changes across several projects are asked first.** Check the change against disk and the
  conventions below, and ask the author when it is not clear.

## Layout

```
projects/
├── heads-of-governments-persistence     SQLite
├── jinahya-persistence                  the library the others use
├── mysql-sakila-persistence             MySQL
├── oracle-sample-schemas-persistence    Oracle; a module per schema: -co, -hr, -sh (and -common)
├── postgresql-demodb-persistence        PostgreSQL
├── sqlserver-samples-persistence        SQL Server; a module per database: -adventureworks, -futonmanufacturing,
│                                        -wideworldimporters (and -common)
└── data/                                *-jakarta-data and *-spring-data, on top of the -persistence projects
```

`jinahya-persistence` is the library, not a sample; most of what follows is about the `-persistence` projects of a
sample database.

## Building

Each project builds on its own, with its own wrapper, from its own directory, on Java 25. A project may depend on a
`-SNAPSHOT` of another one here; install that first (`./mvnw install -DskipTests` in `jinahya-persistence`, say).

- `./mvnw test-compile` compiles every test without a database.
- `*_PersistenceTest` runs under surefire, on the `test` unit.
- `*_PersistenceIT` runs under failsafe, only with `-Pfailsafe`, on the `it` unit, against the installed database.

Persistence units are named `test` and `it`; a module of several schemas or databases prefixes them (`hr-test`,
`adventureworks-it`). `heads-of-governments-persistence`, on SQLite, has `test` only.

## `src/test/sql`: profiling queries

A file per scope; the module is the scope a query can join within (a schema in SQL Server or PostgreSQL is a namespace,
not a join boundary):

| Scope | File |
|---|---|
| the module as a whole (the database, or Oracle's schema) | `__.sql` |
| one schema, in a module of several schemas | `_<Schema>.sql`, in the schema's own case |
| one table or view | `<table>.sql`, in the database's own case; `<Schema>_<Object>.sql` in SQL Server |

SQL Server keeps the schema prefix because object names repeat across schemas (`Sales.Customers`,
`Website.Customers`).

## `src/test/sql-exercises`: the exercises

```
src/test/sql-exercises/
├── EXERCISES.asciidoc     every problem, under [[<ID>]]
├── EXERCISES.yaml         the registry: id, section, tier, title, sql, test, native-only, retired
├── __/                    the whole module
├── <table>/               one table or view
└── _<Schema>/             one schema (SQL Server)
    ├── 01_basic.sql
    ├── 02_intermediate.sql
    └── 03_advanced.sql
```

- A directory is named after the file of `src/test/sql` it exercises, case and all (`actor/`, `EMPLOYEES/`,
  `_HumanResources/`, `__/`).
- A file holds its level's exercises in id order, each under a ruler that carries its id. A level with no exercise has
  no file.
- Ids are permanent; see the header of each `EXERCISES.yaml`. `../PROJECTS_EXERCISES.asciidoc`, in the book, picks the
  exercises the book shows.
- Exercise SQL pages in the optimal form the database permits (`LIMIT n`, `OFFSET m` only past the first page;
  `setMaxResults` / `setFirstResult` likewise), as the book's `../CLAUDE.md` states it.

## `src/test/java-exercises`: the tests of the exercises

`src/test/java` keeps to the persistence tests. The tests that answer the exercises are in `src/test/java-exercises`,
which each project's root `pom.xml` adds as a test source with `build-helper-maven-plugin` (execution
`add-exercises-test-source`), in no profile.

- A class per `.sql` file: `<Dir>_Exercises_<NN>_<Level>_Persistence{IT|Test}`, where `<Dir>` is the directory in
  PascalCase, a leading `_` kept (`__/01_basic.sql` → `__Exercises_01_Basic_PersistenceIT`, `actor_info/` →
  `ActorInfo_…`, `EMP_DETAILS_VIEW/` → `EmpDetailsView_…`, `_HumanResources/` → `_HumanResources_…`).
- A nested class per exercise, `<ID>_Test`, with `@DisplayName("<ID>: <title>")`; the registry's `test:` names it as
  `<Class>.<ID>_Test`.
- The classes are in the module's test package, so they keep package-private access; helpers they share are in a
  package-private `__Exercises_TestUtils` beside them.
- `src/test/java-exercises` may use anything in `src/test/java`; `src/test/java` never uses `src/test/java-exercises`.

## Shared files

- **The projects share one `.gitignore` and one `.idea/codeStyles`.** Every submodule here (and under `data/`) has the
  same `.gitignore`, which ignores `.idea/*` but keeps `!.idea/codeStyles/`; what a single project needs goes at its
  end, under "This project". Every submodule but `jinahya-persistence` tracks the same plain
  `.idea/codeStyles/Project.xml` and `codeStyleConfig.xml`.
- **`jinahya-persistence` is the exception, and we don't touch it:** its `.idea/codeStyles` is a git submodule
  (`onacit/dot-idea-codestyles`), with its own content; never replace it with plain files, copy it to the others, or
  bump it.

## Documents

The documents about the projects are not here: this repository is what the book's readers clone. They live at the root
of the book's repository (`../`), beside `_alignment.py`, where the skills run, and write their paths relative to it.

| File | What |
|---|---|
| `PROJECTS_STRUCTURE.asciidoc` | the domains, their parts, and how the parts depend on one another |
| `PROJECTS_BUILD.asciidoc` | the names and meanings of the profiles, scripts and Docker Compose files |
| `PROJECTS_VERSIONS.asciidoc` | the version every submodule is to be on, per Jakarta EE generation (`_alignment.py`) |
| `PROJECTS_EXERCISES.asciidoc` | which exercises the book shows, and the rules of the exercises |
| `EXERCISES_PROGRESS.asciidoc` | the progress of the exercises (empty so far) |
| `SUBMODULE_RELEASE.asciidoc` | releasing and deploying a submodule (`/release`, `/deploy-undeployed`) |
| `PERSISTENCE_PROVIDERS.asciidoc`, `JAKARTA_PERSISTENCE.asciidoc` | what the specification says and what the providers do |
| `HIBERNATE_PROCESSOR.asciidoc`, `SQL_SERVER_SAMPLES.asciidoc` | notes on one question each |
