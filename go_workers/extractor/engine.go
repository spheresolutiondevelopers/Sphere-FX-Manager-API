package engine

import (
    "fmt"
    "log"

    pb "sphere-fx-manager-api/go_workers/pb"
    "sphere-fx-manager-api/go_workers/extractor/cleaner"
    "sphere-fx-manager-api/go_workers/extractor/parser"
    "sphere-fx-manager-api/go_workers/extractor/validator"
    "sphere-fx-manager-api/go_workers/extractor/config"
)

type Engine struct {
    cleaner   *cleaner.Cleaner
    parser    *parser.Parser
    validator *validator.Validator
}

func NewEngine(cfg *config.Config) (*Engine, error) {
    cl := cleaner.NewCleaner()
    p, err := parser.NewParser(cfg.PatternsDir)
    if err != nil {
        return nil, fmt.Errorf("failed to initialize parser: %w", err)
    }
    v := validator.NewValidator()

    return &Engine{
        cleaner:   cl,
        parser:    p,
        validator: v,
    }, nil
}

func (e *Engine) Process(rawText string) (*pb.ParsedSignal, error) {
    // 1. Clean
    cleaned := e.cleaner.Clean(rawText)

    // 2. Parse
    parsed, err := e.parser.Parse(cleaned)
    if err != nil {
        return nil, fmt.Errorf("parse error: %w", err)
    }

    // 3. Validate
    if err := e.validator.Validate(parsed); err != nil {
        return nil, fmt.Errorf("validation error: %w", err)
    }

    // 4. Convert to protobuf
    return parsed, nil
}