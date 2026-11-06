#!/usr/bin/env python3
# gather.py <projects> <UNIT> <module> <SECTION[,SECTION...]|*> <ddl file or dir>...
# Writes exercises_progress/<UNIT>/{exercises.asciidoc,exercises.yaml,conventions.md,ddl/}.
import os, re, sys, shutil, glob

projects, unit, module, sections = sys.argv[1:5]
ddls = sys.argv[5:]
mod = os.path.join(projects, module)
ex = os.path.join(mod, 'src/test/sql-exercises')
out = os.path.join(projects, 'exercises_progress', unit)
os.makedirs(os.path.join(out, 'ddl'), exist_ok=True)
want = None if sections == '*' else set(sections.split(','))

# EXERCISES.asciidoc: keep the preamble and the exercises of the sections, without the output blocks
text = open(os.path.join(ex, 'EXERCISES.asciidoc')).read()
text = re.sub(r'^\.{4,}\n.*?^\.{4,}\n', '', text, flags=re.S | re.M)
if want is not None:
    parts = re.split(r'(?m)^(?=\[\[[A-Z0-9_]+\]\]\n)', text)
    keep = [parts[0].split('\n== ')[0]]
    for p in parts[1:]:
        m = re.match(r'\[\[[A-Z]+_([A-Z0-9_]+)_[BIA]_\d+\]\]', p)
        body = re.split(r'(?m)^(?===? )', p)[0]  # drop a following section heading
        if m and m[1] in want:
            keep.append(body)
    text = '\n'.join(keep)
open(os.path.join(out, 'exercises.asciidoc'), 'w').write(text)

# EXERCISES.yaml: header and the entries of the sections
y = open(os.path.join(ex, 'EXERCISES.yaml')).read()
head = y.split('\n- id:')[0]
entries = re.findall(r'(?ms)^- id: .*?(?=^- id: |\Z)', y)
if want is not None:
    entries = [e for e in entries if re.search(r'section: "?([A-Z0-9_]+)', e)[1] in want]
open(os.path.join(out, 'exercises.yaml'), 'w').write(head + '\n' + ''.join(entries))

# conventions: the registry's header, a .sql file's header, the module's CLAUDE.md section on exercises
conv = ['## EXERCISES.yaml header\n', '```', head.strip(), '```\n']
sqls = sorted(glob.glob(os.path.join(ex, '*', '*.sql')))
if sqls:
    lines = open(sqls[0]).read().split('\n')
    i = next((k for k, l in enumerate(lines) if re.match(r'-- -+ ', l)), len(lines))
    conv += ['## Header of ' + os.path.relpath(sqls[0], ex) + '\n', '```sql', '\n'.join(lines[:i]).strip(), '```\n']
conv += ['## Paging\n', 'A query that takes the top n rows writes only what it needs: `LIMIT n` alone for the first '
         'rows, `OFFSET m` only for a page past the first, in the form the database runs best; never a clause for its '
         'own sake.\n']
open(os.path.join(out, 'conventions.md'), 'w').write('\n'.join(conv))

for d in ddls:
    src = d if os.path.isabs(d) else os.path.join(mod, d)
    if os.path.isdir(src):
        for f in glob.glob(os.path.join(src, '*')):
            if os.path.isfile(f) and not f.endswith(('.csv', '.log', '.txt')) and 'populate' not in f and os.path.getsize(f) < 400_000:
                shutil.copy(f, os.path.join(out, 'ddl'))
    else:
        shutil.copy(src, os.path.join(out, 'ddl'))
print(out, len(entries), 'entries;', len(re.findall(r'(?m)^\[\[', text)), 'exercises;', os.listdir(os.path.join(out, 'ddl')))
