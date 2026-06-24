# Limitations and Roadmap

## Limitations

- v0.1 is a controlled benchmark, not an industrial production router.
- The oracle is manually constructed and task-specific.
- The current public summary covers one full `deepseek-v4-pro` Stage3 run.
- Real external dataset adapters are scaffolded but not used in v0.1.
- The generated legacy-shop project is intentionally small and synthetic.
- `conflicting` evidence is still difficult for the model and should be strengthened in future versions.
- The workspace used for this cleanup contains an invalid `.git` directory, so git status could not be used as a verification signal.

## Roadmap

- Add multi-model comparison while keeping the same Stage3 protocol.
- Convert real issues, coding sessions, failed patches, and rollback records into claim/evidence inputs through adapters.
- Strengthen `conflicting` cases so the model must distinguish `verify_first` from `conflict_detected`.
- Add richer case-level reports for pollution, destructive changes, and over-conservative decisions.
- Build a lightweight web dashboard for browsing runs and evidence decisions.
- Create a smaller public artifact profile that commits benchmark definitions and summaries while keeping large raw model outputs out of Git history.
