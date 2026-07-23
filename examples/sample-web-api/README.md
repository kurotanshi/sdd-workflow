# Sample Web API: complete SDD walkthrough

This self-contained example replays the protocol path a user is most likely to
need when approved requirements change during implementation.

The sample starts with a tiny dependency-free API and a draft proposal for
`/health`. The executable walkthrough:

1. records the initial proposal and source in Git;
2. validates and explicitly approves the proposal;
3. implements and completes the first canonical task;
4. simulates an out-of-band edit that adds a version requirement;
5. proves `status` fails closed with `ERROR_APPROVED_PLAN_CHANGED`;
6. begins a managed revision while retaining the completed task;
7. validates and explicitly reapproves the revised scope;
8. implements and completes the remaining tasks;
9. runs the acceptance tests;
10. archives the completed proposal;
11. deletes the derived archive `INDEX.md`; and
12. rebuilds and validates INDEX, then runs `doctor`.

Every material step is committed in a temporary Git repository, so the output
includes a reproducible commit history without nesting a repository inside
this example.

Run it:

```text
python3 examples/sample-web-api/run-walkthrough.py
```

The script copies `project/` to a temporary directory. It never mutates this
checked-in template and does not invoke an Agent.
