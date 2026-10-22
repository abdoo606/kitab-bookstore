#!/usr/bin/env bash
# Run every round-49 client backend test suite. No dependencies beyond Python 3.11.
set -u
cd "$(dirname "$0")"
fail=0
for suite in enveritas:eudr cable-energy:billing vlm-run:release_gate komodo-health:annex; do
  client="${suite%%:*}"
  module="${suite##*:}"
  printf '%-16s ' "$client"
  if out=$(cd "$client/backend" && python3 -m unittest "test_${module}" 2>&1); then
    echo "OK  $(echo "$out" | grep -oE 'Ran [0-9]+ tests' | head -1)"
  else
    echo "FAIL"
    echo "$out" | tail -20
    fail=1
  fi
done
exit $fail
