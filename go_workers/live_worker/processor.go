package main

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "io"
    "log"
    "net/http"
    // "time"  // REMOVE THIS LINE
)

type Processor struct {
    cfg        *Config
    httpClient *http.Client
    riskMgr    *RiskManager
}

func NewProcessor(cfg *Config) *Processor {
    return &Processor{
        cfg: cfg,
        httpClient: &http.Client{
            Timeout: cfg.MT5Timeout,
        },
        riskMgr: NewRiskManager(cfg),
    }
}

func (p *Processor) ProcessNextJob(ctx context.Context) error {
    job, err := ClaimNextJob()
    if err != nil {
        return fmt.Errorf("claim job: %w", err)
    }
    if job == nil {
        return nil
    }

    log.Printf("Claimed job %s (signal %d, account %d)", job.ID, job.SignalID, job.AccountID)

    var processErr error
    defer func() {
        if r := recover(); r != nil {
            log.Printf("Panic processing job %s: %v", job.ID, r)
            processErr = fmt.Errorf("panic: %v", r)
        }
        if processErr != nil {
            result := map[string]interface{}{"error": processErr.Error()}
            resultJSON, _ := json.Marshal(result)
            if err := UpdateJobStatus(job.ID, "FAILED", resultJSON); err != nil {
                log.Printf("Failed to update job %s to FAILED: %v", job.ID, err)
            }
            log.Printf("Job %s marked as FAILED: %v", job.ID, processErr)
        }
    }()

    if err := p.riskMgr.ValidateJob(job); err != nil {
        processErr = fmt.Errorf("risk validation failed: %w", err)
        return processErr
    }

    result, err := p.executeOrder(job)
    if err != nil {
        processErr = fmt.Errorf("MT5 execution failed: %w", err)
        return processErr
    }

    resultJSON, err := json.Marshal(result)
    if err != nil {
        processErr = fmt.Errorf("failed to marshal result: %w", err)
        return processErr
    }
    if err := UpdateJobStatus(job.ID, "SUCCESS", resultJSON); err != nil {
        processErr = fmt.Errorf("failed to update job status: %w", err)
        return processErr
    }

    log.Printf("Job %s completed successfully", job.ID)
    return nil
}

func (p *Processor) executeOrder(job *Job) (map[string]interface{}, error) {
    var payload map[string]interface{}
    if err := json.Unmarshal(job.Payload, &payload); err != nil {
        return nil, fmt.Errorf("invalid payload: %w", err)
    }

    orderReq := map[string]interface{}{
        "symbol":      payload["symbol"],
        "action":      payload["action"],
        "order_type":  payload["order_type"],
        "lot_size":    payload["lot_size"],
        "entry_price": payload["entry_price"],
        "stop_loss":   payload["stop_loss"],
        "take_profit": payload["take_profit"],
    }
    body, err := json.Marshal(orderReq)
    if err != nil {
        return nil, fmt.Errorf("marshal order request: %w", err)
    }

    url := p.cfg.MT5BridgeURL + "/execute"
    req, err := http.NewRequest("POST", url, bytes.NewReader(body))
    if err != nil {
        return nil, fmt.Errorf("create request: %w", err)
    }
    req.Header.Set("Content-Type", "application/json")

    resp, err := p.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("HTTP request to MT5 Bridge: %w", err)
    }
    defer resp.Body.Close()

    respBody, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, fmt.Errorf("read response body: %w", err)
    }

    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("MT5 Bridge returned %d: %s", resp.StatusCode, string(respBody))
    }

    var result map[string]interface{}
    if err := json.Unmarshal(respBody, &result); err != nil {
        return nil, fmt.Errorf("parse MT5 response: %w", err)
    }

    if errMsg, ok := result["error"].(string); ok && errMsg != "" {
        return nil, fmt.Errorf("MT5 Bridge error: %s", errMsg)
    }

    return result, nil
}

func (p *Processor) Shutdown() {
    if err := CloseDB(); err != nil {
        log.Printf("Error closing DB: %v", err)
    }
    log.Println("Live worker shut down")
}