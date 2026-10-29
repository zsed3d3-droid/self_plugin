# Self Plugin development contract

Read the project harness and the matching skill before implementation. Use gstack as the base flow: requirements and a concrete user task, relevant references, implementation, actual browser task, causal diagnosis, narrow repair, the same task again, and a record of why the change helped. Retrieve earlier cases by symptom and cause; recorded cases are conditional evidence, not automatic user preferences.

All new services require Dockerfile, Compose, healthcheck and an explicit persistent-data contract. The separately approved Mac MLX Metal speech engine is the sole host-service exception. CLI tools and short-lived tests are not services. Use current official documentation when choosing or updating a stack; pinned versions here are reproducibility records, not a permanent claim to be latest.

Preserve source, images, data, earlier outputs, failures and reasons before edits or rebuilds. Invoke `harness/preservation/preserve-product.py` with explicit safe roots. A complete source snapshot is not a database backup or actual restore. Never delete old products, prune Docker, run `down -v`, overwrite archives or label unexecuted checks as passed.

Separate user feedback, agent task observations, source inspection, test-harness failures and hypotheses. Do not promote assistant examples to adopted user rules. Personal policies stay in private project paths. Existing authentication is never copied. Do not publish deployments, spend money or send messages unless the user authorizes that action.

The hook installer does not approve host trust. The optional Codex visual critic stays unavailable until the user completes its dedicated login. Capacity retry is enabled only through a verified same-session delivery adapter; an implemented observer alone is not an active retry hook.
