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

    pb "sphere-fx-manager-api/go_workers/pb" // adjust import path
    "sphere-fx-manager-api/go_workers/extractor/engine"
    "sphere-fx-manager-api/go_workers/extractor/config"
)

type extractorServer struct {
    pb.UnimplementedExtractorServiceServer
    engine *engine.Engine
}

func (s *extractorServer) Extract(ctx context.Context, req *pb.ExtractRequest) (*pb.ExtractResponse, error) {
    if req.RawText == "" {
        return &pb.ExtractResponse{
            Success: false,
            ErrorMessage: "raw_text cannot be empty",
        }, nil
    }

    parsed, err := s.engine.Process(req.RawText)
    if err != nil {
        return &pb.ExtractResponse{
            Success: false,
            ErrorMessage: err.Error(),
        }, nil
    }

    return &pb.ExtractResponse{
        ParsedSignal: parsed,
        Success:      true,
    }, nil
}

func main() {
    cfg := config.LoadConfig()

    log.Printf("Starting Extractor gRPC server on port %s", cfg.GRPCPort)

    lis, err := net.Listen("tcp", ":"+cfg.GRPCPort)
    if err != nil {
        log.Fatalf("Failed to listen: %v", err)
    }

    eng, err := engine.NewEngine(cfg)
    if err != nil {
        log.Fatalf("Failed to initialize engine: %v", err)
    }

    grpcServer := grpc.NewServer(
        grpc.MaxRecvMsgSize(1024*1024), // 1MB
        grpc.MaxSendMsgSize(1024*1024),
    )
    pb.RegisterExtractorServiceServer(grpcServer, &extractorServer{engine: eng})
    reflection.Register(grpcServer)

    // Graceful shutdown
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
        <-sigCh
        log.Println("Shutting down extractor server...")
        grpcServer.GracefulStop()
    }()

    log.Printf("Extractor server listening on %v", lis.Addr())
    if err := grpcServer.Serve(lis); err != nil {
        log.Fatalf("Failed to serve: %v", err)
    }
}