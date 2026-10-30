# jakarta-persistence-applied-book-projects

The projects of *Jakarta Persistence Applied*, each a git submodule, at the commits the book is written against.

| Project | What |
|---|---|
| [`heads-of-governments-jakarta-data`](https://github.com/jinahya/heads-of-governments-jakarta-data) | Jakarta Data, on the heads-of-governments database |
| [`heads-of-governments-persistence`](https://github.com/jinahya/heads-of-governments-persistence) | Jakarta Persistence mappings of a small SQLite database of heads of government |
| [`heads-of-governments-spring-data`](https://github.com/jinahya/heads-of-governments-spring-data) | Spring Data, on the heads-of-governments database |
| [`jinahya-persistence`](https://github.com/jinahya/jinahya-persistence) | The library the other projects use |
| [`mysql-sakila-persistence`](https://github.com/jinahya/mysql-sakila-persistence) | Jakarta Persistence mappings of the MySQL Sakila sample database |
| [`oracle-sample-schemas-persistence`](https://github.com/jinahya/oracle-sample-schemas-persistence) | Jakarta Persistence mappings of the Oracle Database sample schemas (CO, HR, SH) |
| [`postgresql-demodb-persistence`](https://github.com/jinahya/postgresql-demodb-persistence) | Jakarta Persistence mappings of the PostgreSQL demo database |

## Cloning

```shell
$ git clone --recurse-submodules https://github.com/jinahya/jakarta-persistence-applied-book-projects.git
```

A version of the book is a tag of this repository; to get the projects as that version shows them:

```shell
$ git clone --branch <version> --recurse-submodules https://github.com/jinahya/jakarta-persistence-applied-book-projects.git
```

## Updating

```shell
$ git pull --recurse-submodules                  # to the commits this repository points at
$ git submodule update --remote --merge          # or, to the tip of each project's develop
```

The first keeps the projects as the book shows them; the second goes past it.

## Building

Each project builds on its own, with its own wrapper, from its own directory; see its `README.md`. They need Java 25.

A project may depend on a `-SNAPSHOT` of another project here (see [Inter-dependencies](#inter-dependencies)), which
is not on Maven Central. Install that project first, `jinahya-persistence` say:

```shell
$ cd jinahya-persistence
$ ./mvnw install -DskipTests
```

## Inter-dependencies

Some projects use another one here, as an `io.github.jinahya` artifact. Between releases, a project's `develop` may
use the other's `-SNAPSHOT`, which has to be installed first (see [Building](#building)); a release uses released
versions only.

| Project | Depends on | Artifact | Scope |
|---|---|---|---|
| `heads-of-governments-jakarta-data` | `heads-of-governments-persistence` | `heads-of-governments-persistence` | `compile` |
| `heads-of-governments-spring-data` | `heads-of-governments-persistence` | `heads-of-governments-persistence` | `compile` |
| `mysql-sakila-persistence` | `jinahya-persistence` | `jinahya-persistence-test-utils` | `test` |
| `oracle-sample-schemas-persistence` | `jinahya-persistence` | `jinahya-persistence-more` | `compile` |
| | | `jinahya-persistence-test-utils` | `test` |
| `postgresql-demodb-persistence` | `jinahya-persistence` | `jinahya-persistence-more` | `compile` |
| | | `jinahya-persistence-utils` | `compile` |
| | | `jinahya-persistence-test-utils` | `test` |

`heads-of-governments-persistence` and `jinahya-persistence` depend on no other project here.

`jinahya-persistence-test-utils` depends on `jinahya-persistence-utils` at `compile` scope, so a project that
declares the former gets the latter too: `mysql-sakila-persistence`'s tests use both, and declare only
`jinahya-persistence-test-utils`.

