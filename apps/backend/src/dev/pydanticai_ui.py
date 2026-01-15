"""Run the PydanticAI Web Chat UI for the chat assistant (dev only)."""

from __future__ import annotations

import uvicorn

from services.chat_agent import get_chat_agent


def main() -> None:
    """Launch the PydanticAI Web Chat UI for local agent iteration."""
    agent = get_chat_agent()
    app = agent.to_web()
    uvicorn.run(app, host="127.0.0.1", port=8021)


if __name__ == "__main__":
    main()
