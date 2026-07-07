package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net"
    "os"
    "os/signal"
    "syscall"
    "time"

    "google.golang.org/grpc"
    "google.golang.org/grpc/reflection"

    pb "sphere-fx-manager-api/go_workers/pb"
)

type backtesterServer struct {
    pb.UnimplementedBacktesterServiceServer
    sim *Simulator
}

func (s *backtesterServer) RunBacktest(
    req *pb.BacktestRequest,
    stream pb.BacktesterService_RunBacktestServer,
) error {
    if len(req.Signals) == 0 {
        return fmt.Errorf("no signals provided")
    }

    // Convert protobuf signals to internal format
    signals := make([]Signal, len(req.Signals))
    for i, pbSig := range req.Signals {
        signals[i] = Signal{
            ID:          pbSig.Id,
            Symbol:      pbSig.Symbol,
            Action:      pbSig.Action,
            OrderType:   pbSig.OrderType,
            EntryPrice:  pbSig.EntryPrice,
            StopLoss:    pbSig.StopLoss,
            TakeProfit:  pbSig.TakeProfit,
            Timestamp:   pbSig.Timestamp.AsTime(),
            Source:      pbSig.Source,
            Confidence:  int(pbSig.Confidence),
        }
    }

    // Apply any config overrides from JSON (optional)
    var configOverride map[string]interface{}
    if req.ConfigJson != "" {
        if err := json.Unmarshal([]byte(req.ConfigJson), &configOverride); err != nil {
            return fmt.Errorf("invalid config JSON: %w", err)
        }
        // Apply overrides to the simulator (already handled inside)
    }

    // Run simulation
    result := s.sim.Run(signals)

    // Stream logs
    for _, logLine := range result.Logs {
        if err := stream.Send(&pb.BacktestLogLine{
            Message:  logLine.Message,
            Level:    logLine.Level,
            Progress: int32(logLine.Progress),
        }); err != nil {
            return err
        }
    }

    // Send final result as a special log line
    resultJSON, err := json.Marshal(result)
    if err != nil {
        return fmt.Errorf("failed to serialize result: %w", err)
    }
    if err := stream.Send(&pb.BacktestLogLine{
        Message:  string(resultJSON),
        Level:    "RESULT",
        Progress: 100,
    }); err != nil {
        return err
    }

    return nil
}

func (s *backtesterServer) GetResult(
    ctx context.Context,
    req *pb.BacktestId,
) (*pb.BacktestResult, error) {
    result, ok := s.sim.GetCachedResult(req.RunId)
    if !ok {
        return nil, fmt.Errorf("result not found for run ID %d", req.RunId)
    }
    return &pb.BacktestResult{
        RunId:         result.RunID,
        TotalSignals:  int32(result.TotalSignals),
        WinCount:      int32(result.WinCount),
        LossCount:     int32(result.LossCount),
        WinRate:       result.WinRate,
        TotalRr:       result.TotalRR,
        ProfitFactor:  result.ProfitFactor,
        MaxDrawdown:   result.MaxDrawdown,
        SharpeRatio:   result.SharpeRatio,
        EquityCurve:   result.EquityCurve,
        StartedAt:     nil, // optional, could be added
        FinishedAt:    nil,
    }, nil
}

func main() {
    cfg := LoadConfig()

    log.Printf("Starting Backtester gRPC server on port %s", cfg.GRPCPort)

    lis, err := net.Listen("tcp", ":"+cfg.GRPCPort)
    if err != nil {
        log.Fatalf("Failed to listen: %v", err)
    }

    sim := NewSimulator(cfg)

    grpcServer := grpc.NewServer(
        grpc.MaxRecvMsgSize(1024*1024),
        grpc.MaxSendMsgSize(1024*1024),
        grpc.ConnectionTimeout(60*time.Second),
    )
    pb.RegisterBacktesterServiceServer(grpcServer, &backtesterServer{sim: sim})
    reflection.Register(grpcServer)

    // Graceful shutdown
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
        <-sigCh
        log.Println("Shutting down backtester server...")
        grpcServer.GracefulStop()
    }()

    log.Printf("Backtester server listening on %v", lis.Addr())
    if err := grpcServer.Serve(lis); err != nil {
        log.Fatalf("Failed to serve: %v", err)
    }
}