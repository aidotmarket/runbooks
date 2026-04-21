# Missing H5 Config Default

## §H. Evolve

### §H.1 Invariants

- Secret reads must always resolve against an explicitly named environment.

### §H.2 BREAKING predicates

- Any change that alters secret path resolution semantics across environments is BREAKING.

### §H.3 REVIEW predicates

- Any change that adds a new integration target for secret sync requires REVIEW.

### §H.4 SAFE predicates

- Documentation-only changes with no behavior changes are SAFE.

### §H.5 Boundary definitions

#### module

The module boundary is one deployable Infisical integration unit such as the CLI or sync worker.

#### public contract

The public contract is the supported command surface, required arguments, output shape, and environment semantics exposed to operators or automation.

#### runtime dependency

A runtime dependency is any external API, credential source, service endpoint, or execution substrate required for the runbook flow to succeed.

### §H.6 Adjudication

When a proposed change touches more than one boundary class, classify it at the highest-risk class and document the reasoning in the change review.
