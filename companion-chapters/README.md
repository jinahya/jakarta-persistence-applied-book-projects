# companion-chapters

The companion chapters of *Jakarta Persistence Applied*: the chapters the printed book leaves out, each rendered
alone as a PDF.

| File | Chapter |
|---|---|
| `oracle-hr-persistence.pdf` | Oracle HR Persistence |
| `oracle-sh-persistence.pdf` | Oracle SH Persistence |
| `sqlserver-wideworldimporters-persistence.pdf` | SQL Server WideWorldImporters Persistence |
| `sqlserver-futonmanufacturing-persistence.pdf` | SQL Server FutonManufacturing Persistence |

They are generated from the book's manuscript, in the book's repository, and are not edited here:

```shell
$ ./build.sh companion        # or ./mvnw -Pcompanion generate-resources
```
