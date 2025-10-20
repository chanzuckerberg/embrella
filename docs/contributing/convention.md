## Branches
`main` branch: deployed to production (umbrella.czbiohub.org)

`staging` branch: deployed to staging.

Branch feature development from main.

When ready to test on staging, rebase your branch using main so it's up to date and deploy to staging. (See [deployment](deployment.md).)

Create PRs into main, squash merge on approval to keep a linear readable history.


## CI/CD
Soon: Github actions using self-hosted github runners that perform the [deployment](deployment.md) upon tests passing.

## Release/Commit Convention
Soon: Use [release please](https://github.com/googleapis/release-please) system.
