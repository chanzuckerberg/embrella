# Embrella

Embrella is a web application that provides an integrated experience for tracking
cryo-electron tomography (cryo-ET) workflows — from sample preparation through data
processing to curation. It links metadata across every stage, giving scientists a
single place to manage and standardize how their data is tracked.

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

_Demo Server Coming Soon_

## Getting Started

The recommended setup uses the [VS Code Dev Container](https://code.visualstudio.com/docs/devcontainers/containers).
It brings up the full stack (db, backend, worker, frontend, nginx) in Docker or Podman containers.

<!-- ## Documentation -->

## Project Structure

```
umbrella/          Django backend
  cryo_grids/      Grid, dewar, cane, puck lifecycle tracking (sample prep)
  tem/             TEM / imaging session tracking
  workflow/        SLURM job execution engine and processors
  processes/       Processing workflows, tomogram review, metadata
  stores/          Data storage / path abstraction layer
  projects/        Project management
frontend/          Next.js frontend
docs/              MkDocs documentation source
infra/             Container / compose configuration
```
