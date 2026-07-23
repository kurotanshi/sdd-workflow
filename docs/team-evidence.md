# Team trial and friction evidence

Status: v0.10 opt-in aggregate contract

`evals/team-evidence-spec-v1.json` defines the only repository-supported team
trial aggregate. Its report shape is versioned by
`evals/schema/team-evidence-v1.schema.json`.

## Consent and collection boundary

Collection is manual and opt-in for each study. The runtime, Skill, package,
and examples enable no telemetry or upload path. Declining participation has
no effect on workflow behavior.

Repository evidence contains aggregate counts and reviewed friction-entry IDs
only. It does not contain:

- operator names, account IDs, email addresses, or stable pseudonyms;
- repository names or local paths;
- proposal, task, source, metadata, or customer content;
- prompts, raw Agent transcripts, tool traces, or command payloads; or
- credentials, tokens, environment variables, or machine identifiers.

Raw observation notes are not accepted into this repository and have a
default retention of zero days. A study needing private raw evidence requires
separate consent, access control, retention, and deletion review before
collection; its raw material never becomes a team-evidence report.

## Required report facts

Every report records:

1. evidence format version and a non-identifying study ID;
2. inclusive UTC observation start and finish;
3. aggregate counts of operators, sessions, proposals, and mutation attempts;
4. environment families without machine or account identity;
5. every metric as an integer numerator, denominator, and unit;
6. reviewed friction-log IDs, if any; and
7. the complete fail-closed privacy declaration from the specification.

A zero denominator is reported as `0/0`, meaning not observed. It is never
rendered as 0%, 100%, or evidence that the event cannot occur. Counts do not
identify an actor or infer why an event happened.

## Metric interpretation

The versioned specification owns each numerator and denominator. In
particular, snapshot-stale results are divided by mutation attempts, INDEX
conflicts by terminal or INDEX-merge operations, and workflow bypass
observations by lifecycle operations. Reports must not substitute a more
favorable denominator or omit a zero-result metric that was in scope.

Friction belongs in `docs/friction-log.md` only when an independently
observable failure or material operator cost was reproduced. The aggregate
may reference its stable ID; it must not copy sensitive evidence or an
unreviewed narrative into JSON.
