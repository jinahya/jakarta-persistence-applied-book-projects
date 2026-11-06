#!/usr/bin/env python3
# nextid.py <EXERCISES.yaml> <PREFIX_SECTION_T> ... -- the next unused id of each section and tier, retired ids counted
import re, sys
y = open(sys.argv[1]).read()
ids = set(re.findall(r'(?m)^- id: (\S+)', y))
for st in sys.argv[2:]:
    n = max([int(i.rsplit('_', 1)[1]) for i in ids if i.rsplit('_', 1)[0] == st] or [0])
    print(f'{st}_{n + 1:02d}')
