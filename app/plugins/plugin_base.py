from abc import ABC, abstractmethod
from typing import Any, Callable


class PluginBase(ABC):
    """Every Hamster AI plugin must subclass this."""

    name: str = "unnamed_plugin"
    description: str = ""
    enabled_by_default: bool = False
    dependencies: list[str] = []
    permissions_required: list[str] = []

    @abstractmethod
    def on_start(self, app: Any) -> None:
        """Called when the plugin is enabled. Receive AppContext as `app`."""

    @abstractmethod
    def on_stop(self, app: Any) -> None:
        """Called when the plugin is disabled or the app exits."""

    @abstractmethod
    def on_event(self, event: str, data: Any) -> None:
        """Called for each event the plugin has subscribed to."""

    @abstractmethod
    def get_commands(self) -> dict[str, Callable]:
        """Return {'/command': handler} for commands this plugin registers."""
