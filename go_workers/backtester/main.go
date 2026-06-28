package main

import (
    "context"
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
    "sphere-fx-manager-api/go_workers/backtester/config"
    "sphere-fx-manager-api/go_workers/backtester/simulator"
)

type backtesterServer struct {
    pb.UnimplementedBacktesterServiceServer
    sim *simulator.Simulator
}

// RunBacktest executes a backtest and streams log lines.
// The signal data is fully contained in the gRPC request.
func (s *backtesterServer) RunBacktest(
    req *pb.BacktestRequest,
    stream pb.BacktesterService_RunBacktestServer,
) error {
    // Validate request
    if len(req.Signals) == 0 {
        return fmt.Errorf("no signals provided for backtest")
    }

    // Parse config overrides from JSON
    configOverride := make(map[string]interface{})
    if req.ConfigJson != "" {
        if err := json.Unmarshal([]byte(req.ConfigJson), &configOverride); err != nil {
            return fmt.Errorf("invalid config JSON: %w", err)
        }
    }

    // Apply config overrides to the simulator
    simConfig := s.sim.Config()
    if rr, ok := configOverride["rr_ratio"].(float64); ok && rr > 0 {
        simConfig.DefaultRR = rr
    }
    if spread, ok := configOverride["spread_pips"].(float64); ok && spread >= 0 {
        simConfig.SpreadPips = spread
    }
    if commission, ok := configOverride["commission_per_lot"].(float64); ok && commission >= 0 {
        simConfig.CommissionPerLot = commission
    }
    if strategy, ok := configOverride["tp_strategy"].(string); ok {
        simConfig.TPStrategy = strategy
    }

    // Convert protobuf signals to internal format
    signals := make([]simulator.Signal, len(req.Signals))
    for i, pbSig := range req.Signals {
        signals[i] = simulator.Signal{
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

    // Run simulation
    result := s.sim.Run(signals)

    // Stream log lines as they become available (in real implementation, streaming)
    for _, logLine := range result.Logs {
        if err := stream.Send(&pb.BacktestLogLine{
            Message:  logLine.Message,
            Level:    logLine.Level,
            Progress: int32(logLine.Progress),
        }); err != nil {
            return err
        }
    }

    // Send final result as a special log message with the result JSON
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

// GetResult retrieves a previously completed backtest result.
// In production, this would fetch from a cache or DB.
// For this stateless implementation, we store results in memory with TTL.
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
        Trades:        convertTrades(result.Trades),
        StartedAt:     timestamppb.New(result.StartedAt),
        FinishedAt:    timestamppb.New(result.FinishedAt),
    }, nil
}

func convertTrades(trades []simulator.Trade) []*pb.TradeDetail {
    result := make([]*pb.TradeDetail, len(trades))
    for i, t := range trades {
        result[i] = &pb.TradeDetail{
            SignalId:    int32(t.SignalID),
            Symbol:      t.Symbol,
            Action:      t.Action,
            EntryPrice:  t.EntryPrice,
            ExitPrice:   t.ExitPrice,
            RrAchieved:  t.RRAchieved,
            Outcome:     t.Outcome,
        }
    }
    return result
}

func main() {
    cfg := config.LoadConfig()

    log.Printf("Starting Backtester gRPC server on port %s", cfg.GRPCPort)

    lis, err := net.Listen("tcp", ":"+cfg.GRPCPort)
    if err != nil {
        log.Fatalf("Failed to listen: %v", err)
    }

    sim := simulator.NewSimulator(cfg)

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