"""gRPC client for the Go Backtester service."""

import grpc
from typing import Optional, AsyncIterator
from app.gen_proto import backtester_pb2, backtester_pb2_grpc
from app.config import settings

_backtester_channel: Optional[grpc.aio.Channel] = None
_backtester_stub: Optional[backtester_pb2_grpc.BacktesterServiceStub] = None


async def init_backtester_client() -> None:
    global _backtester_channel, _backtester_stub
    if _backtester_channel is None:
        _backtester_channel = grpc.aio.insecure_channel(settings.BACKTESTER_GRPC_ADDR)
        _backtester_stub = backtester_pb2_grpc.BacktesterServiceStub(_backtester_channel)


async def close_backtester_client() -> None:
    global _backtester_channel, _backtester_stub
    if _backtester_channel:
        await _backtester_channel.close()
        _backtester_channel = None
        _backtester_stub = None


async def run_backtest(
    signal_ids: list[int],
    config: dict,
) -> Optional[AsyncIterator[backtester_pb2.BacktestLogLine]]:
    """
    Run a backtest and stream log lines.
    Returns an async iterator of BacktestLogLine messages.
    """
    if _backtester_stub is None:
        await init_backtester_client()

    try:
        request = backtester_pb2.BacktestRequest(
            signal_ids=signal_ids,
            config_json=json.dumps(config)
        )
        stream = _backtester_stub.RunBacktest(request, timeout=60.0)
        return stream
    except grpc.RpcError:
        return None
    except Exception:
        return None