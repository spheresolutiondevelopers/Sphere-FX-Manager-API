package main

import (
    "fmt"
    //"log"
    pb "sphere-fx-manager-api/go_workers/pb"
)

type Engine struct {
    cleaner   *Cleaner
    parser    *Parser
    validator *Validator
}

func NewEngine(cfg *Config) (*Engine, error) {
    cl, err := NewCleaner(cfg.PatternsDir)
    if err != nil {
        return nil, fmt.Errorf("cleaner init: %w", err)
    }
    p, err := NewParser(cfg.PatternsDir)
    if err != nil {
        return nil, fmt.Errorf("parser init: %w", err)
    }
    v := NewValidator()
    return &Engine{cleaner: cl, parser: p, validator: v}, nil
}

func (e *Engine) Process(rawText string) (*pb.ParsedSignal, error) {
    cleaned := e.cleaner.Clean(rawText)
    parsed, err := e.parser.Parse(cleaned)
    if err != nil {
        return nil, fmt.Errorf("parse: %w", err)
    }
    if err := e.validator.Validate(parsed); err != nil {
        return nil, fmt.Errorf("validation: %w", err)
    }
    return parsed, nil
}