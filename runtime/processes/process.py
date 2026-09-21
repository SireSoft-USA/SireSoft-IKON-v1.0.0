import os
import subprocess
import time


class ProcessResult:
    def __init__(
        self,
        exit_code,
        stdout,
        stderr,
        runtime_seconds,
        termination,
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.runtime_seconds = (
            runtime_seconds
        )
        self.termination = (
            termination
        )

    def to_dict(
        self,
    ):
        return {
            "exit_code": (
                self.exit_code
            ),
            "stdout": (
                self.stdout
            ),
            "stderr": (
                self.stderr
            ),
            "runtime_seconds": (
                self.runtime_seconds
            ),
            "termination": (
                self.termination
            ),
        }


class ManagedProcess:
    """
    One child process with explicit lifecycle and captured output.
    """

    def __init__(
        self,
        spec,
    ):
        if not isinstance(
            spec,
            ProcessSpec,
        ):
            raise TypeError(
                "spec must be ProcessSpec"
            )

        self.spec = spec
        self._process = None
        self._state = "new"
        self._started_monotonic = None
        self._finished_monotonic = None
        self._result = None
        self._termination = (
            "natural"
        )

    def start(
        self,
    ):
        if self._process is not None:
            raise RuntimeError(
                "process instance already started"
            )

        environment = dict(
            os.environ
        )

        for key in self.spec.env:
            environment[
                key
            ] = self.spec.env[
                key
            ]

        self._process = (
            subprocess.Popen(
                self.spec.command,
                cwd=self.spec.cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )

        self._started_monotonic = (
            time.monotonic()
        )
        self._state = "running"

        return self

    def pid(
        self,
    ):
        if self._process is None:
            return None

        return self._process.pid

    def poll(
        self,
    ):
        if self._process is None:
            return None

        code = self._process.poll()

        if (
            code is not None
            and self._state
            == "running"
        ):
            self._state = "exited"

        return code

    def running(
        self,
    ):
        return (
            self._process
            is not None
            and self.poll()
            is None
        )

    def wait(
        self,
        timeout=None,
    ):
        self._require_started()

        if self._result is not None:
            return self._result

        try:
            stdout, stderr = (
                self._process
                .communicate(
                    timeout=timeout
                )
            )

        except subprocess.TimeoutExpired:
            raise TimeoutError(
                "process wait timed out"
            )

        self._finish(
            stdout,
            stderr,
        )

        return self._result

    def terminate(
        self,
        timeout=None,
    ):
        self._require_started()

        if self._result is not None:
            return self._result

        if timeout is None:
            timeout = (
                self.spec
                .graceful_timeout_seconds
            )

        if not self.running():
            return self.wait()

        self._termination = (
            "terminated"
        )

        self._process.terminate()

        try:
            return self.wait(
                timeout=timeout
            )

        except TimeoutError:
            self._termination = (
                "killed_after_timeout"
            )

            self._process.kill()

            return self.wait()

    def kill(
        self,
    ):
        self._require_started()

        if self._result is not None:
            return self._result

        if self.running():
            self._termination = (
                "killed"
            )
            self._process.kill()

        return self.wait()

    def result(
        self,
    ):
        return self._result

    def state(
        self,
    ):
        if (
            self._process is not None
            and self._result is None
        ):
            self.poll()

        return self._state

    def status(
        self,
    ):
        return {
            "name": self.spec.name,
            "pid": self.pid(),
            "state": self.state(),
            "running": self.running()
            if self._process
            is not None
            else False,
            "exit_code": (
                None
                if self._result
                is None
                else self._result
                .exit_code
            ),
            "termination": (
                None
                if self._result
                is None
                else self._result
                .termination
            ),
        }

    def _finish(
        self,
        stdout,
        stderr,
    ):
        self._finished_monotonic = (
            time.monotonic()
        )

        runtime = (
            self._finished_monotonic
            - self._started_monotonic
        )

        self._result = (
            ProcessResult(
                exit_code=(
                    self._process
                    .returncode
                ),
                stdout=self._decode(
                    stdout
                ),
                stderr=self._decode(
                    stderr
                ),
                runtime_seconds=(
                    runtime
                ),
                termination=(
                    self._termination
                ),
            )
        )

        self._state = "exited"

    def _decode(
        self,
        value,
    ):
        if value is None:
            return ""

        return value.decode(
            "utf-8",
            errors="replace",
        )

    def _require_started(
        self,
    ):
        if self._process is None:
            raise RuntimeError(
                "process has not been started"
            )
