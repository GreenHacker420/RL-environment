from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from models import DrugAction
from .environment import DrugInteractionEnv

try:
    from core.env_server import create_fastapi_app
except ImportError:
    try:
        from openenv_core.env_server import create_fastapi_app  # type: ignore[attr-defined]
    except ImportError:
        def _jsonify(value: Any) -> Any:
            if is_dataclass(value):
                return asdict(value)
            return value

        def create_fastapi_app(env: DrugInteractionEnv) -> FastAPI:
            app = FastAPI(title="Drug Interaction Env")

            @app.get("/health")
            async def health() -> dict[str, str]:
                return {"status": "healthy"}

            @app.post("/reset")
            async def reset() -> dict[str, Any]:
                observation = env.reset()
                return {"observation": _jsonify(observation), "state": _jsonify(env.state)}

            @app.post("/step")
            async def step(action_payload: dict[str, Any]) -> dict[str, Any]:
                action = DrugAction(**action_payload)
                observation = env.step(action)
                return {"observation": _jsonify(observation), "state": _jsonify(env.state)}

            @app.get("/state")
            async def state() -> dict[str, Any]:
                return _jsonify(env.state)

            @app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket) -> None:
                await websocket.accept()
                session_env = DrugInteractionEnv()
                try:
                    while True:
                        message = await websocket.receive_json()
                        message_type = message.get("type")
                        if message_type == "reset":
                            observation = session_env.reset()
                            await websocket.send_json(
                                {
                                    "observation": _jsonify(observation),
                                    "state": _jsonify(session_env.state),
                                }
                            )
                        elif message_type == "step":
                            action = DrugAction(**message.get("action", {}))
                            observation = session_env.step(action)
                            await websocket.send_json(
                                {
                                    "observation": _jsonify(observation),
                                    "state": _jsonify(session_env.state),
                                }
                            )
                        elif message_type == "state":
                            await websocket.send_json(_jsonify(session_env.state))
                except WebSocketDisconnect:
                    return


env = DrugInteractionEnv()
app = create_fastapi_app(env)
