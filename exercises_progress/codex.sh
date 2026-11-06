#!/bin/sh
# codex.sh <dir> [<prompt file>] -- a blind review by Codex of the inputs in <dir>, into <dir>/review-codex.md
# (or, with a prompt file, the reply into <dir>/review-codex-reply.md). Read-only; prints the exit status.
d=$(cd "$1" && pwd)
p=${2:-$(dirname "$0")/CODEX_PROMPT.md}
out=$d/review-codex.md; log=$d/codex.log
[ -n "$2" ] && out=$d/review-codex-reply.md && log=$d/codex-reply.log
codex exec -s read-only --skip-git-repo-check -C "$d" -o "$out" "$(cat "$p")" < /dev/null > "$log" 2>&1
echo "$d: exit $?"
