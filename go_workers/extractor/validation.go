package main

import (
    "fmt"
    pb "sphere-fx-manager-api/go_workers/pb"
)

type Validator struct {
    // Could load symbol rules from config
}

func NewValidator() *Validator {
    return &Validator{}
}

func (v *Validator) Validate(signal *pb.ParsedSignal) error {
    if signal.Symbol == "" {
        return fmt.Errorf("symbol is required")
    }
    if signal.Action == "" {
        return fmt.Errorf("action is required")
    }
    if signal.Action != "BUY" && signal.Action != "SELL" {
        return fmt.Errorf("invalid action: %s", signal.Action)
    }
    if signal.EntryPrice <= 0 {
        return fmt.Errorf("entry price must be positive")
    }
    // Basic range checks could be added
    return nil
}
