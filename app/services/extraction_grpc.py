"""gRPC client for the Go Extractor service."""

import grpc
from typing import Optional
from app.gen_proto import extractor_pb2, extractor_pb2_grpc
from app.config import settings

# Global channel (initialized at startup)
_extractor_channel: Optional[grpc.aio.Channel] = None
_extractor_stub: Optional[extractor_pb2_grpc.ExtractorServiceStub] = None


async def init_extractor_client() -> None:
    """Initialize the gRPC channel and stub."""
    global _extractor_channel, _extractor_stub
    if _extractor_channel is None:
        _extractor_channel = grpc.aio.insecure_channel(settings.EXTRACTOR_GRPC_ADDR)
        _extractor_stub = extractor_pb2_grpc.ExtractorServiceStub(_extractor_channel)


async def close_extractor_client() -> None:
    """Close the gRPC channel."""
    global _extractor_channel, _extractor_stub
    if _extractor_channel:
        await _extractor_channel.close()
        _extractor_channel = None
        _extractor_stub = None


async def extract_signal(raw_text: str) -> Optional[extractor_pb2.ExtractResponse]:
    """
    Send a raw text to the Go Extractor and return the parsed signal.
    Returns None on error.
    """
    if _extractor_stub is None:
        await init_extractor_client()

    try:
        request = extractor_pb2.ExtractRequest(raw_text=raw_text)
        response = await _extractor_stub.Extract(request, timeout=5.0)
        return response
    except grpc.RpcError as e:
        # Log error (handled by caller)
        return None
    except Exception as e:
        return None