from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, NamedTuple, Union, overload

from pydantic import BaseModel, Field

from .._subprocess import ExecResult

TaskInit = Callable[[str, Union["SandboxEnvironmentConfigType", None]], Awaitable[None]]
TaskCleanup = Callable[
    [str, Union["SandboxEnvironmentConfigType", None], bool], Awaitable[None]
]

SampleInit = Callable[
    [str, Union["SandboxEnvironmentConfigType", None], dict[str, str]],
    Awaitable[dict[str, "SandboxEnvironment"]],
]
SampleCleanup = Callable[
    [
        str,
        Union["SandboxEnvironmentConfigType", None],
        dict[str, "SandboxEnvironment"],
        bool,
    ],
    Awaitable[None],
]


class HostMapping(BaseModel):
    host_ip: str
    host_port: int


class PortMapping(BaseModel):
    container_port: int
    protocol: Literal["tcp", "udp"]
    mappings: list[HostMapping]


class SandboxConnection(BaseModel):
    """Information required to connect to sandbox."""

    type: str
    """Sandbox type name (e.g. 'docker', 'local', etc.)"""

    command: str
    """Shell command to connect to sandbox."""

    vscode_command: list[Any] | None = Field(default=None)
    """Optional vscode command (+args) to connect to sandbox."""

    ports: list[PortMapping] | None = Field(default=None)
    """Optional list of port mappings into container"""

    container: str | None = Field(default=None)
    """Optional container name (does not apply to all sandboxes)."""


class SandboxEnvironment(abc.ABC):
    """Environment for executing arbitrary code from tools.

    Sandbox environments provide both an execution environment as well as a per-sample
    filesystem context to copy samples files into and resolve relative paths to.
    """

    @abc.abstractmethod
    async def exec(
        self,
        cmd: list[str],
        input: str | bytes | None = None,
        cwd: str | None = None,
        env: dict[str, str] = {},
        user: str | None = None,
        timeout: int | None = None,
        timeout_retry: bool = True,
    ) -> ExecResult[str]:
        """Execute a command within a sandbox environment.

        The current working directory for execution will be the per-sample
        filesystem context.

        Each output stream (stdout and stderr) is limited to 10 MiB. If exceeded, an
        `OutputLimitExceededError` will be raised.

        Args:
          cmd: Command or command and arguments to execute.
          input: Standard input (optional).
          cwd: Current working dir (optional). If relative, will be relative to the per-sample filesystem context.
          env: Environment variables for execution.
          user: Optional username or UID to run the command as.
          timeout: Optional execution timeout (seconds).
          timeout_retry: Retry the command in the case that it times out.
            Commands will be retried up to twice, with a timeout of no greater
            than 60 seconds for the first retry and 30 for the second.


        Returns:
          Execution result (status code, stderr/stdout, etc.)

        Raises:
          TimeoutError: If the specified `timeout` expires
            (and `timeout_retry` attempts also timeout).
          UnicodeDecodeError: If an error occurs while
            decoding the command output.
          PermissionError: If the user does not have
            permission to execute the command.
          OutputLimitExceededError: If an output stream
            exceeds the 10 MiB limit.
        """
        ...

    @abc.abstractmethod
    async def write_file(self, file: str, contents: str | bytes) -> None:
        """Write a file into the sandbox environment.

        If the parent directories of the file path do not exist they
        should be automatically created.

        Args:
          file: Path to file (relative file paths will resolve to the
            per-sample working directory).
          contents: Text or binary file contents.

        Raises:
          PermissionError: If the current user does not have permission to
            write to the specified path.
          IsADirectoryError: If the file exists already and
            is a directory.
        """
        ...

    @overload
    async def read_file(self, file: str, text: Literal[True] = True) -> str: ...

    @overload
    async def read_file(self, file: str, text: Literal[False]) -> bytes: ...

    @abc.abstractmethod
    async def read_file(self, file: str, text: bool = True) -> Union[str | bytes]:
        """Read a file from the sandbox environment.

        File size is limited to 100 MiB.

        When reading text files, implementations should preserve newline constructs
        (e.g. crlf should be preserved not converted to lf). This is equivalent
        to specifying `newline=""` in a call to the Python `open()` function.

        Args:
          file: Path to file (relative file paths will resolve to the
            per-sample working directory).
          text: Read as a utf-8 encoded text file.

        Returns:
          Contents of file (as str or bytes for binary files)

        Raises:
          FileNotFoundError: If the file does not exist.
          UnicodeDecodeError: If an encoding error occurs
            while reading the file.
            (only applicable when `text = True`)
          PermissionError: If the user does not have
            permission to read from the specified path.
          IsADirectoryError: If the file is a directory.
          OutputLimitExceededError: If the file size
            exceeds the 100 MiB limit.
        """
        ...

    async def connection(self) -> SandboxConnection:
        """Information required to connect to sandbox environment.

        Returns:
           SandboxConnection: connection information

        Raises:
           NotImplementedError: For sandboxes that don't provide connections
           ConnectionError: If sandbox is not currently running.
        """
        raise NotImplementedError("connection not implemented")

    @classmethod
    def config_files(cls) -> list[str]:
        """Standard config files for this provider (used for automatic discovery)"""
        return []

    @classmethod
    def default_concurrency(cls) -> int | None:
        """Default max_sandboxes for this provider (`None` means no maximum)"""
        return None

    @classmethod
    async def task_init(
        cls, task_name: str, config: SandboxEnvironmentConfigType | None
    ) -> None:
        """Called at task startup initialize resources.

        Args:
          task_name: Name of task using the sandbox environment.
          config: Implementation defined configuration (optional).
        """
        pass

    @classmethod
    async def sample_init(
        cls,
        task_name: str,
        config: SandboxEnvironmentConfigType | None,
        metadata: dict[str, str],
    ) -> dict[str, "SandboxEnvironment"]:
        """Initialize sandbox environments for a sample.

        Args:
          task_name: Name of task using the sandbox environment.
          config: Implementation defined configuration (optional).
          metadata: Sample `metadata` field

        Returns:
          Dictionary of named sandbox environments. The environment which represents
          the default environment (resolved by `sandbox("default")` or `sandbox()`) must
          be the first key/value pair in the dictionary.
        """
        return {}

    @classmethod
    @abc.abstractmethod
    async def sample_cleanup(
        cls,
        task_name: str,
        config: SandboxEnvironmentConfigType | None,
        environments: dict[str, "SandboxEnvironment"],
        interrupted: bool,
    ) -> None:
        """Cleanup sandbox environments.

        Args:
          task_name: Name of task using the sandbox environment.
          config: Implementation defined configuration (optional).
          environments: Sandbox environments created for this sample.
          interrupted: Was the task interrupted by an error or cancellation
        """
        ...

    @classmethod
    async def task_cleanup(
        cls, task_name: str, config: SandboxEnvironmentConfigType | None, cleanup: bool
    ) -> None:
        """Called at task exit as a last chance to cleanup resources.

        Args:
          task_name: Name of task using the sandbox environment.
          config: Implementation defined configuration (optional).
          cleanup: Whether to actually cleanup environment resources
            (False if `--no-sandbox-cleanup` was specified)
        """
        pass

    @classmethod
    async def cli_cleanup(cls, id: str | None) -> None:
        """Handle a cleanup invoked from the CLI (e.g. inspect sandbox cleanup).

        Args:
          id: Optional ID to limit scope of cleanup.
        """
        pass


@dataclass
class SandboxEnvironments:
    """Collection of sandbox environments used for an evaluation."""

    environments: dict[str, SandboxEnvironment]
    """Sandbox environments by name."""

    cleanup: Callable[[bool], Awaitable[None]] | None = field(default=None)
    """Optional global cleanup function.

    Called with a boolean indicating whether the sample was cancelled.
    """


class SandboxEnvironmentSpec(NamedTuple):
    """Specification of a SandboxEnvironment."""

    type: str
    """Sandbox type (e.g. 'local', 'docker')"""

    config: SandboxEnvironmentConfigType | None = None
    """Sandbox configuration (filename or config object)."""


SandboxEnvironmentConfigType = BaseModel | str

SandboxEnvironmentType = SandboxEnvironmentSpec | str | tuple[str, str]
"""SandboxEnvironmentSpec and str and tuple shorthands for it.

A plain str, e.g. "docker", is equivalent to SandboxEnvironmentSpec("docker")
A tuple, e.g. ("docker", "compose.yaml"), is equivalent to SandboxEnvironmentSpec("docker", "compose.yaml")
"""


def resolve_sandbox_environment(
    sandbox: SandboxEnvironmentType | None,
) -> SandboxEnvironmentSpec | None:
    # do the resolution
    if isinstance(sandbox, str):
        return SandboxEnvironmentSpec(type=sandbox)
    elif isinstance(sandbox, SandboxEnvironmentSpec):
        return sandbox
    elif isinstance(sandbox, tuple):
        return SandboxEnvironmentSpec(sandbox[0], sandbox[1])
    else:
        return None
