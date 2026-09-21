<h1 align="center">
  <img src="docs/assets/embrella_logo.png" alt="" width="48" valign="middle">
  Embrella
</h1>

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Release](https://img.shields.io/github/v/release/chanzuckerberg/embrella)](https://github.com/chanzuckerberg/embrella/releases)
[![CI](https://github.com/chanzuckerberg/embrella/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/chanzuckerberg/embrella/actions/workflows/ci.yaml)
[![Docs](https://github.com/chanzuckerberg/embrella/actions/workflows/argus-docker-build-dispatch.yaml/badge.svg)](https://embrella.apps-staging.czbiohub.org/docs/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Next.js 16](https://img.shields.io/badge/next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)

</div>

Embrella is a web application that provides an integrated experience for tracking
cryo-electron tomography (cryo-ET) workflows — from sample preparation through data
processing to curation. It links metadata across every stage, giving scientists a
single place to manage and standardize how their data is tracked.

> [!NOTE]
> Embrella is under active development. Expect breaking changes between major releases.

Full documentation at [embrella.apps-staging.czbiohub.org/docs](https://embrella.apps-staging.czbiohub.org/docs/).

## Overview

Embrella is organized around three main stages of the cryo-ET workflow:

### 1. Sample Preparation

Grid logging lets users record how and where they
placed their prepared samples. This keeps track of where grids live in shared storage
and streamlines hand-off to downstream sample-prep steps or imaging sessions.

### 2. Data Processing

Grids are linked to imaging (TEM) sessions and, from there, to compute jobs. Using the
captured imaging metadata, Embrella pre-fills processing scripts and submits them as
SLURM jobs to HPC clusters (e.g. AreTomo3, denoising, membrane segmentation, copick).

### 3. Curation

Processed tomograms can be filtered and viewed through integrated plots and reviewed in an interactive viewer.

## Try It Out!

Come try our [Public Demo Server](https://embrella.apps-staging.czbiohub.org/).

## Contributing

See our [contributing documentation](https://embrella.apps-staging.czbiohub.org/docs/contributing/gettingstarted/).

The recommended setup uses [VS Code Dev Container](https://code.visualstudio.com/docs/devcontainers/containers).
It brings up the full stack (db, backend, worker, frontend, nginx) in Docker or Podman containers.

## Reporting Security Issues

If you believe you have found a security vulnerability, please report as instructed in our [Security](SECURITY.md) notes.
