package main

import (
    "context"
    "log"
    "net"
    "os"
    "os/signal"
    "syscall"

    "google.golang.org/grpc"
    "google.golang.org/grpc/reflection"
    pb "sphere-fx-manager-api/go_workers/pb"
)

type extractorServer struct {
    pb.UnimplementedExtractorServiceServer
    engine *Engine
}

func (s *extractorServer) Extract(ctx context.Context, req *pb.ExtractRequest) (*pb.ExtractResponse, error) {
    if req.RawText == "" {
        return &pb.ExtractResponse{Success: false, ErrorMessage: "raw_text cannot be empty"}, nil
    }
    parsed, err := s.engine.Process(req.RawText)
    if err != nil {
        return &pb.ExtractResponse{Success: false, ErrorMessage: err.Error()}, nil
    }
    return &pb.ExtractResponse{ParsedSignal: parsed, Success: true}, nil
}

func main() {
    cfg := LoadConfig()
    log.Printf("Extractor starting on port %s", cfg.GRPCPort)
    lis, err := net.Listen("tcp", ":"+cfg.GRPCPort)
    if err != nil {
        log.Fatalf("Failed to listen: %v", err)
    }
    eng, err := NewEngine(cfg)
    if err != nil {
        log.Fatalf("Failed to init engine: %v", err)
    }
    s := grpc.NewServer()
    pb.RegisterExtractorServiceServer(s, &extractorServer{engine: eng})
    reflection.Register(s)
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
        <-sigCh
        log.Println("Shutting down...")
        s.GracefulStop()
    }()
    if err := s.Serve(lis); err != nil {
        log.Fatalf("Serve error: %v", err)
    }
}