#!/usr/bin/env python3
"""Applies a unit's decisions to a -persistence module.

    python3 apply.py <decisions.json> [--dry]

decisions.json:
  {"module": "heads-of-governments-persistence",
   "changes": [
     {"op": "fix", "id": "X_A_B_01", "title": "...", "request": ["sentence", ...], "sql": "...", "rerun": true},
     {"op": "add", "id": "X_A_B_02", "after": "X_A_B_01", "title": "...", "request": [...], "sql": "...",
      "rerun": true},
     {"op": "remove", "id": "X_A_B_03"}]}

A fix changes only the keys it gives. "rerun": true puts NOT YET RUN where the output is (EXERCISES.asciidoc, and the
.sql file where the module keeps output there); an exercise with a parameter shows no output, so give it false.
An add goes after "after", which must be in the same .sql file. A remove retires the id in EXERCISES.yaml and takes the
exercise out of EXERCISES.asciidoc, its .sql file and its test class.
"""
import json, os, re, sys, textwrap, glob

LEVEL = {'B': ('01_basic', 'Basic'), 'I': ('02_intermediate', 'Intermediate'), 'A': ('03_advanced', 'Advanced')}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry' in sys.argv
D = json.load(open(sys.argv[1]))
MOD = os.path.join(ROOT, D['module'])
EX = os.path.join(MOD, 'src/test/sql-exercises')
ADOC, YAML = os.path.join(EX, 'EXERCISES.asciidoc'), os.path.join(EX, 'EXERCISES.yaml')
files = {}


def read(p):
    if p not in files:
        files[p] = open(p).read()
    return files[p]


def write(p, t):
    files[p] = t


def entry(yaml, id_):
    m = re.search(rf'(?ms)^- id: {id_}\n.*?(?=^- id: |^# ---|\Z)', yaml)
    if not m:
        sys.exit(f'{id_}: not in EXERCISES.yaml')
    return m


def field(e, k):
    m = re.search(rf'(?m)^  {k}: (.*)$', e)
    return m[1].strip().strip('"') if m else None


def sql_path(id_):
    return os.path.join(MOD, field(entry(read(YAML), id_)[0], 'sql'))


def test_file(id_):
    t = field(entry(read(YAML), id_)[0], 'test')
    if not t:
        return None, None
    cls = t.split('.')[0]
    f = glob.glob(os.path.join(MOD, 'src/test/java-exercises/**', cls + '.java'), recursive=True)
    return (f[0] if f else None), cls


# ---------------------------------------------------------------------------------------------------------- asciidoc
def adoc_block(t, id_):
    m = re.search(rf'(?ms)^\[\[{id_}\]\]\n.*?(?=^\[\[[A-Z0-9_]+\]\]\n|^==?=? |\Z)', t)
    if not m:
        sys.exit(f'{id_}: not in EXERCISES.asciidoc')
    return m


def adoc_render(id_, title, request, caption, sql, tail):
    return (f'[[{id_}]]\n==== {id_}: {title}\n\n' + '\n'.join(request) + '\n\n'
            f'.`{caption}`, {id_}\n[%collapsible]\n====\n[source,sql]\n----\n{sql.strip()}\n----\n{tail}====\n\n')


def adoc_parse(block):
    m = re.match(r'(?s)\[\[(\S+)\]\]\n==== \S+: (.*?)\n\n(.*?)\n\n\.`([^`]+)`, \S+\n\[%collapsible\]\n====\n'
                 r'\[source,sql\]\n----\n(.*?)\n----\n(.*)====\n\n?$', block)
    if not m:
        sys.exit('cannot parse block:\n' + block[:400])
    return {'title': m[2], 'request': m[3].split('\n'), 'caption': m[4], 'sql': m[5], 'tail': m[6]}


# --------------------------------------------------------------------------------------------------------------- sql
RULER = re.compile(r'(?m)^-- -+ ([A-Z0-9_]+) (.*)$')


def sql_block(t, id_):
    m = re.search(rf'(?ms)^-- -+ {id_} .*?(?=^-- -+ [A-Z0-9_]+ |\Z)', t)
    if not m:
        sys.exit(f'{id_}: no ruler in the .sql file')
    return m


def ruler(id_, title):
    s = f' {id_} {title}'
    return '-- ' + '-' * max(4, 120 - 3 - len(s)) + s


def comments(request):
    out = []
    for line in textwrap.wrap(' '.join(request), 117, break_long_words=False, break_on_hyphens=False):
        out.append('-- ' + line)
    return out


def keeps_output(t):  # a module whose .sql files carry output as comments under the statement
    return bool(re.search(r'(?m)^;\n-- (?!-+ [A-Z0-9_]+ )', t))


def sql_render(id_, title, request, sql, out_lines):
    body = [ruler(id_, title)] + comments(request) + [sql.strip().rstrip(';').rstrip(), ';'] + out_lines
    return '\n'.join(body) + '\n\n\n'


# -------------------------------------------------------------------------------------------------------------- java
def nested(id_, title):
    t = title.replace('\\', '\\\\').replace('"', '\\"')
    return f'    @DisplayName("{id_}: {t}")\n    @Nested\n    class {id_}_Test {{\n    }}\n'


def java_block(t, id_):
    return re.search(rf'(?ms)(?:^    //[^\n]*\n)*(?:^    @[^\n]*\n)*^    class {id_}_Test \{{.*?^    }}\n', t)


def java_new_class(path, cls, id_, title, after_file):
    """A class for a .sql file that has none yet, modelled on a sibling."""
    sib = open(after_file).read() if after_file else None
    pkg = re.search(r'(?m)^package .*;$', sib)[0]
    lic = sib[:sib.index(pkg)]
    rel = os.path.relpath(sql_path(id_), EX)
    kind = 'IT' if cls.endswith('IT') else 'Test'
    return (f'{lic}{pkg}\n\nimport org.junit.jupiter.api.DisplayName;\nimport org.junit.jupiter.api.Nested;\n\n'
            f'/**\n * Answers the exercises of {{@code src/test/sql-exercises/{rel}}}; a nested class per exercise.\n */\n'
            f'@SuppressWarnings({{\n        "java:S101" // Class names should comply with a naming convention\n}})\n'
            f'class {cls} {{\n\n{nested(id_, title)}}}\n')


# ------------------------------------------------------------------------------------------------------------- apply
log = []
for c in D['changes']:
    id_, op = c['id'], c['op']
    adoc, yaml = read(ADOC), read(YAML)
    if op == 'fix':
        b = adoc_block(adoc, id_)
        p = adoc_parse(b[0])
        title = c.get('title', p['title'])
        request = c.get('request', p['request'])
        sql = c.get('sql', p['sql'])
        tail = '\n// NOT YET RUN\n\n' if c.get('rerun') else p['tail']
        write(ADOC, adoc[:b.start()] + adoc_render(id_, title, request, p['caption'], sql, tail) + adoc[b.end():])
        sp = sql_path(id_)
        st = read(sp)
        sb = sql_block(st, id_)
        lines = sb[0].rstrip('\n').split('\n')
        semi = max(i for i, l in enumerate(lines) if l == ';')
        outs = [l for l in lines[semi + 1:] if l.strip()]
        if c.get('rerun') and keeps_output(st):
            outs = ['-- NOT YET RUN']
        write(sp, st[:sb.start()] + sql_render(id_, title, request, sql, outs) + st[sb.end():])
        if 'title' in c:
            e = entry(read(YAML), id_)
            write(YAML, read(YAML)[:e.start()] + re.sub(r'(?m)^  title: .*$', f'  title: "{title}"', e[0], 1)
                  + read(YAML)[e.end():])
            jf, _ = test_file(id_)
            if jf:
                jt = read(jf)
                write(jf, re.sub(rf'@DisplayName\("{id_}: [^"]*"\)', f'@DisplayName("{id_}: {title}")', jt))
        log.append(f'fix {id_}')
    elif op == 'add':
        after = c['after']
        prefix, tier = id_.rsplit('_', 2)[0], id_.rsplit('_', 2)[1]
        ae = entry(yaml, after)
        section = field(ae[0], 'section')
        sqlrel = field(ae[0], 'sql')
        if id_.rsplit('_', 2)[1] != after.rsplit('_', 2)[1]:
            sys.exit(f'{id_}: after {after} is in another tier')
        acls = field(ae[0], 'test')
        cls = acls.split('.')[0] if acls else None
        # EXERCISES.asciidoc
        b = adoc_block(adoc, after)
        cap = adoc_parse(b[0])['caption']
        tail = '\n// NOT YET RUN\n\n' if c.get('rerun') else '\n'
        write(ADOC, adoc[:b.end()] + adoc_render(id_, c['title'], c['request'], cap, c['sql'], tail) + adoc[b.end():])
        # .sql
        sp = os.path.join(MOD, sqlrel)
        st = read(sp)
        sb = sql_block(st, after)
        outs = ['-- NOT YET RUN'] if c.get('rerun') and keeps_output(st) else []
        write(sp, st[:sb.end()] + sql_render(id_, c['title'], c['request'], c['sql'], outs) + st[sb.end():])
        # EXERCISES.yaml
        e = f'- id: {id_}\n  section: "{section}"\n  tier: {LEVEL[tier][1]}\n  title: "{c["title"]}"\n  sql: {sqlrel}\n'
        if cls:
            e += f'  test: {cls}.{id_}_Test\n'
        yaml = read(YAML)
        ae = entry(yaml, after)
        write(YAML, yaml[:ae.end()] + e + yaml[ae.end():])
        # the nested class
        jf, _ = test_file(after)
        if jf:
            jt = read(jf)
            jb = java_block(jt, after)
            write(jf, jt[:jb.end()] + '\n' + nested(id_, c['title']) + jt[jb.end():])
        log.append(f'add {id_} after {after}')
    elif op == 'remove':
        b = adoc_block(adoc, id_)
        write(ADOC, adoc[:b.start()] + adoc[b.end():])
        sp = sql_path(id_)
        st = read(sp)
        sb = sql_block(st, id_)
        write(sp, st[:sb.start()] + st[sb.end():])
        jf, _ = test_file(id_)
        if jf:
            jt = read(jf)
            jb = java_block(jt, id_)
            if jb:
                s = jt[:jb.start()].rstrip('\n') + '\n'
                write(jf, s + ('\n' if not jt[jb.end():].startswith('}') else '') + jt[jb.end():].lstrip('\n'))
        e = entry(read(YAML), id_)
        if 'retired: true' not in e[0]:
            y = read(YAML)
            write(YAML, y[:e.end()].rstrip('\n') + '\n  retired: true\n' + y[e.end():])
        log.append(f'remove {id_}')
    else:
        sys.exit(f'unknown op {op}')

for p, t in files.items():
    if p.endswith('.sql'):  # two blank lines before each ruler, one newline at the end
        t = re.sub(r'\n+(?=^-- -+ [A-Z0-9_]+ )', '\n\n\n', t, flags=re.M).rstrip() + '\n'
    if not DRY:
        open(p, 'w').write(t)
print('\n'.join(log))
print(('would write' if DRY else 'wrote'), *sorted(os.path.relpath(p, MOD) for p in files), sep='\n  ')
