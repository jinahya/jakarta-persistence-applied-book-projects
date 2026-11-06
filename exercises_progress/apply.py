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

A fix changes only the keys it gives. "rerun": true puts NOT YET RUN where the output is: in EXERCISES.asciidoc, and in
the .sql file where the module keeps output there (above the statement or under it, as the file does); an exercise with
a parameter shows no output, so give it false. An add goes after "after", in the same .sql file. A remove retires the
id in EXERCISES.yaml and takes the exercise out of EXERCISES.asciidoc, its .sql file and its test class.

"sql_comment" (a fix or an add) is the comment above the statement in the .sql file, as lines; without it the request
is used where the file's comments are the request, and the title otherwise. Each .sql file keeps its own layout: a
ruler with or without the title, the output above or under the statement, and its blank lines between exercises.
"""
import collections, glob, json, os, re, sys, textwrap

LEVEL = {'B': ('01_basic', 'Basic'), 'I': ('02_intermediate', 'Intermediate'), 'A': ('03_advanced', 'Advanced')}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = '--dry' in sys.argv
D = json.load(open(sys.argv[1]))
MOD = os.path.join(ROOT, D['module'])
EX = os.path.join(MOD, 'src/test/sql-exercises')
ADOC, YAML = os.path.join(EX, 'EXERCISES.asciidoc'), os.path.join(EX, 'EXERCISES.yaml')
NOT_YET_RUN = 'NOT YET RUN'
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
        return None
    name = t.split('.')[0] + '.java'
    pending = [p for p in files if os.path.basename(p) == name]  # a class this run creates
    f = pending or glob.glob(os.path.join(MOD, 'src/test/java-exercises/**', name), recursive=True)
    return f[0] if f else None


# ---------------------------------------------------------------------------------------------------------- asciidoc
def adoc_block(t, id_):
    m = re.search(rf'(?ms)^\[\[{id_}\]\]\n.*?(?=^\[\[[A-Z0-9_]+\]\]\n|^==?=? |\Z)', t)
    if not m:
        sys.exit(f'{id_}: not in EXERCISES.asciidoc')
    return m


def adoc_parse(block):
    m = re.match(r'(?ms)\[\[(\S+)\]\]\n==== \S+: (.*?)\n\n(.*?)\n\n\.`([^`]+)`, \S+\n\[%collapsible\]\n====\n'
                 r'\[source,sql\]\n----\n(.*?)\n----\n(.*)^====\n(.*)$', block)
    if not m:
        sys.exit('cannot parse block:\n' + block[:400])
    # gap: what follows the closing ==== (blank lines, and a line such as "Answered by ...", kept as it is)
    return {'title': m[2], 'request': m[3].split('\n'), 'caption': m[4], 'sql': m[5], 'tail': m[6], 'gap': '\n' + m[7]}


def rerun_tail(tail):
    """The tail with its output (a literal block, a 'N rows; ...' note) replaced by NOT YET RUN; other lines kept."""
    t = re.sub(r'(?ms)^\.{4,}\n.*?^\.{4,}\n', f'// {NOT_YET_RUN}\n', tail, count=1)
    t = re.sub(r'(?ms)^\.{4,}\n.*?^\.{4,}\n', '', t)
    t = re.sub(r'(?m)^\d+ rows?[;,.].*\n', '', t)
    if NOT_YET_RUN not in t:
        t = f'\n// {NOT_YET_RUN}\n' + t.lstrip('\n')
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t if t.endswith('\n\n') else t.rstrip('\n') + '\n\n'


def adoc_render(id_, title, request, caption, sql, tail, gap):
    return (f'[[{id_}]]\n==== {id_}: {title}\n\n' + '\n'.join(request) + '\n\n'
            f'.`{caption}`, {id_}\n[%collapsible]\n====\n[source,sql]\n----\n{sql.strip()}\n----\n{tail}===={gap}')


# --------------------------------------------------------------------------------------------------------------- sql
def ruler_re(id_=r'[A-Z][A-Z0-9_]+'):
    return rf'^-- -+ {id_}(?: [^\n]*)?$'


def sql_block(t, id_):
    m = re.search(rf'(?ms){ruler_re(id_)}\n.*?(?={ruler_re()}|\Z)', t)
    if not m:
        sys.exit(f'{id_}: no ruler in the .sql file')
    return m


def is_output(line):
    """A comment line that is output: a table, 'no rows.', '... N rows in all.', or the NOT YET RUN marker."""
    return (bool(re.match(r'-- (?:[+|]|no rows\b|\.\.\. \d+ rows?\b|\(\d+ rows?\))', line))  # MySQL, and psql's count
            or bool(re.match(r'-- -+(?:\+-+)+\s*$', line))  # psql's rule under the header
            or ' | ' in line or line.rstrip().endswith(' |')  # a row of a table
            or NOT_YET_RUN in line)


def sql_parse(block):
    """ruler, comments (above the statement, less the output), output above, statement, output under, gap."""
    lines = block.rstrip('\n').split('\n')
    gap = len(block) - len(block.rstrip('\n')) - 1
    i, comments, above = 1, [], []
    while i < len(lines) and lines[i].startswith('--'):
        (above if above or is_output(lines[i]) else comments).append(lines[i])
        i += 1
    j = next(k for k in range(i, len(lines)) if lines[k] == ';')
    return {'ruler': lines[0], 'comments': comments, 'above': above, 'stmt': lines[i:j], 'under': lines[j + 1:],
            'gap': gap}


def layout(t):
    """How the file lays its exercises out: a title on the ruler, the output above or under, the blank lines."""
    rulers = re.findall(r'(?m)^-- -+ [A-Z][A-Z0-9_]+( .*)?$', t)
    gaps = collections.Counter(len(m) for m in re.findall(r'(?m)^;\n(\n*)(?=-- -+ [A-Z])', t))
    blocks = [sql_parse(b) for b in re.findall(rf'(?ms){ruler_re()}\n.*?(?={ruler_re()}|\Z)', t)]
    return {'title': any(r for r in rulers),
            'above': any(b['above'] for b in blocks),
            'under': any(l.startswith('--') for b in blocks for l in b['under']),
            'gap': gaps.most_common(1)[0][0] if gaps else 2,
            'request': None}


def ruler(id_, title, with_title, width=120):
    s = f' {id_} {title}' if with_title else f' {id_}'
    return '-- ' + '-' * max(4, width - 3 - len(s)) + s


def ruler_width(t):
    """The width the file draws its rulers to, the most common."""
    widths = collections.Counter(len(l) for l in re.findall(r'(?m)^-- -+ [A-Z][A-Z0-9_]+(?: [^\n]*)?$', t))
    return widths.most_common(1)[0][0] if widths else 120


def wrap(text):
    return ['-- ' + l for l in textwrap.wrap(text, 117, break_long_words=False, break_on_hyphens=False)]


def sql_render(id_, title, comment_lines, above, sql, under, with_title, gap, width=120, keep_ruler=None):
    body = [keep_ruler or ruler(id_, title, with_title, width)] + comment_lines + above + [sql.strip().rstrip(';').rstrip(), ';'] + under
    return '\n'.join(body) + '\n' * (gap + 1)


def comment_for(c, request, title, prev, prev_title):
    """The comment above the statement: given, or like the file's, which writes either the title or the request."""
    if 'sql_comment' in c:
        return [l if l.startswith('--') else '-- ' + l for l in c['sql_comment']]
    text = ' '.join(l[3:] for l in prev or []).lower()
    if prev and prev_title and text.startswith(prev_title.lower()[:25]):  # the file writes the title
        if title == prev_title and c.get('op') == 'fix':
            return prev
        return wrap(title + ('' if title.endswith('.') else '.'))
    return wrap(' '.join(request))


# -------------------------------------------------------------------------------------------------------------- java
def nested(id_, title):
    t = title.replace('\\', '\\\\').replace('"', '\\"')
    return f'    @DisplayName("{id_}: {t}")\n    @Nested\n    class {id_}_Test {{\n    }}\n'


def java_block(t, id_):
    # an annotation may run over continuation lines, indented deeper (a long @DisplayName)
    return re.search(rf'(?ms)(?:^    //[^\n]*\n)*(?:^    @[^\n]*\n(?:^ {{8,}}[^\n]*\n)*)*^    class {id_}_Test \{{.*?^    }}\n', t)


# ---------------------------------------------------------------------------------------------- a tier's first exercise
def new_sql_file(sibling_path, new_rel, tier, file_header):
    """A .sql file for a level that has none yet: the sibling's header, for the new level and path."""
    st = read(sibling_path)
    m = re.search(ruler_re(), st, re.M)
    head = st[:m.start()] if m else st
    old_rel = os.path.relpath(sibling_path, MOD)
    head = head.replace(old_rel, new_rel)
    level = LEVEL[tier][1].lower()
    if file_header:
        head = re.sub(r'(?ms)^-- Exercises .*?(?=^--\n)', '\n'.join(wrap(file_header)) + '\n', head, count=1)
    else:
        head = re.sub(r'at the \w+ level', f'at the {level} level', head, count=1)
    return head


def new_test_class(sibling_file, cls, sql_rel):
    """A test class for a level that has none yet, modelled on the sibling's license, package and javadoc."""
    t = read(sibling_file)
    pkg = re.search(r'(?m)^package [^;]+;$', t)
    lic = t[:pkg.start()]
    after = re.match(r'(?s)\n*(/\*(?!\*).*?\*/\n)', t[pkg.end():])  # a license comment after the package line
    lic_after = '\n' + after[1] if after else ''
    doc = re.search(r'(?ms)^/\*\*\n.*?^ \*/\n', t[pkg.end():])
    old_sql = re.search(r'src/test/sql-exercises/[^}\s]+\.sql', doc[0]) if doc else None
    javadoc = doc[0].replace(old_sql[0], sql_rel) if old_sql else \
        f'/**\n * Answers the exercises of {{@code {sql_rel}}}; a nested class per exercise.\n */\n'
    return (f'{lic}{pkg[0]}\n{lic_after}\nimport org.junit.jupiter.api.DisplayName;\nimport org.junit.jupiter.api.Nested;\n\n'
            f'{javadoc}@SuppressWarnings({{\n        "java:S101" // Class names should comply with a naming convention\n}})\n'
            f'class {cls} {{\n}}\n')


# ------------------------------------------------------------------------------------------------------------- apply
log = []
for c in D['changes']:
    id_, op = c['id'], c['op']
    adoc = read(ADOC)
    if op == 'fix':
        b = adoc_block(adoc, id_)
        p = adoc_parse(b[0])
        title = c.get('title', p['title'])
        request = c.get('request', p['request'])
        sql = c.get('sql', p['sql'])
        tail = rerun_tail(p['tail']) if c.get('rerun') else p['tail']
        write(ADOC, adoc[:b.start()] + adoc_render(id_, title, request, p['caption'], sql, tail, p['gap'])
              + adoc[b.end():])
        sp = sql_path(id_)
        st = read(sp)
        lay = layout(st)
        sb = sql_block(st, id_)
        s = sql_parse(sb[0])
        comment = s['comments'] if not ('request' in c or 'title' in c or 'sql_comment' in c) \
            else comment_for(c, request, title, s['comments'], p['title'])
        above, under = s['above'], s['under']
        if c.get('rerun'):
            if lay['above']:
                above = [f'-- {NOT_YET_RUN}']
            elif lay['under']:
                under = [f'-- {NOT_YET_RUN}']
        stmt = sql if 'sql' in c else '\n'.join(s['stmt'])  # the .sql file's own statement, unless it changes
        keep = s['ruler'] if not (lay['title'] and 'title' in c) else None  # the ruler stays unless its title changes
        write(sp, st[:sb.start()] + sql_render(id_, title, comment, above, stmt, under, lay['title'], s['gap'],
                                               ruler_width(st), keep)
              + st[sb.end():])
        if 'title' in c:
            y = read(YAML)
            e = entry(y, id_)
            write(YAML, y[:e.start()] + re.sub(r'(?m)^  title: .*$', f'  title: "{title}"', e[0], count=1) + y[e.end():])
            jf = test_file(id_)
            if jf:
                write(jf, re.sub(rf'@DisplayName\("{id_}: [^"]*"\)', f'@DisplayName("{id_}: {title}")', read(jf)))
        log.append(f'fix {id_}')
    elif op == 'add':
        after = c['after']
        if after == 'last':  # the last live exercise of the section and tier, or of the section
            sec = id_.rsplit('_', 2)[0]
            live = [(i, b) for i, b in re.findall(r'(?ms)^- id: (\S+)\n(.*?)(?=^- id: |^# ---|\Z)', read(YAML))
                    if i.rsplit('_', 2)[0] == sec and 'retired: true' not in b and i != id_]
            same = [i for i, _ in live if i.rsplit('_', 2)[1] == id_.rsplit('_', 2)[1]]
            order = {'B': 0, 'I': 1, 'A': 2}
            after = same[-1] if same else sorted((i for i, _ in live), key=lambda i: (order[i.rsplit('_', 2)[1]],
                                                                                        i))[-1]
        tier = id_.rsplit('_', 2)[1]
        y = read(YAML)
        ae = entry(y, after)
        section, sqlrel, atest = field(ae[0], 'section'), field(ae[0], 'sql'), field(ae[0], 'test')
        first = tier != after.rsplit('_', 2)[1]
        if first:  # the first exercise of its tier: a new .sql file, a heading, a test class
            sibling = os.path.join(MOD, sqlrel)
            sqlrel = os.path.join(os.path.dirname(sqlrel), LEVEL[tier][0] + '.sql')
            sp = os.path.join(MOD, sqlrel)
            if os.path.exists(sp) or sp in files:
                sys.exit(f'{id_}: {sqlrel} exists; add after an exercise of the same tier')
            write(sp, new_sql_file(sibling, sqlrel, tier, c.get('file_header')))
            if atest:
                acls = atest.split('.')[0]
                ncls = re.sub(r'_0[123]_[A-Za-z]+_Persistence', f'_{LEVEL[tier][0][:2]}_{LEVEL[tier][1]}_Persistence', acls)
                jf_sib = test_file(after)
                if jf_sib:
                    nf = os.path.join(os.path.dirname(jf_sib), ncls + '.java')
                    write(nf, new_test_class(jf_sib, ncls, sqlrel))
                atest = f'{ncls}.x'
        # EXERCISES.asciidoc
        b = adoc_block(adoc, after)
        p = adoc_parse(b[0])
        tail = f'\n// {NOT_YET_RUN}\n\n' if c.get('rerun') else '\n'
        blank = re.search(r'\n*$', p['gap'])[0]  # the blank lines only; "Answered by ..." belongs to the other
        caption = p['caption'] if not first else os.path.relpath(os.path.join(MOD, sqlrel), EX)
        heading = f'=== {LEVEL[tier][1]}\n\n' if first else ''
        write(ADOC, adoc[:b.end()] + heading + adoc_render(id_, c['title'], c['request'], caption, c['sql'], tail,
                                                           blank if len(blank) >= 2 else '\n\n')
              + adoc[b.end():])
        # .sql
        sp = os.path.join(MOD, sqlrel)
        st = read(sp)
        src = read(os.path.join(MOD, field(ae[0], 'sql')))  # the file of 'after', for the layout and the comment
        lay = layout(src)
        if not re.search(r'(?m)^;\n\n*-- -+ [A-Z]', src):  # one exercise so far: the gaps of the files beside it
            for o in sorted(glob.glob(os.path.join(os.path.dirname(sp), '*.sql'))):
                if re.search(r'(?m)^;\n\n*-- -+ [A-Z]', read(o)):
                    lay['gap'] = layout(read(o))['gap']
                    break
        sb = sql_block(src, after)
        s = sql_parse(sb[0])
        comment = comment_for(c, c['request'], c['title'], s['comments'], adoc_parse(adoc_block(read(ADOC), after)[0])['title'])
        above = [f'-- {NOT_YET_RUN}'] if c.get('rerun') and lay['above'] else []
        under = [f'-- {NOT_YET_RUN}'] if c.get('rerun') and lay['under'] and not lay['above'] else []
        block = sql_render(id_, c['title'], comment, above, c['sql'], under, lay['title'], lay['gap'], ruler_width(src))
        if first:
            write(sp, st.rstrip('\n') + '\n' * 3 + block)
        else:
            sb = sql_block(st, after)
            head = st[:sb.end()].rstrip('\n') + '\n' * (lay['gap'] + 1)
            write(sp, head + block + st[sb.end():])
        # EXERCISES.yaml
        e = f'- id: {id_}\n  section: "{section}"\n  tier: {LEVEL[id_.rsplit("_", 2)[1]][1]}\n  title: "{c["title"]}"\n' \
            f'  sql: {sqlrel}\n'
        if atest:
            e += f'  test: {atest.split(".")[0]}.{id_}_Test\n'
        write(YAML, y[:ae.end()] + e + y[ae.end():])
        # the nested class
        jf = test_file(id_)
        if jf and first:
            jt = read(jf)
            write(jf, jt.rstrip().rstrip('}').rstrip('\n') + '\n\n' + nested(id_, c['title']) + '}\n')
        elif jf:
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
        jf = test_file(id_)
        if jf:
            jt = read(jf)
            jb = java_block(jt, id_)
            if jb:
                rest = jt[jb.end():].lstrip('\n')
                write(jf, jt[:jb.start()].rstrip('\n') + '\n' + ('' if rest.startswith('}') else '\n') + rest)
        y = read(YAML)
        e = entry(y, id_)
        if 'retired: true' not in e[0]:
            write(YAML, y[:e.end()].rstrip('\n') + '\n  retired: true\n' + y[e.end():])
        log.append(f'remove {id_}')
    else:
        sys.exit(f'unknown op {op}')

for p, t in files.items():
    if p.endswith('.sql'):
        t = t.rstrip() + '\n'
    if not DRY:
        open(p, 'w').write(t)
print('\n'.join(log))
print(('would write' if DRY else 'wrote'), *sorted(os.path.relpath(p, MOD) for p in files), sep='\n  ')
