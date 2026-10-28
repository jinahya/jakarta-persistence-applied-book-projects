# jakarta-persistence-applied-book-projects

The projects of *Jakarta Persistence Applied*, each a git submodule, at the commits the book is written against.

| Project | What |
|---|---|
| [`heads-of-governments-jakarta-data`](https://github.com/jinahya/heads-of-governments-jakarta-data) | Jakarta Data, on the heads-of-governments database |
| [`heads-of-governments-persistence`](https://github.com/jinahya/heads-of-governments-persistence) | Jakarta Persistence mappings of a small SQLite database of heads of government |
| [`heads-of-governments-spring-data`](https://github.com/jinahya/heads-of-governments-spring-data) | Spring Data, on the heads-of-governments database |
| [`jinahya-persistence`](https://github.com/jinahya/jinahya-persistence) | The library the other projects use |
| [`mysql-sakila-persistence`](https://github.com/jinahya/mysql-sakila-persistence) | Jakarta Persistence mappings of the MySQL Sakila sample database |
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

A project may depend on a `-SNAPSHOT` of `jinahya-persistence`, which is not on Maven Central. Install it first:

```shell
$ cd jinahya-persistence
$ ./mvnw install -DskipTests
```

