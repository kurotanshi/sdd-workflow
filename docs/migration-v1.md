# Migration guide: v0.6.0 to v1.0.0

Migration version: `1`

Status: v1 release guide

The v1.0.0 release freezes existing proven behavior. It does not introduce
Schema v3 or a new machine-envelope version. Proposal Schema v1/v2 and active,
approval, attestation, archive, snapshot, and terminal formats remain at their
documented version `1`/`2` axes. Migration therefore replaces one complete
package and validates existing projects; it does not rewrite proposal data.

## Supported sources and result

| Source | Read after upgrade | Managed mutation after upgrade | Required handling |
| --- | --- | --- | --- |
| v0.6.0 package with Schema v1/v2 proposal and v1 machine envelopes | Yes | Yes when ordinary approval/attestation gates pass | Direct package upgrade. |
| v0.4/v0.5 managed proposal | Yes | Yes when all envelope versions are supported | Run `status` and `doctor`; writer version remains evidence only. |
| Unmanaged draft | Yes | Yes after explicit approval establishes managed evidence | Normal `開始實作` path. |
| Approved v1 proposal without Approval Manifest | Yes | No until reconfirmed | Explicit `--establish-manifest`; never silently adopt. |
| Readable legacy proposal | Conditional read | No | Recreate/upgrade through an explicit proposal; do not mutate legacy bytes. |
| Unknown future schema or envelope | No for affected operation | No | Use a compatible engine; do not strip the version. |

The target package MUST report engine `1.0.0`, protocol
`sdd-protocol-1.0`, CLI output `1`, handshake `1`, schema range `1..2`, and the
documented required capabilities.

## Preflight

Before replacing an installed package:

1. identify every host-native installation path in use;
2. record the current `--json --version` and package-local discovery results;
3. run project `status`, `doctor`, and `validate-index` read-only;
4. finish any partially committed terminal recovery indicated by the runtime;
5. preserve a byte-for-byte backup of the complete installed package; and
6. preserve project/Git backups according to local policy without changing SDD
   lifecycle state.

Do not start from a dirty mixed package, a `SKILL.md`-only copy, or an
ambiguous discovery result.

## Upgrade

1. Stop Agent sessions using the old package.
2. Replace the complete `sdd-workflow/` directory as one distribution unit.
3. Do not merge old/new `SKILL.md`, identity, scripts, or runtime modules.
4. Start a fresh Agent session so host loading is observable.
5. Run the installed package's `scripts/discover-runtime.py`.
6. Run `scripts/sdd.py --json --handshake` and `--json --version`.
7. For each project, run read-only `status`, `doctor`, and `validate-index`.
8. Resume mutation only when package identity, formats, approval, attestation,
   and project authority all validate.

The upgrade MUST NOT edit `proposal.md`, `tasks.md`, `.sdd`, archive bundles,
or `INDEX.md` merely to make version output look current.

## Validation

For source or release-package installation, require:

- package validation and fresh-install smoke;
- complete lifecycle smoke with uninstall/no-residue;
- runtime and public conformance suites;
- CLI JSON regression fixtures;
- recovery drills;
- example and composition smoke; and
- supported Agent host/model evidence named by the v1 eval report.

A successful runtime handshake proves the package only. A fresh host session
is still required to prove which Skill the host loaded.

## Failed migration

If replacement fails before the new package is used for mutation, restore the
complete package backup and re-run discovery. If any managed operation ran,
first inspect current artifact/envelope versions and operation evidence. Use
the rollback classification in [`rollback-v1.md`](./rollback-v1.md); do not
combine package rollback with Git or proposal-state rollback.
