# Getting Started: Developers

The project supports two local-development paths. Pick whichever fits.

|             | Containerized (recommended)       | Bare-metal (legacy)          |
| ----------- | --------------------------------- | ---------------------------- |
| Prereqs     | `git`, `podman`, `just`(optional) | `git`, `conda`, `just`       |
| Setup time  | One-time images build (~10 min).  | Conda env install + dep sync |
| Editor      | VS Code Dev Containers            | Any editor on host           |
| Layout docs | [Container Layout](containers.md) | (rest of this page)          |

The `Justfile` contains short shell helpers for common tasks under both paths. [Package Installation.](https://just.systems/man/en/packages.html)
Run `just --list --unsorted` to see them.

See `just info` for a summary of your development environment.

# Path A: Containerized (recommended)

Podman size defaults on Mac are too limited. On Linux, skip this block.

```bash
$ podman machine init --memory 16384 --cpus 8 --disk-size 50   # first time
$ podman machine start
# Already have a machine? Restart with new options:
#   podman machine stop && podman machine set --memory 16384 --cpus 8 --disk-size 50 && podman machine start
```

One-time setup:

```bash
$ cp helpers/.env_template .env   # if you don't have a .env yet
# make edits to the .env file. Contact local admin for secrets needed.
```

Then bring up the stack either way:

- **VS Code Dev Containers (recommended):** Install extension for Dev Containers. Then, "Dev Containers: Reopen in Container"
  → "Embrella". This brings up the whole compose stack and drops you into a preconfigured dev environment.
- **CLI alternative:** `just devup` builds the images and starts the stack in the
  background.

Open `http://localhost:8080` to view site locally.

See
[Container Layout → Devcontainer](containers.md#devcontainer) for the
full setup notes.

# Path B: Bare-metal (legacy)

You'll need `git` and `conda` installed.
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

# Running

Then check out the guide to [running/deploying](./deployment.md) the server.
