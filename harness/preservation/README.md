# Product preservation before edits and rebuilds

Run `preserve-product.py` **before each product edit or rebuild**, using the product's explicit directory and a separate archive root. It creates a new filtered source bundle, per-file hashes, and unique local tags for the images used by its currently running Compose containers. It does not build, restart, stop, export, publish, remove, or prune anything.

```sh
python3 harness/preservation/preserve-product.py \
  --project /absolute/path/to/ux-lab/products/002-example \
  --archive-root /absolute/path/to/ux-lab/archive/002-example
```

Proceed with an edit/build only when the command exits **0** and prints `"status":"complete"`. For a shell workflow, put the next action after a successful command with `&&`, or have the caller check the exit status. This tool does not execute the next action itself. No existing build command or CI job is automatically wrapped by its installation; future developers must invoke it until the parent workflow explicitly connects it. The UX Lab contract separately requires this step.

Additional private research, copyrighted raw pages, or external-data caches can be excluded explicitly:

```sh
python3 harness/preservation/preserve-product.py \
  --project /absolute/path/to/product \
  --archive-root /absolute/path/to/archive/product \
  --exclude 'research/raw/**' \
  --exclude 'references/full-market/*.html' \
  --exclude 'private-external-data/**'
```

`--exclude` is repeatable. Patterns are relative to the product: `*`, `?`, and bracket classes match within one path component; `**` matches zero or more whole components. For example, `**/*.html` matches HTML files at any depth. Absolute paths, `..`, backslashes, negated patterns, and malformed `**` components are rejected. Explicit exclusions add to the built-in policy; they cannot re-include secrets. The exact patterns, policy hash, and each skipped path/reason are recorded in the private manifest. Excluding a directory records its skipped tree without reading every child.

For a new product whose service has **never run**, or for source-only synthetic checks, use the explicit exception:

```sh
python3 harness/preservation/preserve-product.py \
  --project /absolute/path/to/synthetic-project \
  --archive-root /absolute/path/to/synthetic-archives \
  --no-docker
```

`--no-docker` runs no Docker command and records `docker_mode: explicitly_skipped`. It is not an image backup. In default mode, no scoped running Compose container or unavailable Docker is a failure; the tool does not silently fall back to source-only preservation.

An existing empty product directory is accepted: a first source-only snapshot can contain zero files before the first implementation, followed by another snapshot of the first coherent source before its initial build. The caller is responsible for that initial-product declaration; `--no-docker` cannot verify that the product never ran. For an existing product, resolve a missing Docker/Compose-image failure and run normal mode. Do not use the initial exception to bypass a failed image-preservation step.

## What a snapshot contains

Every run allocates a new directory named from the product, UTC microsecond timestamp, and UUID. It never reuses an existing destination, even on a collision. Snapshot directories are `0700`; archive/journal/manifest files are `0600`. A preexisting archive root must be owned by the caller and not writable by group/others. Its persistent `0600` lock serializes this harness's operations; the lock is retained.

| File | Meaning |
|---|---|
| `source.tar.gz` | Filtered source under the relative `source/` prefix; safe regular-file/directory entries only |
| `files.jsonl` | Included file SHA-256/byte size, original mode/mtime, and directory records |
| `events.jsonl` | Sequential, flushed stage/exclusion/tag events |
| `manifest.initial.json` | Initial identity, tool hash, exclusion policy/hash, limits and explicit Docker mode |
| `manifest.json` | Final `complete` or `failed` state, artifacts and hashes, exclusions, observed image IDs and tags |

A complete snapshot requires a final manifest with `status: complete`. A crash may leave only the initial manifest, journals, and a partial bundle; treat it as incomplete and preserve it. Failures after allocation retain partial artifacts and return nonzero. Invalid/unsafe roots fail before writing, because an unsafe location must not receive a failure artifact. If the final manifest itself cannot be written, the error output identifies the allocated snapshot when available. No failure cleanup removes snapshots or tags. A new attempt always makes another version; it does not repair or overwrite a previous one.

## Scope and exclusions

This is **filtered source preservation**, not a claim to capture every product byte. Defaults exclude `.env*`, `*.env`, known auth/credential material, private keys, local credential stores, database files/dumps, nested/compressed archives, `node_modules`, `.git`, Python environments, and common caches. Database magic/header checks also exclude a renamed PostgreSQL/SQLite/MySQL dump; ordinary SQL migrations remain. Packed files are skipped conservatively rather than opened to inspect nested content. Python environments are detected by `pyvenv.cfg` even under a custom directory name.

Generated/private agent trees `.agents`, `.claude`, `.codex`, and `.cursor` are excluded, including symlinked wrappers. Reinstall those from the separately maintained development harness. The per-snapshot policy and exclusion list expose the omission. Application source such as `auth/session.py`, `test_sessions.py`, `credentials/helper.ts`, and token-related JS/CSS is preserved; the directory or word alone does not discard ordinary source files. Exact private files such as `auth.json`, `credentials.json`, `.env`, or a private key remain excluded.

These rules are name/signature based, not a secret scanner: a credential embedded in otherwise ordinary code cannot be certified absent. Review a product's private material and add explicit exclusions for ambiguous runtime data or raw external research. Existing excluded data stays where it is; this tool does not delete it. Credentials and databases require their own separately authorized secure preservation/restore process. A dump is deliberately not included here.

Both roots must be explicit canonical POSIX directory paths without symlink components or `..`; the filesystem root and the caller's home/ancestors are refused as overly broad projects. The archive root must be outside the product. The walker uses directory descriptors, `O_NOFOLLOW`, and exclusive artifact creation. Non-excluded source symlinks are refused, including in-bounds links; hardlinks and special files are also refused. An exclusion can intentionally omit a generated link tree without following it. Do not bypass a failure by relocating the archive inside the product.

Included files are hashed as the exact archived bytes. Inode/size/mtime/ctime checks detect observed file/directory changes during traversal; root identities are rechecked. Stop editing while taking a snapshot. This is not an atomic filesystem snapshot or protection against every concurrent same-user mutation.

## Docker behavior and limits

The default path uses the current Docker CLI context. It lists only running containers whose `com.docker.compose.project.working_dir` label exactly matches the canonical product path. It then requests only container ID, immutable image ID, running state, and the selected Compose project/service/working-directory labels. It does **not** run `compose config`, expand `.env`, print raw inspect/config/environment objects, read container logs, or forward raw Docker stdout/stderr on failure. Missing/mismatched labels fail instead of widening the search to other products.

Each distinct image ID gets a reference of the form `uxlab-preserved/<product>:<timestamp>-<uuid>-<image-id-prefix>`. A preexisting reference is refused before tagging, each resulting tag is verified against its immutable image ID, and failed verification retains the planned reference in the manifest. The only mutating Docker operation is local `image tag`. There is no push, pull, save/export, commit, container lifecycle, deletion, prune, or volume command.

Docker's [tag API](https://docs.docker.com/reference/api/engine/version/v1.51/) can overwrite an existing tag and has no atomic create-only option. Unique UUIDs, absence checks, a harness lock, and post-verification prevent this tool's normal invocations from overwriting their references; they cannot stop an independent Docker client from racing, retagging, or deleting them. Local tags keep images referenced on the current daemon, but are **not a portable/off-host image backup**. A full Docker save is not implemented. Container writable layers, environment/config values, mounts, and database/volume contents are not backed up. Separately authorized database backups must be preserved separately.

Primary references: Docker documents [formatted metadata output](https://docs.docker.com/reference/cli/docker/container/ls/); Compose's [label constants](https://pkg.go.dev/github.com/docker/compose/v2/pkg/api) identify its working-directory label. This tool uses selected label fields instead of dumping configuration.

## Synthetic verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 harness/preservation/tests/test_preserve_product.py
```

The 24 standard-library tests use retained synthetic projects and a fake Docker adapter. They check the first empty-product snapshot, secrets/data exclusions beside ordinary auth-code preservation, relative glob behavior, private permissions, per-file/tar hashes, root/link escapes, hardlinks/FIFOs, changing-source failure, immutable prior snapshots/collision refusal, explicit no-Docker behavior, scoped image metadata/tagging, existing-tag refusal, partial failure state, redacted errors, and CLI nonzero status. No existing product or real Docker daemon is operated by the tests.

Each run is kept under `harness/preservation/tests/runs/<timestamp>-<uuid>/`, with a private `test-result.json`; no synthetic run is cleaned up. These tests establish the implemented boundaries, not a completed live Docker preservation run. The parent workflow will perform the first actual product use separately.
