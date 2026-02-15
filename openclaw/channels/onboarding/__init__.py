"""Channel onboarding adapters (aligned with TypeScript onboarding/)"""

from .types import ChannelOnboardingAdapter, ChannelOnboardingStatus, ChannelOnboardingDmPolicy
from .telegram import TelegramOnboardingAdapter
from .discord import DiscordOnboardingAdapter
from .slack import SlackOnboardingAdapter

__all__ = [
    "ChannelOnboardingAdapter",
    "ChannelOnboardingStatus",
    "ChannelOnboardingDmPolicy",
    "TelegramOnboardingAdapter",
    "DiscordOnboardingAdapter",
    "SlackOnboardingAdapter",
]
