#!/usr/bin/env bash
# shellcheck disable=SC2153 # The upper-case variables come from the workflow and GITHUB_ENV.
# Copyright 2026 The flink-gcp authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Proposes one release to one consumer for the Update consumers workflow (ADR-0001).
# Each subcommand is one workflow step, run from this repository's root with the consumer checked out in
# CONSUMER_DIR. The steps pass state through GITHUB_ENV and GITHUB_OUTPUT as GitHub Actions does, and the
# prepare job hands the update to the propose job as files in UPDATE_DIR.
set -euo pipefail

dev_tools_dir="$PWD"
consumer_dir="${CONSUMER_DIR:-consumer}"
update_dir="${UPDATE_DIR:-$RUNNER_TEMP/update}"
# The consumer's single pin line; the first group is the commit.
pin_pattern='^dev_tools_revision := "([0-9a-f]{40})"$'
# How much of the patch the job summary shows; GitHub drops a summary over 1 MiB, so the bytes are bounded too.
summary_lines=1000
summary_bytes=262144
# The paths an update may change: the pin, the recipe copy, the installed skills and tools, and the Hugo module.
allowed_paths='^(justfile|dev-tools\.just|\.agents/skills/.+|scripts/[^/]+|docs/go\.(mod|sum))$'

fail() {
  echo "::error::$*"
  exit 1
}

# Sets pin to the commit that the justfile text names, failing unless exactly one line assigns it.
# It sets a variable rather than printing, so that its error is not captured by a command substitution.
read_pin() {
  local count
  count="$(grep -cE "$pin_pattern" <<< "$1" || true)"
  [[ "$count" == 1 ]] || fail 'justfile must assign dev_tools_revision a full commit SHA on exactly one line.'
  pin="$(sed -nE "s/$pin_pattern/\\1/p" <<< "$1")"
}

is_ancestor() {
  git -C "$dev_tools_dir" merge-base --is-ancestor "$1" "$2"
}

decide() {
  echo "action=$1" >> "$GITHUB_OUTPUT"
}

# Resolves the commit to propose: the PR head for a dry run, and otherwise the latest release, whichever tag or
# manual run started the workflow. Every run then converges on the same proposal, so a run that GitHub replaces
# or that runs late cannot hold back or undo a newer release.
resolve() {
  local target label dry_run tags
  if [[ "$EVENT" == pull_request ]]; then
    target="$HEAD_SHA"
    label="${HEAD_SHA:0:12}"
    dry_run=true
  else
    # Consumers pin only commits from the main history.
    tags="$(git tag --merged origin/main --list 'v*' --sort=-v:refname)"
    label="$(grep -m 1 -E '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' <<< "$tags" || true)"
    [[ -n "$label" ]] || fail 'main has no release tag such as v0.1.0.'
    target="$(git rev-parse --verify "refs/tags/$label^{commit}")"
    if [[ -n "${TAG:-}" && "$TAG" != "$label" ]]; then
      echo "::notice::This run proposes the latest release, $label, rather than $TAG."
    fi
    dry_run=false
  fi
  { echo "TARGET=$target"; echo "LABEL=$label"; echo "DRY_RUN=$dry_run"; } >> "$GITHUB_ENV"
}

# Decides what to do from the consumer's pin, its update branch, and its open update PR:
# skip, propose (push the update and open or update the PR), or describe (only refresh the PR's text).
# A dry run reads only the pin, so the consumer's open PRs cannot fail a pull request here.
state() {
  local pin previous base lease emails others prs number head proposed
  cd "$consumer_dir"
  # The update replaces this imported copy; a recipe pasted into the justfile would not be refreshed.
  git ls-files --error-unmatch dev-tools.just > /dev/null 2>&1 \
    || fail 'The consumer must track dev-tools.just and import it from its justfile.'
  read_pin "$(cat justfile)"
  previous="$pin"
  { echo "PREVIOUS=$previous"; echo "TITLE=Update flink-gcp-dev-tools to $LABEL"; } >> "$GITHUB_ENV"
  if [[ "$DRY_RUN" == true ]]; then
    decide propose
    return
  fi
  if [[ "$previous" == "$TARGET" ]]; then
    echo "::notice::$CONSUMER already pins $LABEL."
    decide skip
    return
  fi
  is_ancestor "$previous" "$TARGET" || fail "$LABEL does not descend from the current pin $previous."
  base="$(gh repo view "$CONSUMER" --json defaultBranchRef --jq .defaultBranchRef.name)"
  lease="$(git ls-remote origin "refs/heads/$BRANCH" | cut -f 1)"
  if [[ -n "$lease" ]]; then
    # A maintainer's commit on the branch, with or without an open PR, must not be overwritten;
    # checking the committer too catches a bot commit that a maintainer amended.
    emails="$(gh api "repos/$CONSUMER/compare/$base...$lease" --jq '.commits[].commit | .author.email, .committer.email')"
    others="$(grep -vxF "$BOT_EMAIL" <<< "$emails" || true)"
    [[ -z "$others" ]] || fail "$CONSUMER's $BRANCH has commits by others; finish or delete it before proposing $LABEL."
  fi
  # A fork's PR may use the same branch name, so keep only PRs from the consumer itself.
  prs="$(gh pr list -R "$CONSUMER" --head "$BRANCH" --state open --json number,headRefOid,isCrossRepository \
    --jq '.[] | select(.isCrossRepository | not) | "\(.number) \(.headRefOid)"')"
  number=''
  if [[ -n "$prs" ]]; then
    read -r number head <<< "$prs"
    proposed="$(gh api -H 'Accept: application/vnd.github.raw+json' "repos/$CONSUMER/contents/justfile?ref=$head")"
    read_pin "$proposed"
    proposed="$pin"
    if [[ "$head" == "$lease" && "$proposed" == "$TARGET" ]]; then
      # A rerun refreshes the PR's text, in case the previous run pushed but failed to edit it.
      decide describe
    elif [[ "$head" == "$lease" ]] && is_ancestor "$TARGET" "$proposed"; then
      echo "::notice::$CONSUMER#$number already proposes a release after $LABEL."
      decide skip
      return
    else
      decide propose
    fi
  else
    decide propose
  fi
  { echo "BASE=$base"; echo "LEASE=$lease"; echo "PR_NUMBER=$number"; } >> "$GITHUB_ENV"
}

# Fails unless the staged change touches only the allowed paths and names the target in both pins.
check_staged() {
  local pin names unexpected
  names="$(git diff --cached --name-only)"
  unexpected="$(grep -vE "$allowed_paths" <<< "$names" || true)"
  [[ -z "$unexpected" ]] || fail "The update changes unexpected paths: ${unexpected//$'\n'/, }"
  read_pin "$(cat justfile)"
  if [[ "$pin" != "$TARGET" ]] || ! grep -qF -- "-${TARGET:0:12}" docs/go.mod; then
    fail 'The justfile and docs/go.mod do not both name the new commit.'
  fi
}

# Moves both pins to the target, refreshes the recipe copy, synchronizes, and writes the change as a patch.
# This runs the consumer's recipe, so it runs without credentials in the prepare job.
apply() {
  cd "$consumer_dir"
  git -C "$dev_tools_dir" show "$TARGET:examples/dev-tools.just" > dev-tools.just
  sed -E "s/$pin_pattern/dev_tools_revision := \"$TARGET\"/" justfile > "$RUNNER_TEMP/justfile"
  cat "$RUNNER_TEMP/justfile" > justfile
  just dev-tools-sync
  (cd docs && hugo mod get "github.com/flink-gcp/flink-gcp-dev-tools/hugo@$TARGET" && hugo mod tidy)
  git add -A
  check_staged
  mkdir -p "$update_dir"
  git diff --cached --binary > "$update_dir/update.patch"
}

# Writes the PR body, which fills the consumer's WHAT and WHY sections, and the job summary.
describe() {
  local template=.github/PULL_REQUEST_TEMPLATE.md release matches status lines mentions=''
  cd "$consumer_dir"
  if [[ -f "$template" ]] && ! { grep -qx '## WHAT' "$template" && grep -qx '## WHY' "$template"; }; then
    fail "$template no longer has the WHAT and WHY sections this body fills."
  fi
  if [[ "$DRY_RUN" == true ]]; then
    release="\`$LABEL\`"
  else
    release="[\`$LABEL\`]($SHARED_URL/releases/tag/$LABEL)"
  fi
  # A permalink cites a file as it read at that commit, so a line naming the commit only in
  # permalinks stays true after the update and is left out. A full SHA after /blob/ or /tree/ is
  # a permalink only when a path, a fragment, a query or the end of a link or Markdown span follows
  # it. Anything else may continue a branch name such as <sha>-fix, so its line stays listed, which
  # costs the reader one line rather than hiding one. The loop keeps the character for the next match.
  if matches="$(git grep -n -F "$PREVIOUS" -- . ':!docs/go.sum')" &&
    matches="$(sed -E -e :a -e "s@/(blob|tree)/$PREVIOUS([]/#?)>\"'\`*[:space:]]|\$)@\\2@" -e ta <<< "$matches" | grep -F "$PREVIOUS")"; then
    mentions=$'\nThese lines still name the previous commit; update the ones that describe the current pin:\n\n'
    # shellcheck disable=SC2016 # The replacement writes a Markdown code span.
    mentions+="$(sed -E 's/^([^:]*:[0-9]*):.*/- `\1`/' <<< "$matches")"$'\n'
  else
    status=$?
    ((status == 1)) || exit "$status"
  fi
  cat > "$update_dir/body.md" << EOF
## WHAT

Update the shared development tools from flink-gcp-dev-tools \`${PREVIOUS:0:12}\` to $release (\`$TARGET\`).
\`dev_tools_revision\` in \`justfile\` and the Hugo module in \`docs/go.mod\` and \`docs/go.sum\` now name that commit.
\`dev-tools.just\` is the recipe copy from that commit, and the skills and tools are the output of \`just dev-tools-sync\`.

Shared changes since the previous pin: $SHARED_URL/compare/$PREVIOUS...$TARGET
$mentions
## WHY

flink-gcp-dev-tools released $LABEL, and its [Update consumers]($SHARED_URL/actions/workflows/update-consumers.yaml) workflow proposes the release here.
The shared changes were reviewed in flink-gcp-dev-tools; review what they change for this repository, following its guidance for dev-tools update PRs.
The workflow never marks this PR Ready or merges it.
EOF
  echo "$TARGET" > "$update_dir/target"
  # The summary shows the start of the patch; the job's artifact carries all of it.
  lines="$(wc -l < "$update_dir/update.patch")"
  head -n "$summary_lines" "$update_dir/update.patch" > "$RUNNER_TEMP/preview"
  head -c "$summary_bytes" "$RUNNER_TEMP/preview" > "$RUNNER_TEMP/preview.bounded"
  {
    echo "### $CONSUMER: $TITLE"
    echo
    cat "$update_dir/body.md"
    echo
    echo "<details><summary>Patch: $lines lines</summary>"
    echo
    echo '````diff'
    cat "$RUNNER_TEMP/preview.bounded"
    echo
    echo '````'
    if ! cmp -s "$RUNNER_TEMP/preview.bounded" "$update_dir/update.patch"; then
      echo "The patch continues in this job's artifact, update-${CONSUMER#*/}."
    fi
    echo
    echo '</details>'
  } >> "$GITHUB_STEP_SUMMARY"
}

# Returns the open update PR to Draft unless it is one, reading its current state rather than an earlier one.
ensure_draft() {
  local draft
  [[ -n "$PR_NUMBER" ]] || return 0
  draft="$(gh pr view "$PR_NUMBER" -R "$CONSUMER" --json isDraft --jq .isDraft)"
  if [[ "$draft" != true ]]; then
    gh pr ready "$PR_NUMBER" -R "$CONSUMER" --undo
  fi
}

# Applies the prepared patch as the bot's commit, pushes the update branch, and opens or updates the Draft PR.
# This runs in the propose job, whose checkout never ran consumer code; GH_TOKEN is the App token there.
push() {
  local header body
  cd "$consumer_dir"
  body="$update_dir/body.md"
  # A release tagged after the prepare job resolved is left to its own run, which follows this one.
  if [[ "$(cat "$update_dir/target")" != "$TARGET" ]]; then
    echo "::notice::The prepared update is not for the latest release, $LABEL; the run that $LABEL started proposes it."
    return
  fi
  if [[ "$ACTION" == propose ]]; then
    # New content needs the review again, so a Ready PR returns to Draft before the push, since a rerun only
    # describes a pushed update, and again after it, in case a maintainer marked it Ready in between.
    ensure_draft
    git apply --index "$update_dir/update.patch"
    # The patch came from a job that ran consumer code, so check it again here.
    check_staged
    # A hook cannot come from the patch, since git apply refuses paths in .git; disable hooks regardless.
    git -c core.hooksPath=/dev/null -c user.name="$BOT_LOGIN" -c user.email="$BOT_EMAIL" \
      commit --quiet -m "$TITLE" -m "Shared changes: $SHARED_URL/compare/$PREVIOUS...$TARGET"
    # The checkout kept no credentials; send the token to GitHub only, as actions/checkout does.
    header="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GH_TOKEN" | base64 | tr -d '\n')"
    git -c "http.https://github.com/.extraheader=$header" \
      push --quiet --force-with-lease="refs/heads/$BRANCH:$LEASE" origin "HEAD:refs/heads/$BRANCH"
    ensure_draft
  fi
  if [[ -z "$PR_NUMBER" ]]; then
    gh pr create -R "$CONSUMER" --draft --base "$BASE" --head "$BRANCH" --title "$TITLE" --body-file "$body"
    return
  fi
  # Runs are serialized, but a maintainer may have pushed since this run read the branch; describe only what it read.
  if [[ "$ACTION" == describe && "$(git ls-remote origin "refs/heads/$BRANCH" | cut -f 1)" != "$LEASE" ]]; then
    fail "$BRANCH moved after this run read it; rerun the workflow for the latest release."
  fi
  if [[ "$(gh pr view "$PR_NUMBER" -R "$CONSUMER" --json title,body --jq '"\(.title)\n\(.body)"')" \
    != "$TITLE"$'\n'"$(cat "$body")" ]]; then
    gh pr edit "$PR_NUMBER" -R "$CONSUMER" --title "$TITLE" --body-file "$body"
  fi
}

case "${1:-}" in
  resolve | state | apply | describe | push) "$1" ;;
  *) fail "Usage: $0 resolve|state|apply|describe|push" ;;
esac
