import time
from typing import cast

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalGroup, Vertical, VerticalGroup
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    Collapsible,
    Link,
    LoadingIndicator,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option, Separator

from inspect_ai._display.textual.widgets.port_mappings import get_url
from inspect_ai._util.format import format_progress_time
from inspect_ai._util.port_names import get_service_by_port
from inspect_ai._util.registry import registry_unqualified_name
from inspect_ai.log._samples import ActiveSample
from inspect_ai.log._transcript import ToolEvent

from .clock import Clock
from .sandbox import SandboxView
from .transcript import TranscriptView


class SamplesView(Widget):
    DEFAULT_CSS = """
    SamplesView {
        width: 1fr;
        height: 1fr;
        padding: 0 1 0 1;
        layout: grid;
        grid-size: 2 3;
        grid-rows: auto 1fr auto;
        grid-columns: 32 1fr;
        grid-gutter: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.samples: list[ActiveSample] = []
        self.last_updated = time.perf_counter()

    def compose(self) -> ComposeResult:
        yield SamplesList()
        yield SampleInfo()
        yield TranscriptView()
        yield SampleToolbar()

    def on_mount(self) -> None:
        self.watch(
            self.query_one(SamplesList), "highlighted", self.set_highlighted_sample
        )

    async def notify_active(self, active: bool) -> None:
        await self.query_one(TranscriptView).notify_active(active)

    def set_samples(self, samples: list[ActiveSample]) -> None:
        # throttle to no more than 1 second per 100 samples
        throttle = round(max(len(samples) / 100, 1))
        current = time.perf_counter()
        if (current - self.last_updated) > throttle:
            self.query_one(SamplesList).set_samples(samples)
            self.last_updated = current

    async def set_highlighted_sample(self, highlighted: int | None) -> None:
        sample_info = self.query_one(SampleInfo)
        sample_vnc = self.query_one(SampleVNC)
        transcript_view = self.query_one(TranscriptView)
        sample_toolbar = self.query_one(SampleToolbar)
        if highlighted is not None:
            sample = self.query_one(SamplesList).sample_for_highlighted(highlighted)
            if sample is not None:
                sample_info.display = True
                transcript_view.display = True
                sample_toolbar.display = True
                await sample_info.sync_sample(sample)
                await sample_vnc.sync_sample(sample)
                await transcript_view.sync_sample(sample)
                await sample_toolbar.sync_sample(sample)
                return

        # otherwise hide ui
        sample_info.display = False
        sample_vnc.display = False
        transcript_view.display = False
        sample_toolbar.display = False


class SamplesList(OptionList):
    DEFAULT_CSS = """
    SamplesList {
        height: 100%;
        scrollbar-size-vertical: 1;
        margin-bottom: 1;
        row-span: 3;
        background: transparent;
    }
    SamplesList:focus > .option-list--option-highlighted {
        background: $primary 40%;
    }

    SamplesList  > .option-list--option-highlighted {
        background: $primary 40%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.samples: list[ActiveSample] = []

    def set_samples(self, samples: list[ActiveSample]) -> None:
        # check for a highlighted sample (make sure we don't remove it)
        highlighted_id = (
            self.get_option_at_index(self.highlighted).id
            if self.highlighted is not None
            else None
        )
        highlighted_sample = (
            sample_for_id(self.samples, highlighted_id)
            if highlighted_id is not None
            else None
        )

        # assign the new samples
        self.samples = samples.copy()

        # add the highlighted sample if its no longer in the list
        if highlighted_sample and (highlighted_sample not in self.samples):
            self.samples.append(highlighted_sample)

        # sort the samples by execution time
        self.samples.sort(key=lambda sample: sample.execution_time, reverse=True)

        # rebuild the list
        self.clear_options()
        options: list[Option | Separator] = []
        for sample in self.samples:
            table = Table.grid(expand=True)
            table.add_column(width=20)
            table.add_column(width=11, justify="right")
            table.add_column(width=1)
            task_name = Text.from_markup(f"{registry_unqualified_name(sample.task)}")
            task_name.truncate(18, overflow="ellipsis", pad=True)
            task_time = Text.from_markup(
                f"{format_progress_time(sample.execution_time)}"
            )
            table.add_row(task_name, task_time, " ")
            sample_id = Text.from_markup(f"id: {sample.sample.id}")
            sample_id.truncate(18, overflow="ellipsis", pad=True)
            sample_epoch = Text.from_markup(f"epoch: {sample.epoch:.0f}")
            table.add_row(
                sample_id,
                sample_epoch,
                " ",
            )
            table.add_row("", "", "")
            options.append(Option(table, id=sample.id))

        self.add_options(options)

        # select sample (re-select the highlighted sample if there is one)
        if len(self.samples) > 0:
            if highlighted_id is not None:
                index = sample_index_for_id(self.samples, highlighted_id)
            else:
                index = 0
            self.highlighted = index
            self.scroll_to_highlight()

    def sample_for_highlighted(self, highlighted: int) -> ActiveSample | None:
        highlighted_id = self.get_option_at_index(highlighted).id
        if highlighted_id is not None:
            return sample_for_id(self.samples, highlighted_id)
        else:
            return None


class SampleVNC(Horizontal):
    DEFAULT_CSS = """
    SampleVNC {
        layout: grid;
        grid-size: 2 1;
        grid-columns: auto 1fr;
    }
    SampleVNC Static {
        color: $secondary;
    }
    SampleVNC Link {
        color: $accent;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._sample: ActiveSample | None = None

    def compose(self) -> ComposeResult:
        yield Static("VNC: ")
        yield Link("")

    async def sync_sample(self, sample: ActiveSample) -> None:
        if sample == self._sample:
            return

        # defult to hidden (show if we find a vnc connection)
        self.display = False

        # is there a vnc connection? if so populate
        for connection in [c for c in sample.sandboxes.values() if c.ports]:
            for port in connection.ports or []:
                service = get_service_by_port(port.container_port, port.protocol)
                if service == "noVNC" and port.mappings:
                    host_mappings = port.mappings
                    link = self.query_one(Link)
                    vnc_url = get_url(host_mappings[0].host_port, service)
                    if vnc_url:
                        link.text = vnc_url
                        link.url = link.text
                        self.display = True
                        break


class SampleInfo(Vertical):
    DEFAULT_CSS = """
    SampleInfo {
        color: $text-muted;
        layout: grid;
        grid-size: 1 2;
        grid-rows: auto 1;
        grid-gutter: 1;
    }
    SampleInfo Collapsible {
        padding: 0;
        border-top: none;
    }
    SampleInfo Collapsible CollapsibleTitle {
        padding: 0;
        color: $secondary;
        &:hover {
            background: $block-hover-background;
            color: $primary;
        }
        &:focus {
            background: $block-hover-background;
            color: $primary;
        }
    }
    SampleInfo Collapsible Contents {
        padding: 1 0 1 2;
        height: auto;
        overflow-x: auto;
    }
    SampleInfo Static {
        width: 1fr;
        background: $surface;
        color: $secondary;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._sample: ActiveSample | None = None
        self._sandbox_count: int | None = None

    def compose(self) -> ComposeResult:
        with Collapsible(title=""):
            yield SampleLimits()
            yield SandboxesView()
        yield SampleVNC()

    async def sync_sample(self, sample: ActiveSample | None) -> None:
        if sample is None:
            self.display = False
            self._sample = None
        else:
            # update sample limits
            limits = self.query_one(SampleLimits)
            await limits.sync_sample(sample)

            new_sandbox_count = len(sample.sandboxes)
            # bail if we've already processed this sample
            if self._sample == sample and self._sandbox_count == new_sandbox_count:
                return

            # set sample
            self._sample = sample
            self._sandbox_count = new_sandbox_count

            # update UI
            self.display = True
            title = f"{registry_unqualified_name(sample.task)} (id: {sample.sample.id}, epoch {sample.epoch}): {sample.model}"
            self.query_one(Collapsible).title = title
            sandboxes = self.query_one(SandboxesView)
            await sandboxes.sync_sample(sample)
            await self.query_one(SampleVNC).sync_sample(sample)


class SampleLimits(Widget):
    DEFAULT_CSS = """
    SampleLimits {
        padding: 0 0 0 0;
        color: $secondary;
        background: transparent;
        height: auto;
    }
    SampleLimits Static {
        background: transparent;
        color: $secondary;
    }
    """

    messages = reactive(0)
    message_limit = reactive(0)
    tokens = reactive(0)
    token_limit = reactive(0)
    started = reactive(0)
    time_limit = reactive(0)

    def __init__(self) -> None:
        super().__init__()

    def render(self) -> RenderableType:
        limits = f"[bold]messages[/bold]: {self.messages}"
        if self.message_limit:
            limits = f"{limits} (limit {self.message_limit})"
        limits = f"{limits}, [bold]tokens[/bold]: {self.tokens:,}"
        if self.token_limit:
            limits = f"{limits} ({self.token_limit:,})"
        return limits

    async def sync_sample(self, sample: ActiveSample) -> None:
        self.messages = sample.total_messages
        self.message_limit = sample.message_limit or 0
        self.tokens = sample.total_tokens
        self.token_limit = sample.token_limit or 0


class SandboxesView(Vertical):
    DEFAULT_CSS = """
    SandboxesView {
        padding: 1 0 0 0;
        background: transparent;
        height: auto;
    }
    #sandboxes-list {
        height: auto;
    }
    SandboxesView Static {
        background: transparent;
    }
    .clipboard-message {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static(id="sandboxes-caption", markup=True)
        yield Vertical(id="sandboxes-list")

    async def sync_sample(self, sample: ActiveSample) -> None:
        if len(sample.sandboxes) > 0:
            multiple_sandboxes = len(sample.sandboxes) > 1
            sandboxes_caption = cast(Static, self.query_one("#sandboxes-caption"))
            sandboxes_caption.update(
                f"[bold]sandbox container{'s' if multiple_sandboxes else ''}:[/bold]"
            )

            sandboxes_list = self.query_one("#sandboxes-list")
            await sandboxes_list.remove_children()

            await sandboxes_list.mount_all(
                [
                    SandboxView(connection, name if multiple_sandboxes else None)
                    for name, connection in sample.sandboxes.items()
                ]
            )

            await sandboxes_list.mount(
                Static(
                    "[italic]Hold down Alt (or Option) to select text for copying[/italic]",
                    classes="clipboard-message",
                    markup=True,
                )
            )
            self.display = True
        else:
            self.display = False


class SampleToolbar(Horizontal):
    STATUS_GROUP = "status_group"
    TIMEOUT_TOOL_CALL = "timeout_tool_call"
    CANCEL_SCORE_OUTPUT = "cancel_score_output"
    CANCEL_RAISE_ERROR = "cancel_raise_error"
    PENDING_STATUS = "pending_status"
    PENDING_CAPTION = "pending_caption"

    DEFAULT_CSS = f"""
    SampleToolbar {{
        grid-size: 5 1;
        grid-columns: auto auto 1fr auto auto;
    }}
    SampleToolbar #{STATUS_GROUP} {{
        width: 22;
    }}
    SampleToolbar Button {{
        margin-bottom: 1;
        margin-right: 2;
        min-width: 18;
    }}
    SampleToolbar #{TIMEOUT_TOOL_CALL} {{
        color: $secondary-darken-3;
        min-width: 16;
    }}
    SampleToolbar #{CANCEL_SCORE_OUTPUT} {{
        color: $primary-darken-3;
    }}
    SampleToolbar #{CANCEL_RAISE_ERROR} {{
        color: $warning-darken-3;
    }}
    """

    def __init__(self) -> None:
        super().__init__()
        self.sample: ActiveSample | None = None

    def compose(self) -> ComposeResult:
        with HorizontalGroup(id=self.STATUS_GROUP):
            with VerticalGroup(id=self.PENDING_STATUS):
                yield Static("Executing...", id=self.PENDING_CAPTION)
                yield HorizontalGroup(EventLoadingIndicator(), Clock())
        yield Button(
            Text("Timeout Tool"),
            id=self.TIMEOUT_TOOL_CALL,
            tooltip="Cancel the tool call and report a timeout to the model.",
        )
        yield Horizontal()
        yield Button(
            Text("Cancel (Score)"),
            id=self.CANCEL_SCORE_OUTPUT,
            tooltip="Cancel the sample and score whatever output has been generated so far.",
        )
        yield Button(
            Text("Cancel (Error)"),
            id=self.CANCEL_RAISE_ERROR,
            tooltip="Cancel the sample and raise an error (task will exit unless fail_on_error is set)",
        )

    def on_mount(self) -> None:
        self.query_one("#" + self.PENDING_STATUS).visible = False
        self.query_one("#" + self.TIMEOUT_TOOL_CALL).display = False
        self.query_one("#" + self.CANCEL_SCORE_OUTPUT).display = False
        self.query_one("#" + self.CANCEL_RAISE_ERROR).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.sample:
            if event.button.id == self.TIMEOUT_TOOL_CALL:
                last_event = (
                    self.sample.transcript.events[-1]
                    if self.sample.transcript.events
                    else None
                )
                if isinstance(last_event, ToolEvent):
                    last_event._cancel()
            elif event.button.id == self.CANCEL_SCORE_OUTPUT:
                self.sample.interrupt("score")
            elif event.button.id == self.CANCEL_RAISE_ERROR:
                self.sample.interrupt("error")

    async def sync_sample(self, sample: ActiveSample | None) -> None:
        from inspect_ai.log._transcript import ModelEvent

        # track the sample
        self.sample = sample

        pending_status = self.query_one("#" + self.PENDING_STATUS)
        timeout_tool = self.query_one("#" + self.TIMEOUT_TOOL_CALL)
        clock = self.query_one(Clock)
        cancel_score_output = cast(
            Button, self.query_one("#" + self.CANCEL_SCORE_OUTPUT)
        )
        cancel_with_error = cast(Button, self.query_one("#" + self.CANCEL_RAISE_ERROR))
        if sample and not sample.completed:
            # update visibility and button status
            self.display = True
            cancel_score_output.display = True
            cancel_with_error.display = not sample.fails_on_error

            # if we have a pending event then start the clock and show pending status
            last_event = (
                sample.transcript.events[-1]
                if len(sample.transcript.events) > 0
                else None
            )
            if last_event and last_event.pending:
                pending_status.visible = True
                pending_caption = cast(
                    Static, self.query_one("#" + self.PENDING_CAPTION)
                )
                pending_caption_text = (
                    "Generating..."
                    if isinstance(last_event, ModelEvent)
                    else "Executing..."
                )
                pending_caption.update(
                    Text.from_markup(f"[italic]{pending_caption_text}[/italic]")
                )

                timeout_tool.display = isinstance(last_event, ToolEvent)

                clock.start(last_event.timestamp.timestamp())
            else:
                pending_status.visible = False
                timeout_tool.display = False
                clock.stop()

        else:
            self.display = False
            pending_status.visible = False
            timeout_tool.display = False
            clock.stop()


class EventLoadingIndicator(LoadingIndicator):
    DEFAULT_CSS = """
    EventLoadingIndicator {
        width: auto;
        height: 1;
        color: $primary;
        text-style: not reverse;
        margin-right: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()


def sample_for_id(samples: list[ActiveSample], id: str) -> ActiveSample | None:
    index = sample_index_for_id(samples, id)
    if index != -1:
        return samples[index]
    else:
        return None


def sample_index_for_id(samples: list[ActiveSample], id: str) -> int:
    for i, sample in enumerate(samples):
        if sample.id == id:
            return i
    return -1
