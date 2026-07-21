# Repository guidelines

## Required reading

Before making changes, read:

1. `README.md` for project status, source-of-truth priority, and workflows.
2. `CONTRIBUTING.md` for Git, commits, review, and data-safety rules.
3. The nearest directory-level `README.md` for area-specific constraints.

## Project phase

This repository is currently validating product assumptions and technical feasibility.

- Do not initialize production applications or prematurely lock frameworks.
- Do not evolve `prototype/` into production code.
- Do not treat code under `spikes/` as production architecture.
- Move validated capabilities into `apps/` or `packages/` only through a separate implementation decision.

## Sources of truth

When requirements conflict, follow this order:

1. Latest PRD under `docs/product/`.
2. Current clickable prototype under `prototype/`.
3. Current prototype specification under `docs/design/`.
4. Completed technical-slice decisions.
5. Archived product and research documents.

Archived documents provide background and are not active requirements.

## Change synchronization

- Product or interaction changes must update the relevant PRD, prototype, and prototype specification together.
- Technical slices must test one falsifiable question and record fixtures, schemas, metrics, thresholds, failures, results, and a decision.
- Every completed slice must state its effect on the PRD, high-fidelity design, architecture, data, and privacy.
- Record what was verified and what remains unverified.

## Safety boundaries

- Never commit real child voice recordings, photos, identity data, credentials, or production logs.
- Use synthetic or de-identified fixtures by default.
- Do not present prototype behavior or technical demonstrations as evidence of accuracy, stability, learning efficacy, or production readiness.
- Preserve content sources, review status, and version traceability.

## Git and verification

Follow `CONTRIBUTING.md` for branch names, commit messages, and pull-request checks. Run the verification required by the affected directory and report any checks that could not be run.

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `junxxxxiao/primary-visual-learning`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout with root `CONTEXT.md` and system-wide ADRs under `docs/adr/`. See `docs/agents/domain.md`.
