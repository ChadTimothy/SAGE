"""Voice WebSocket proxy for secure Grok Voice API access."""

import asyncio
import json
import logging

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sage.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

GROK_REALTIME_URL = "wss://api.x.ai/v1/realtime"


class VoiceConnectionManager:
    """Manage paired client-Grok WebSocket connections."""

    def __init__(self):
        self.client_connections: dict[str, WebSocket] = {}
        self.grok_connections: dict[str, websockets.WebSocketClientProtocol] = {}
        self.voice_settings: dict[str, str] = {}

    async def connect_client(self, session_id: str, websocket: WebSocket) -> None:
        """Accept client WebSocket connection."""
        await websocket.accept()
        self.client_connections[session_id] = websocket
        logger.info(f"Voice client connected: {session_id}")

    async def connect_grok(self, session_id: str, voice: str = "ara") -> bool:
        """Connect to Grok Voice API with server-side auth."""
        settings = get_settings()
        if not settings.llm_api_key:
            logger.error("LLM_API_KEY not configured")
            return False

        try:
            url = f"{GROK_REALTIME_URL}?model=grok-2-voice"
            ws = await websockets.connect(url)
            self.grok_connections[session_id] = ws
            self.voice_settings[session_id] = voice

            # Configure session
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "voice": voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                    },
                },
            }))

            # Authenticate with server-side key
            await ws.send(json.dumps({
                "type": "auth",
                "api_key": settings.llm_api_key,
            }))

            logger.info(f"Grok voice connected: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Grok: {e}")
            return False

    async def disconnect(self, session_id: str) -> None:
        """Clean up both connections."""
        if session_id in self.grok_connections:
            try:
                await self.grok_connections[session_id].close()
            except Exception:
                pass
            del self.grok_connections[session_id]

        if session_id in self.client_connections:
            del self.client_connections[session_id]

        self.voice_settings.pop(session_id, None)
        logger.info(f"Voice disconnected: {session_id}")

    async def forward_to_grok(self, session_id: str, message: str) -> None:
        """Forward message from client to Grok."""
        if session_id in self.grok_connections:
            await self.grok_connections[session_id].send(message)

    async def send_to_client(self, session_id: str, message: str) -> None:
        """Send message to client."""
        if session_id in self.client_connections:
            await self.client_connections[session_id].send_text(message)

    async def update_voice(self, session_id: str, voice: str) -> None:
        """Update voice setting and notify Grok."""
        if session_id in self.grok_connections:
            self.voice_settings[session_id] = voice
            await self.grok_connections[session_id].send(json.dumps({
                "type": "session.update",
                "session": {"voice": voice},
            }))


manager = VoiceConnectionManager()


@router.websocket("/api/voice/{session_id}")
async def websocket_voice(websocket: WebSocket, session_id: str) -> None:
    """Voice WebSocket proxy endpoint.

    Proxies audio between browser and Grok Voice API,
    keeping the API key secure on the server.
    """
    await manager.connect_client(session_id, websocket)

    # Get initial voice preference from first message
    try:
        init_data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        voice = init_data.get("voice", "ara")
    except asyncio.TimeoutError:
        voice = "ara"
    except Exception:
        voice = "ara"

    # Connect to Grok
    if not await manager.connect_grok(session_id, voice):
        await websocket.send_json({
            "type": "error",
            "message": "Failed to connect to voice service",
        })
        await manager.disconnect(session_id)
        return

    # Notify client of successful connection
    await websocket.send_json({"type": "session.ready"})

    async def client_to_grok() -> None:
        """Forward client messages to Grok."""
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle voice change requests locally
                if message.get("type") == "session.update":
                    new_voice = message.get("session", {}).get("voice")
                    if new_voice:
                        await manager.update_voice(session_id, new_voice)
                else:
                    # Forward everything else to Grok
                    await manager.forward_to_grok(session_id, data)
        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Client->Grok error: {e}")

    async def grok_to_client() -> None:
        """Forward Grok messages to client."""
        try:
            grok_ws = manager.grok_connections.get(session_id)
            if not grok_ws:
                return

            async for message in grok_ws:
                await manager.send_to_client(session_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Grok connection closed: {session_id}")
        except Exception as e:
            logger.error(f"Grok->Client error: {e}")

    # Run both directions concurrently
    try:
        await asyncio.gather(
            client_to_grok(),
            grok_to_client(),
            return_exceptions=True,
        )
    finally:
        await manager.disconnect(session_id)
