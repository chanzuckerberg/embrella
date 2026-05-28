# Getting Started

The project supports two local-development paths. Pick whichever fits.

|              | Containerized (recommended)                                        | Bare-metal (legacy)          |
| ------------ | ------------------------------------------------------------------ | ---------------------------- |
| Prereqs      | `git`, `podman` (with `podman machine` started on macOS), `just`   | `git`, `conda`               |
| Setup time   | One-time image build (~5 min), then `just devup`                   | Conda env install + dep sync |
| Tests/manage | `just devexec pytest`, `just devexec python umbrella/manage.py …`  | `pytest`, `just manage …`    |
| Editor       | VS Code Dev Containers OR PyCharm Pro (Docker Compose interpreter) | Any editor on host           |
| Layout docs  | [infra/README.md](../../infra/README.md)                           | (rest of this page)          |

The `Justfile` contains short shell helpers for common tasks under both paths.
Run `just --list --unsorted` to see them.

See `just info` for a summary of your development environment.

## Path A: Containerized (recommended)

```bash
$ podman machine start            # macOS only
$ just netinit                    # one-time: create the embrella podman network
$ cp helpers/.env_template .env   # if you don't have a .env yet
$ just devup                      # build images, bring up the stack
```

On macOS, the default `podman machine` VM has only 4 GB of RAM, which is tight
once the full stack + devcontainer is running. See
[infra/README.md → "macOS: bumping the podman machine"](../../infra/README.md#macos-bumping-the-podman-machine)
for the recommended bump (8 GB / 4 CPUs / 100 GB).

Open `http://localhost:8080`. Logs: `just devlogs [service]`. Tear down with
`just devdown`. Full details: [infra/README.md](../../infra/README.md). Debugger
attach instructions: [../../.claude/plans/dockerize-embrella.md](../../.claude/plans/dockerize-embrella.md#debugger-support).

### Editing inside the devcontainer

The repo ships a single full-stack devcontainer at `.devcontainer/devcontainer.json`
that attaches to the `backend` service. It has Python + Node + `gh` + Claude Code
preinstalled and mounts the whole repo (with `.git/`) so both `pytest` and
`yarn test` run from one shell. In VS Code: "Dev Containers: Reopen in
Container" → "Embrella". On first launch, run `claude` to sign in
and `gh auth login` for git push. See
[infra/README.md → Devcontainer](../../infra/README.md#devcontainer) for the
full setup notes.

For quick one-off commands without opening VS Code:

```bash
$ just devshell            # interactive zsh in the backend container
$ just devexec pytest -k test_foo
```

## Path B: Bare-metal (legacy)

You'll need `bash` or `zsh`, plus `git` and `conda`.
The conda environment (`environment.yml`) installs python, nodejs, and the
`just` CLI.

## Initial Setup: Conda

Setup and activate initial conda environment with:

```bash
(base) $ conda env create -f environment.yml
(base) $ conda activate umbrella
(umbrella) $ just --version
just 1.39.0
```

Note: the conda environment installs its own version of nodejs. It installs `uv` for managing python and project dependencies.

To update the environment after modifying environment.yml you can use `just condasync`.

## Set up your env

Next you'll want to set up your [environment variables](./environments.md).

## Backend/frontend package installation

You'll need to have `mysql-client` installed (if you're using a mac, `brew install mysql-client`, and set up the LDFLAGS and CFLAGS so mysql.h is accessible for python to compile support for.)

The python and nodejs packages can be installed with these helpers. (Note, these check whether the contents of `requirements.txt` or `package.json` have changed, and only do the slow updates if so.)

```bash
(umbrella) $ just updatebackenddeps
(umbrella) $ just updatefrontenddeps
```

### Backend populating initial db

```bash
(umbrella) $ just manage migrate
(umbrella) $ just manage createsuperuser
# Optional: Populate some example data
(umbrella) $ just populatedbexamples
```

## Running

Then check out the guide to [running/deploying](./deployment.md) the server.
