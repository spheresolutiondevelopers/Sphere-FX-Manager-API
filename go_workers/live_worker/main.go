package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"sphere-fx-manager-api/go_workers/live_worker/config"
	"sphere-fx-manager-api/go_workers/live_worker/processor"
)

func main() {
	cfg := config.LoadConfig()

	log.Printf("Starting Live Worker (poll interval: %ds)", cfg.PollIntervalSeconds)

	// Create processor
	proc := processor.NewProcessor(cfg)

	// Context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Signal handling
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		log.Println("Shutdown signal received, stopping live worker...")
		cancel()
	}()

	// Main polling loop
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