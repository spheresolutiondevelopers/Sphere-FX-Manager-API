package risk

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"time"

	"sphere-fx-manager-api/go_workers/live_worker/config"
	"sphere-fx-manager-api/go_workers/live_worker/db"
	"sphere-fx-manager-api/go_workers/live_worker/position_mgr"
)

type RiskManager struct {
	cfg *config.Config
}

func NewRiskManager(cfg *config.Config) *RiskManager {
	return &RiskManager{cfg: cfg}
}

// ValidateJob performs all risk checks on the job and returns an error if any fails.
func (r *RiskManager) ValidateJob(job *db.Job) error {
	// 1. Parse payload
	var payload map[string]interface{}
	if err := json.Unmarshal(job.Payload, &payload); err != nil {
		return fmt.Errorf("invalid payload JSON: %w", err)
	}

	symbol, _ := payload["symbol"].(string)
	action, _ := payload["action"].(string)
	orderType, _ := payload["order_type"].(string)
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

	// 2. Check lot size within limits
	if lotSize < r.cfg.DefaultMinLot {
		return fmt.Errorf("lot size %.2f below minimum %.2f", lotSize, r.cfg.DefaultMinLot)
	}
	if lotSize > r.cfg.DefaultMaxLot {
		return fmt.Errorf("lot size %.2f exceeds maximum %.2f", lotSize, r.cfg.DefaultMaxLot)
	}

	// 3. Check daily drawdown
	if err := r.checkDailyDrawdown(job.AccountID, job.LotSize, symbol); err != nil {
		return err
	}

	// 4. Check max concurrent positions
	if err := r.checkMaxPositions(job.AccountID); err != nil {
		return err
	}

	// 5. Check minimum RR
	if err := r.checkMinRR(entryPrice, stopLoss, takeProfit); err != nil {
		return err
	}

	// 6. Basic validation: SL must be on correct side
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

func (r *RiskManager) checkDailyDrawdown(accountID int64, lotSize float64, symbol string) error {
	// 1. Get account balance
	var balance float64
	balanceQuery := `
		SELECT ISNULL(balance_cache, 0)
		FROM mt5_accounts
		WHERE id = @p1
	`
	err := db.GetDB().QueryRow(balanceQuery, accountID).Scan(&balance)
	if err != nil {
		if err == sql.ErrNoRows {
			return fmt.Errorf("account %d not found", accountID)
		}
		return fmt.Errorf("failed to fetch account balance: %w", err)
	}
	if balance <= 0 {
		return fmt.Errorf("account balance is zero or negative: %.2f", balance)
	}

	// 2. Determine max daily loss percentage from account_risk_settings
	var maxDailyLossPercent float64
	riskQuery := `
		SELECT ISNULL(max_daily_loss, 0)
		FROM account_risk_settings
		WHERE account_id = @p1
	`
	err = db.GetDB().QueryRow(riskQuery, accountID).Scan(&maxDailyLossPercent)
	if err != nil {
		if err == sql.ErrNoRows {
			// No specific settings, use global default
			maxDailyLossPercent = r.cfg.DefaultMaxDailyDrawdown
		} else {
			return fmt.Errorf("failed to fetch risk settings: %w", err)
		}
	}
	// Fallback: if still 0, use the global default
	if maxDailyLossPercent <= 0 {
		maxDailyLossPercent = r.cfg.DefaultMaxDailyDrawdown
	}

	// 3. Compute maximum allowed daily loss in currency
	maxAllowedLoss := balance * (maxDailyLossPercent / 100.0)
	if maxAllowedLoss <= 0 {
		return fmt.Errorf("max allowed daily loss is zero or negative: %.2f", maxAllowedLoss)
	}

	// 4. Fetch today's realized P&L for this account
	var todayPL float64
	plQuery := `
		SELECT ISNULL(SUM(realized_pl), 0)
		FROM daily_pl
		WHERE account_id = @p1 AND trade_date = CAST(GETDATE() AS DATE)
	`
	err = db.GetDB().QueryRow(plQuery, accountID).Scan(&todayPL)
	if err != nil {
		// If the table doesn't exist or no rows, treat as 0
		log.Printf("Warning: could not fetch daily P&L: %v", err)
		todayPL = 0
	}

	// 5. Check if the current trade would exceed the limit
	// We need to estimate the potential loss of this trade.
	// We'll use the stop loss distance to compute max loss in currency.
	// For simplicity, we assume a pip value based on symbol; in production we'd fetch it.
	// We'll use a simplified risk amount = lotSize * stopLossDistance (in account currency).
	// For forex pairs, pip value = lotSize * 0.0001 * 100000 (for standard lot) = lotSize * 10.
	// We'll use a generic multiplier: 10 * lotSize * priceDiff (approximate).
	// In a real system, get pip value from symbol table.
	var potentialLoss float64
	if lotSize > 0 && entryPrice > 0 && stopLoss > 0 {
		priceDiff := math.Abs(entryPrice - stopLoss)
		// Approximate pip value: for most pairs, 1 pip = 0.0001, and 1 lot = 100,000 units
		// So loss in account currency = lotSize * 100,000 * priceDiff
		potentialLoss = lotSize * 100000 * priceDiff
		// Cap at a reasonable value
		if potentialLoss > 0 && potentialLoss < 0.01 {
			potentialLoss = 0.01 // minimum
		}
	} else {
		// If we can't estimate, we'll assume a small loss to be conservative.
		potentialLoss = lotSize * 10 // minimal pip value
	}

	// 6. Check if daily loss after this trade would exceed the limit
	projectedLoss := todayPL - potentialLoss // todayPL is negative for losses
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
	positions, err := position_mgr.GetOpenPositions(accountID)
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
		return nil // RR check not applicable without entry/SL
	}
	if len(takeProfit) == 0 {
		return nil // no TP, skip RR check
	}
	risk := math.Abs(entry - stopLoss)
	if risk == 0 {
		return nil
	}
	// Use the nearest TP to entry (first or closest)
	tp := takeProfit[0]
	reward := math.Abs(tp - entry)
	rr := reward / risk
	if rr < r.cfg.DefaultMinRR {
		return fmt.Errorf("RR ratio %.2f below minimum %.2f", rr, r.cfg.DefaultMinRR)
	}
	return nil
}