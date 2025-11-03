# Getting Started
You'll need to have access to a bash or zsh shell, and to have `git`, `conda`.

The conda environment (see `environment.yml`) installs python, nodejs, and gives the CLI tool `just`.

The `Justfile` contains short shell script helpers for common tasks.

See `just --list --unsorted` to see a commented list of what's available in it.

See `just info` for a useful summary of the state of your development environment. 

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