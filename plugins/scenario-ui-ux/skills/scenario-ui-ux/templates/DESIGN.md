# Design agreement

## Task and user scenario

Replace this with the current project/task, the user, the action they need to complete, and the expected result. A new task needs a new description; do not rename task_id to bypass retained failures.

## Structure and feedback

Describe the primary action, what is initially visible, what is opened on demand, and what the user praised and asked to preserve. Record the user's exact feedback/source IDs and the scope of any interpretation. Token consistency alone does not establish UX quality.

## Runtime evidence

The configured browser test must perform the task, write expected vs observed behavior and screenshots under .design-audit/, and report failures honestly. Functional validation and the user's design preference remain separate. AI critique is optional until the dedicated Codex Broker is authenticated; required unavailable stages fail the gate.

## Permissions and exceptions

Source and user data are read-only to this pipeline. Only explicitly reviewed argv commands may run; they are executable code, not a sandbox. Use fixture data and a read-only container mount where possible. Every legacy allowance is file/value scoped with a reason. No paid assets, new services, external writes, or expanded permissions follow from a hook or reference.

<!-- design-contract: design-contract.example.json sha256:146ea138cf50b16da0bb30b5615dc923025fc51bd2eff4fec25368e56ac97712 -->
