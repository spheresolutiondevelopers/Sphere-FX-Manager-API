package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    cfg := LoadConfig()

    // Initialize database
    if err := InitDB(cfg); err != nil {
        log.Fatalf("Failed to initialize database: %v", err)
    }

    log.Printf("Starting Live Worker (poll interval: %ds)", cfg.PollIntervalSeconds)

    proc := NewProcessor(cfg)

    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

    go func() {
        <-sigCh
        log.Println("Shutdown signal received, stopping live worker...")
        cancel()
    }()

    ticker := time.NewTicker(time.Duration(cfg.PollIntervalSeconds) * time.Second)
    defer ticker.Stop()

    log.Println("Live worker started, polling for jobs...")

    for {
        select {
        case <-ctx.Done():
            log.Println("Live worker shutting down gracefully")
            proc.Shutdown()
            return
        case <-ticker.C:
            if err := proc.ProcessNextJob(ctx); err != nil {
                log.Printf("Error processing job: %v", err)
            }
        }
    }
}