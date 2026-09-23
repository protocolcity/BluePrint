# Covenant

Human authorization defines the work an agent may do. Provider choice does not
change that authority. This contract applies to interactive and unattended work.

| Actor | Authority | Identity and responsibility |
|---|---|---|
| You | Own the requested outcome and grant permissions | The acting human |
| Interactive session | Acts within the user's current authorized scope | Records the acting identity and session evidence supported by the tools |
| Registered agent | Acts within its contract and dispatch authorization | Signs as its registered identity and owns its claim |

An interactive session does not have unlimited authority merely because a human
opened it. A scheduled agent does not acquire permission from a task description
outside its contract. Honor authorization already given; ask only for a missing
real decision, credential, permission or irreversible choice needed for the work.

Keep the responsible agent assigned when escalating. Record the exact blocker
and required action as a human gate. Do not hide failed agent work in a personal
queue or reopen gates to improve queue counts.

## Interrupted work

Before ending or changing providers, preserve edits and record a continuation
checkpoint on the owning work order. Include source/checkout identity, objective,
acceptance, work completed, verification, pending work and next action. Commit
reviewable owned changes when appropriate; preserve unfinished edits otherwise.
Never auto-commit unrelated files merely to clear a dirty checkout.

A new process must verify that the prior process stopped before transferring a
claim. It must recheck the current instructions and source. A note is not a lock,
and an expired heartbeat is not process termination evidence. Automated recovery
exists only where the installed engines implement and verify it.

## Multiple people

Each action and approval must identify its actual actor. Route a gate to the
person authorized for that decision. Shared access, role enforcement and remote
identity require explicit implementation and configuration; this paper does not
claim multi-user access control or authentication is already installed.

See the [Charter](CHARTER.md) for the complete coordination model.
