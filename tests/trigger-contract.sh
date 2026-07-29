#!/bin/sh

set -eu

skill_file=${1:-skills/sdd-workflow/SKILL.md}
readme_zh=README.md
readme_en=README.en.md
claude_file=CLAUDE.md

if [ ! -f "$skill_file" ]; then
  echo "trigger-contract: missing skill file: $skill_file" >&2
  exit 2
fi

description=$(
  awk '
    NR == 1 && $0 == "---" { in_frontmatter = 1; next }
    in_frontmatter && $0 == "---" { exit }
    in_frontmatter && /^description:/ { print; found = 1 }
    END { if (!found) exit 1 }
  ' "$skill_file"
) || {
  echo "trigger-contract: missing frontmatter description" >&2
  exit 1
}

case "$description" in
  *"取消提案"*) ;;
  *)
    echo "trigger-contract: frontmatter must include explicit 取消提案" >&2
    exit 1
    ;;
esac

description_without_cancel_proposal=$(printf '%s\n' "$description" | sed 's/取消提案//g')
case "$description_without_cancel_proposal" in
  *"取消"*)
    echo "trigger-contract: frontmatter must contain 取消 only as part of 取消提案" >&2
    exit 1
    ;;
esac

case "$description" in
  *"Generic cancellation without an explicit SDD proposal target is outside this skill."*) ;;
  *)
    echo "trigger-contract: frontmatter must exclude untargeted cancellation routing" >&2
    exit 1
    ;;
esac

case "$description" in
  *"Source-control or code rollback is outside SDD: confirm its exact scope before changing files and never alter proposal state because of it."*) ;;
  *)
    echo "trigger-contract: frontmatter must carry the code-revert scope safety boundary" >&2
    exit 1
    ;;
esac

grep -Fq 'A bare `取消`, or a cancellation request whose target is unclear—including' "$skill_file" || {
  echo "trigger-contract: missing bare-cancel disambiguation rule" >&2
  exit 1
}

grep -Fq '`取消剛才的程式碼修改`' "$skill_file" || {
  echo "trigger-contract: missing explicit code-revert handling example" >&2
  exit 1
}

grep -Fq 'Never offer a bare `取消` as a menu option' "$skill_file" || {
  echo "trigger-contract: phase menu must keep bare 取消 out of its options" >&2
  exit 1
}

grep -Fq 'scripts/discover-runtime.py' "$skill_file" || {
  echo "trigger-contract: missing package-local runtime discovery gate" >&2
  exit 1
}

grep -Fq '## Deterministic command contract' "$skill_file" || {
  echo "trigger-contract: missing deterministic CLI command contract" >&2
  exit 1
}

grep -Fq '`python3 <skill-dir>/scripts/sdd.py`' "$skill_file" || {
  echo "trigger-contract: skill must invoke the bundled CLI through python3" >&2
  exit 1
}

grep -Fq 'do not fall back to prose parsing' "$skill_file" || {
  echo "trigger-contract: CLI execution failure must fail closed" >&2
  exit 1
}

if grep -Eq 'Task checklist format and scanner|Checkbox-like line|shasum|sha256sum' "$skill_file"; then
  echo "trigger-contract: skill must not duplicate parser or hash implementation prose" >&2
  exit 1
fi

grep -Fq '> 版本 v1.1.0' "$readme_zh" || {
  echo "trigger-contract: README.md must report v1.1.0" >&2
  exit 1
}

grep -Fq '> Version v1.1.0' "$readme_en" || {
  echo "trigger-contract: README.en.md must report v1.1.0" >&2
  exit 1
}

for readme_file in "$readme_zh" "$readme_en"; do
  grep -Fq '`取消提案`' "$readme_file" || {
    echo "trigger-contract: $readme_file must document explicit 取消提案" >&2
    exit 1
  }
  grep -Fq 'Source-control rollback' "$readme_file" || {
    echo "trigger-contract: $readme_file must document the code-revert boundary" >&2
    exit 1
  }
done

grep -Fq '單獨說「取消」只會先詢問' "$readme_zh" || {
  echo "trigger-contract: README.md must exclude bare 取消 from direct routing" >&2
  exit 1
}

grep -Fq 'A standalone `取消` only asks whether' "$readme_en" || {
  echo "trigger-contract: README.en.md must exclude bare 取消 from direct routing" >&2
  exit 1
}

claude_without_cancel_proposal=$(sed 's/取消提案//g' "$claude_file")
case "$claude_without_cancel_proposal" in
  *"取消"*)
    echo "trigger-contract: CLAUDE.md must contain 取消 only as part of 取消提案" >&2
    exit 1
    ;;
esac

echo "trigger-contract: PASS"
