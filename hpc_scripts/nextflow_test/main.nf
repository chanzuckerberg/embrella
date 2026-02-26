#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
 * Embrella workflow: AreTomo3 on CZII, then Copick on Bruno.
 *
 * Usage:
 *   nextflow run main.nf \
 *     --aretomo3_script /path/to/aretomo3_job.sh \
 *     --copick_script /path/to/copick_job.sh
 */

process ARETOMO3 {
    executor 'local'

    output:
    val true, emit: done

    script:
    """
    echo "=== Submitting AreTomo3 to CZII ==="
    ssh ${params.ssh_user}@${params.czii_host} 'sbatch --wait ${params.aretomo3_script}'
    echo "=== AreTomo3 completed ==="
    """
}

process WAIT_BETWEEN {
    executor 'local'

    input:
    val ready

    output:
    val true, emit: done

    script:
    """
    echo "=== Waiting ${params.wait_minutes} minutes before Copick ==="
    sleep ${params.wait_minutes}m
    echo "=== Wait complete ==="
    """
}

process COPICK_CREATE_PROJECT {
    executor 'local'

    input:
    val ready

    output:
    val true, emit: done

    script:
    """
    echo "=== Submitting Copick Create Project to Bruno ==="
    ssh ${params.ssh_user}@${params.bruno_host} 'sbatch --wait ${params.copick_script}'
    echo "=== Copick Create Project completed ==="
    """
}

workflow {
    ARETOMO3()
    WAIT_BETWEEN(ARETOMO3.out.done)
    COPICK_CREATE_PROJECT(WAIT_BETWEEN.out.done)
}
