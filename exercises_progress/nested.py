#!/usr/bin/env python3
"""Gives every live exercise of a module its nested test class.

    python3 nested.py <module> [--dry]

For each .sql file of src/test/sql-exercises, the class <Dir>_Exercises_<NN>_<Level>_Persistence{IT|Test} in
src/test/java-exercises, in the package of the module's *_PersistenceIT (or *_PersistenceTest) classes, with the license
header of one of them; a missing class is made, and a missing nested class is added to it, empty:

    @DisplayName("<ID>: <title>")
    @Nested
    class <ID>_Test {
    }

An entry of EXERCISES.yaml without a `test:` gets one. A nested class that exists is left as it is.
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, sys.argv[1])
DRY = '--dry' in sys.argv
EX = os.path.join(MOD, 'src/test/sql-exercises')
LEVEL = {'01_basic': ('01', 'Basic'), '02_intermediate': ('02', 'Intermediate'), '03_advanced': ('03', 'Advanced')}


def pascal(d):
    lead = re.match(r'_*', d)[0]
    parts = [p for p in d[len(lead):].split('_') if p]
    return lead + ''.join(p[:1].upper() + p[1:].lower() if p.islower() or p.isupper() else p for p in parts)


# the package and the license, from the module's own persistence tests
samples = sorted(glob.glob(os.path.join(MOD, 'src/test/java/**/*_PersistenceIT.java'), recursive=True)) or \
          sorted(glob.glob(os.path.join(MOD, 'src/test/java/**/*_PersistenceTest.java'), recursive=True))
kind = 'IT' if samples[0].endswith('IT.java') else 'Test'
existing = glob.glob(os.path.join(MOD, 'src/test/java-exercises/**/*_Exercises_*.java'), recursive=True)
if existing:
    kind = 'IT' if any(f.endswith('IT.java') for f in existing) else 'Test'
counts = {}
for f in samples:
    pkg = re.search(r'(?m)^package ([\w.]+);', open(f).read())[1]
    counts[pkg] = counts.get(pkg, 0) + 1
package = min(counts, key=lambda p: (-counts[p], len(p)))  # the most common, the shortest at a tie
sample = open(next(f for f in samples if f'package {package};' in open(f).read())).read()
pm = re.search(r'(?m)^package [^;]+;\n', sample)
before = sample[:pm.start()]
after = re.match(r'(?s)\n*(/\*(?!\*).*?\*/\n)', sample[pm.end():])
license_after = '\n' + after[1] if after else ''
jdir = os.path.join(MOD, 'src/test/java-exercises', *package.split('.'))
by_sql, by_name = {}, {}
for f in existing:
    t = open(f).read()
    for sp in re.findall(r'src/test/sql-exercises/[\w/]+\.sql', t):
        by_sql.setdefault(sp, f)
    by_name[os.path.basename(f)[:-5].lower().replace('_', '')] = f
if existing:  # new classes go beside the module's own exercise classes
    jdir = os.path.dirname(existing[0])
    package = re.search(r'(?m)^package ([\w.]+);', open(existing[0]).read())[1]


def class_file(sql, cls):
    f = by_sql.get(sql) or by_name.get(cls.lower().replace('_', ''))
    return f or os.path.join(jdir, cls + '.java')

yaml_path = os.path.join(EX, 'EXERCISES.yaml')
yaml = open(yaml_path).read()
entries = list(re.finditer(r'(?ms)^- id: (\S+)\n(.*?)(?=^- id: |^# ---|\Z)', yaml))
writes, made, added, tests = {}, [], [], 0
for m in entries:
    id_, body = m[1], m[2]
    if 'retired: true' in body:
        continue
    sql = re.search(r'(?m)^  sql: (\S+)', body)[1]
    title = re.search(r'(?m)^  title: (.*)$', body)[1].strip().strip('"')
    d, lv = sql.split('/')[-2], sql.split('/')[-1][:-4]
    nn, level = LEVEL[lv]
    cls = f'{pascal(d)}_Exercises_{nn}_{level}_Persistence{kind}'
    path = class_file(sql, cls)
    cls = os.path.basename(path)[:-5]
    text = writes.get(path) or (open(path).read() if os.path.exists(path) else None)
    if text is None:
        text = (f'{before}package {package};\n{license_after}\nimport org.junit.jupiter.api.DisplayName;\n'
                f'import org.junit.jupiter.api.Nested;\n\n'
                f'/**\n * Answers the exercises of {{@code {sql}}}; a nested class per exercise.\n */\n'
                f'@SuppressWarnings({{\n        "java:S101" // Class names should comply with a naming convention\n}})\n'
                f'class {cls} {{\n}}\n')
        made.append(cls)
    if not re.search(rf'(?m)^    class {id_}_Test\b', text):
        t = title.replace('\\', '\\\\').replace('"', '\\"')
        block = f'    @DisplayName("{id_}: {t}")\n    @Nested\n    class {id_}_Test {{\n    }}\n'
        head = text.rstrip().rstrip('}').rstrip('\n')
        text = head + '\n\n' + block + '}\n'
        added.append(id_)
    writes[path] = text
    if not re.search(r'(?m)^  test: ', body):
        tests += 1

# the test: entries, after each entry's sql:
def with_test(m):
    body = m[0]
    if 'retired: true' in body or re.search(r'(?m)^  test: ', body):
        return body
    sql = re.search(r'(?m)^  sql: (\S+)', body)[1]
    d, lv = sql.split('/')[-2], sql.split('/')[-1][:-4]
    nn, level = LEVEL[lv]
    cls = os.path.basename(class_file(sql, f'{pascal(d)}_Exercises_{nn}_{level}_Persistence{kind}'))[:-5]
    return re.sub(r'(?m)^(  sql: \S+\n)', rf'\1  test: {cls}.{m[1]}_Test\n', body, count=1)


new_yaml = re.sub(r'(?ms)^- id: (\S+)\n.*?(?=^- id: |^# ---|\Z)', with_test, yaml)
if not DRY:
    os.makedirs(jdir, exist_ok=True)
    for p, t in writes.items():
        open(p, 'w').write(t)
    open(yaml_path, 'w').write(new_yaml)
if DRY:
    print('would make', made, 'would add', added[:8], '...' if len(added) > 8 else '')
print(f'{sys.argv[1]}: package {package}, kind {kind}; classes made {len(made)}, nested added {len(added)}, '
      f'test: entries added {tests}')
