package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "math"
)

type RiskManager struct {
    cfg *Config
}

func NewRiskManager(cfg *Config) *RiskManager {
    return &RiskManager{cfg: cfg}
}

func (r *RiskManager) ValidateJob(job *Job) error {
    // Parse payload
    var payload map[string]interface{}
    if err := json.Unmarshal(job.Payload, &payload); err != nil {
        return fmt.Errorf("invalid payload JSON: %w", err)
    }

    symbol, _ := payload["symbol"].(string)
    action, _ := payload["action"].(string)
    entryPrice, _ := payload["entry_price"].(float64)
    stopLoss, _ := payload["stop_loss"].(float64)
    takeProfitRaw, _ := payload["take_profit"].([]interface{})
    var takeProfit []float64
    for _, v := range takeProfitRaw {
        if val, ok := v.(float64); ok {
            takeProfit = append(takeProfit, val)
        }
    }
    lotSize, _ := payload["lot_size"].(float64)

    // Check lot size within limits
    if lotSize < r.cfg.DefaultMinLot {
        return fmt.Errorf("lot size %.2f below minimum %.2f", lotSize, r.cfg.DefaultMinLot)
    }
    if lotSize > r.cfg.DefaultMaxLot {
        return fmt.Errorf("lot size %.2f exceeds maximum %.2f", lotSize, r.cfg.DefaultMaxLot)
    }

    // Check daily drawdown
    if err := r.checkDailyDrawdown(job.AccountID, lotSize, symbol, entryPrice, stopLoss); err != nil {
        return err
    }

    // Check max concurrent positions
    if err := r.checkMaxPositions(job.AccountID); err != nil {
        return err
    }

    // Check minimum RR
    if err := r.checkMinRR(entryPrice, stopLoss, takeProfit); err != nil {
        return err
    }

    // Basic validation: SL must be on correct side
    if entryPrice == 0 || stopLoss == 0 {
        return fmt.Errorf("entry price and stop loss must be non-zero")
    }
    if action == "BUY" && stopLoss >= entryPrice {
        return fmt.Errorf("stop loss must be below entry for BUY orders")
    }
    if action == "SELL" && stopLoss <= entryPrice {
        return fmt.Errorf("stop loss must be above entry for SELL orders")
    }

    log.Printf("Risk checks passed for job %s", job.ID)
    return nil
}

func (r *RiskManager) checkDailyDrawdown(accountID int64, lotSize float64, symbol string, entryPrice, stopLoss float64) error {
    // Get account balance
    var balance float64
    balanceQuery := `
        SELECT ISNULL(balance_cache, 0)
        FROM mt5_accounts
        WHERE id = @p1
    `
    dbConn := GetDB()
    err := dbConn.QueryRow(balanceQuery, accountID).Scan(&balance)
    if err != nil {
        if err == sql.ErrNoRows {
            return fmt.Errorf("account %d not found", accountID)
        }
        return fmt.Errorf("failed to fetch account balance: %w", err)
    }
    if balance <= 0 {
        return fmt.Errorf("account balance is zero or negative: %.2f", balance)
    }

    // Determine max daily loss percentage
    var maxDailyLossPercent float64
    riskQuery := `
        SELECT ISNULL(max_daily_loss, 0)
        FROM account_risk_settings
        WHERE account_id = @p1
    `
    err = dbConn.QueryRow(riskQuery, accountID).Scan(&maxDailyLossPercent)
    if err != nil {
        if err == sql.ErrNoRows {
            maxDailyLossPercent = r.cfg.DefaultMaxDailyDrawdown
        } else {
            return fmt.Errorf("failed to fetch risk settings: %w", err)
        }
    }
    if maxDailyLossPercent <= 0 {
        maxDailyLossPercent = r.cfg.DefaultMaxDailyDrawdown
    }

    // Compute maximum allowed daily loss
    maxAllowedLoss := balance * (maxDailyLossPercent / 100.0)
    if maxAllowedLoss <= 0 {
        return fmt.Errorf("max allowed daily loss is zero or negative: %.2f", maxAllowedLoss)
    }

    // Fetch today's realized P&L
    var todayPL float64
    plQuery := `
        SELECT ISNULL(SUM(realized_pl), 0)
        FROM daily_pl
        WHERE account_id = @p1 AND trade_date = CAST(GETDATE() AS DATE)
    `
    err = dbConn.QueryRow(plQuery, accountID).Scan(&todayPL)
    if err != nil {
        log.Printf("Warning: could not fetch daily P&L: %v", err)
        todayPL = 0
    }

    // Estimate potential loss
    var potentialLoss float64
    if lotSize > 0 && entryPrice > 0 && stopLoss > 0 {
        priceDiff := math.Abs(entryPrice - stopLoss)
        potentialLoss = lotSize * 100000 * priceDiff
        if potentialLoss > 0 && potentialLoss < 0.01 {
            potentialLoss = 0.01
        }
    } else {
        potentialLoss = lotSize * 10
    }

    // Check if daily loss would exceed limit
    projectedLoss := todayPL - potentialLoss
    if projectedLoss < -maxAllowedLoss {
        return fmt.Errorf(
            "daily loss limit would be exceeded: current loss %.2f, potential loss %.2f, limit %.2f",
            todayPL, potentialLoss, maxAllowedLoss,
        )
    }

    log.Printf("Daily drawdown check passed: current loss %.2f, potential loss %.2f, limit %.2f",
        todayPL, potentialLoss, maxAllowedLoss)
    return nil
}

func (r *RiskManager) checkMaxPositions(accountID int64) error {
    positions, err := GetOpenPositions(accountID)
    if err != nil {
        return fmt.Errorf("failed to get open positions: %w", err)
    }
    if len(positions) >= r.cfg.DefaultMaxPositions {
        return fmt.Errorf("max positions (%d) reached", r.cfg.DefaultMaxPositions)
    }
    return nil
}

func (r *RiskManager) checkMinRR(entry, stopLoss float64, takeProfit []float64) error {
    if entry == 0 || stopLoss == 0 {
        return nil
    }
    if len(takeProfit) == 0 {
        return nil
    }
    risk := math.Abs(entry - stopLoss)
    if risk == 0 {
        return nil
    }
    tp := takeProfit[0]
    reward := math.Abs(tp - entry)
    rr := reward / risk
    if rr < r.cfg.DefaultMinRR {
        return fmt.Errorf("RR ratio %.2f below minimum %.2f", rr, r.cfg.DefaultMinRR)
    }
    return nil
}