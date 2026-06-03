from abc import ABC, abstractmethod


class Messenger(ABC):
    """A channel that can deliver an outbound message to a recipient.

    Recipients are identified by an opaque string (`to`): a phone number for SMS,
    a chat id for Telegram, etc. The rest of the bot stays channel-agnostic.
    """

    name: str = "messenger"

    @abstractmethod
    def send(self, to: str, text: str) -> None:
        """Deliver `text` to recipient `to`. Implementations log success/failure."""
        ...
