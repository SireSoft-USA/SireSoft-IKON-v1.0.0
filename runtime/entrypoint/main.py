def run_runtime(
    spec,
    wait_timeout=None,
):
    """
    Programmatic process-entry function.

    Returns RuntimeExitStatus instead of calling sys.exit(), keeping process
    termination policy in the executable wrapper rather than the runtime core.
    """

    entrypoint = (
        RuntimeEntrypointFactory()
        .create(
            spec
        )
    )

    return entrypoint.run(
        wait_timeout=wait_timeout
    )
