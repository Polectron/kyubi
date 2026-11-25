# Contributing

## Pull request titles and releases

Use a Conventional Commit title for every pull request, for example:

- `fix: improve query performance`
- `feat(parser): support nested expressions`
- `feat(api)!: replace the query interface` for a breaking change

Release Please uses merged commit messages to decide when to open a release pull request and what version to select. Squash-merge pull requests and use the validated pull request title as the squash commit title. `feat` and `fix` changes drive minor and patch releases; breaking changes are marked with `!`.
