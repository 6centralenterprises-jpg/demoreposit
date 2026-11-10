"""Shared ElevenLabs connection for every 6 Central Enterprises portfolio project.

Any project that needs voice (voiceovers for videos, narration, call agents)
imports the client from here instead of setting up its own:

    from elevenlabs_client import get_client
    client = get_client()

The API key is never stored in code. The SDK reads ELEVENLABS_API_KEY from
the environment. In the cloud sessions the real key is a network secret the
proxy adds to every request to api.elevenlabs.io, so the variable only needs
a placeholder there (for example ELEVENLABS_API_KEY=proxy-injected).
"""

from functools import lru_cache

from elevenlabs.client import ElevenLabs


@lru_cache(maxsize=1)
def get_client() -> ElevenLabs:
    """Return one shared ElevenLabs client (key read from ELEVENLABS_API_KEY)."""
    return ElevenLabs()
