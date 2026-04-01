from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from models import DrugAction, DrugObservation, DrugState

try:
    from openenv_core.client import HTTPEnvClient, StepResult
except ImportError:
    try:
        from core.client import HTTPEnvClient, StepResult  # type: ignore[attr-defined]
    except ImportError:
        @dataclass
        class StepResult:
            observation: DrugObservation
            done: bool
            reward: float
            state: DrugState | None = None
            raw: dict[str, Any] | None = None

        class HTTPEnvClient(AbstractAsyncContextManager["HTTPEnvClient"]):
            def __init__(self, base_url: str) -> None:
                self.base_url = base_url.rstrip("/")
                self._client: httpx.AsyncClient | None = None

            async def __aenter__(self) -> "HTTPEnvClient":
                self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
                return self

            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
                if self._client is not None:
                    await self._client.aclose()
                    self._client = None


class DrugEnvClient(HTTPEnvClient):
    def __init__(self, base_url: str) -> None:
        super().__init__(base_url=base_url)

    def _step_payload(self, action: DrugAction) -> dict[str, Any]:
        return asdict(action)

    def _parse_result(self, payload: dict[str, Any]) -> StepResult:
        observation_payload = payload.get("observation", payload)
        observation = DrugObservation(**observation_payload)
        state_payload = payload.get("state")
        state = DrugState(**state_payload) if isinstance(state_payload, dict) else None
        return StepResult(
            observation=observation,
            done=observation.done,
            reward=float(observation.reward),
            state=state,
            raw=payload,
        )

    def _parse_state(self, payload: dict[str, Any]) -> DrugState:
        return DrugState(**payload)

    async def reset(self) -> StepResult:
        client = getattr(self, "_client", None)
        if client is None:
            raise RuntimeError("Client must be used inside an async context manager.")
        response = await client.post("/reset")
        response.raise_for_status()
        return self._parse_result(response.json())

    async def step(self, action: DrugAction) -> StepResult:
        client = getattr(self, "_client", None)
        if client is None:
            raise RuntimeError("Client must be used inside an async context manager.")
        response = await client.post("/step", json=self._step_payload(action))
        response.raise_for_status()
        return self._parse_result(response.json())

    async def state(self) -> DrugState:
        client = getattr(self, "_client", None)
        if client is None:
            raise RuntimeError("Client must be used inside an async context manager.")
        response = await client.get("/state")
        response.raise_for_status()
        return self._parse_state(response.json())

    def sync(self) -> "DrugEnvSyncClient":
        return DrugEnvSyncClient(self)


class DrugEnvSyncClient(AbstractContextManager["DrugEnvSyncClient"]):
    def __init__(self, async_client: DrugEnvClient) -> None:
        self._async_client = async_client
        self._loop: asyncio.AbstractEventLoop | None = None

    def __enter__(self) -> "DrugEnvSyncClient":
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_client.__aenter__())
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._loop is None:
            return
        self._loop.run_until_complete(self._async_client.__aexit__(exc_type, exc, tb))
        self._loop.close()
        asyncio.set_event_loop(None)

    def reset(self) -> StepResult:
        assert self._loop is not None
        return self._loop.run_until_complete(self._async_client.reset())

    def step(self, action: DrugAction) -> StepResult:
        assert self._loop is not None
        return self._loop.run_until_complete(self._async_client.step(action))

    def state(self) -> DrugState:
        assert self._loop is not None
        return self._loop.run_until_complete(self._async_client.state())


if __name__ == "__main__":
    with DrugEnvClient(base_url="http://localhost:8000").sync() as client:
        reset_result = client.reset()
        print(reset_result.observation.prompt)
        action = DrugAction(
            severity="moderate",
            explanation="Possible clinically important interaction requiring monitoring.",
        )
        step_result = client.step(action)
        print(step_result.reward)
        print(step_result.observation.feedback)
