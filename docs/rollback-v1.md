# Rollback guide: v1.0.0

Rollback version: `1`

Status: historical v1.0 release evidence; not a current rollback policy

The v1.0.0 release changes package/release identity and freezes contracts but
does not introduce a new proposal schema or machine-envelope version. The
default rollback from v1.0.0 to v0.6.0 is therefore class `direct` only when
read-only inspection confirms the project contains formats supported by
v0.6.0 and no partial transition remains.

## Boundaries

Package rollback replaces the complete installed `sdd-workflow/` directory.
It does not:

- revert source files or Git history;
- change proposal lifecycle or task completion;
- abandon an active proposal;
- move a terminal bundle back to active;
- delete `.sdd` metadata or version markers; or
- prove that an older Agent host/model still follows the same adapter contract.

These scopes require separate explicit authority.

## Read-only rollback preflight

Before pinning v0.6.0:

1. stop all Agent sessions using v1.0.0;
2. preserve the v1 package and project backups;
3. record v1 `--json --version`, discovery, and handshake;
4. run `status`, `doctor`, and `validate-index`;
5. inventory proposal schemas and every machine-envelope version; and
6. classify any incomplete operation using its authoritative commit point.

Direct rollback is allowed only for Schema v1/v2 and the v1 metadata,
approval, attestation, snapshot, archive, and terminal envelopes supported by
v0.6.0. Writer version `1.0.0` is diagnostic evidence; format versions decide
compatibility.

## Direct package rollback

1. Replace the complete package with the exact v0.6.0 distribution.
2. Do not merge files across releases.
3. Start a fresh host session.
4. Run package-local discovery, handshake, and `--json --version`.
5. Run project `status`, `doctor`, and `validate-index`.
6. Resume only if the older engine explicitly supports every observed format
   and no approval/attestation drift is present.

The older doctor may report engine writer-version skew. That warning is not
permission to ignore a narrower unsupported format.

## When direct rollback is unsafe

Use `finish-or-abandon` when an in-flight proposal contains a format the prior
engine cannot mutate: finish or abandon it with a compatible current engine,
then reassess. Use `restore-backup` only for a future committed format
migration with an explicit pre-migration backup. Use `forward-recovery` when a
terminal directory move or another authoritative commit point has committed
and derived state remains incomplete.

For terminal INDEX failure, the archive bundle remains authoritative. Rebuild
INDEX with a compatible engine; never move the terminal directory back.

## Roll-forward

If v0.6.0 cannot validate the installed package or project formats, restore the
complete v1 package, start a fresh session, run discovery/handshake, and use
the v1 recovery action. Preserve failure evidence and avoid repeated mutation
attempts with different engines.

## Verification

Rollback is complete only when:

- one complete package is discoverable;
- its Skill and runtime identity match;
- `status` and `doctor` are successful for affected projects;
- `validate-index` is clean or the documented rebuild has completed; and
- no proposal, archive, or Git state was changed outside an explicitly
  authorized operation.
