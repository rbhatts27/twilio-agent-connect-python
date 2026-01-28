"""Anchor scenario modules for the unified All My Sons demo."""

from anchors.base import BaseAnchor
from anchors.anchor1 import Anchor1ConcurrentChannels
from anchors.anchor2 import Anchor2ContextPreservation
from anchors.anchor3 import Anchor3ChannelSwitching
from anchors.anchor4 import Anchor4HumanTransfer
from anchors.anchor5 import Anchor5ProactiveOutreach
from anchors.anchor6 import Anchor6MultiParty

ANCHOR_REGISTRY: dict[str, type] = {
    "anchor1": Anchor1ConcurrentChannels,
    "anchor2": Anchor2ContextPreservation,
    "anchor3": Anchor3ChannelSwitching,
    "anchor4": Anchor4HumanTransfer,
    "anchor5": Anchor5ProactiveOutreach,
    "anchor6": Anchor6MultiParty,
}

__all__ = [
    "BaseAnchor",
    "ANCHOR_REGISTRY",
    "Anchor1ConcurrentChannels",
    "Anchor2ContextPreservation",
    "Anchor3ChannelSwitching",
    "Anchor4HumanTransfer",
    "Anchor5ProactiveOutreach",
    "Anchor6MultiParty",
]
