package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "time"
)

type Position struct {
    ID            int64
    JobID         string
    OrderID       int64
    AccountID     int64
    BrokerPosID   string
    Symbol        string
    Action        string
    EntryPrice    float64
    CurrentPrice  float64
    LotSize       float64
    StopLoss      float64
    TakeProfit    []float64
    RemainingLots float64
    Status        string
    PnL           float64
    OpenedAt      time.Time
    ClosedAt      *time.Time
    CloseReason   string
}

func GetOpenPositions(accountID int64) ([]Position, error) {
    query := `
        SELECT
            id, job_id, order_id, account_id, broker_position_id,
            symbol, action, entry_price, current_price, lot_size,
            stop_loss, take_profit, remaining_lots, status, pnl,
            opened_at, closed_at, close_reason
        FROM live_positions
        WHERE account_id = @p1 AND status = 'OPEN'
    `
    rows, err := db.Query(query, accountID)
    if err != nil {
        return nil, fmt.Errorf("query open positions: %w", err)
    }
    defer rows.Close()

    var positions []Position
    for rows.Next() {
        var pos Position
        var takeProfitJSON []byte
        var closedAt sql.NullTime
        var closeReason sql.NullString

        err := rows.Scan(
            &pos.ID, &pos.JobID, &pos.OrderID, &pos.AccountID, &pos.BrokerPosID,
            &pos.Symbol, &pos.Action, &pos.EntryPrice, &pos.CurrentPrice, &pos.LotSize,
            &pos.StopLoss, &takeProfitJSON, &pos.RemainingLots, &pos.Status, &pos.PnL,
            &pos.OpenedAt, &closedAt, &closeReason,
        )
        if err != nil {
            log.Printf("Scan position row error: %v", err)
            continue
        }
        if len(takeProfitJSON) > 0 {
            var tp []float64
            if err := json.Unmarshal(takeProfitJSON, &tp); err == nil {
                pos.TakeProfit = tp
            }
        }
        if closedAt.Valid {
            pos.ClosedAt = &closedAt.Time
        }
        if closeReason.Valid {
            pos.CloseReason = closeReason.String
        }
        positions = append(positions, pos)
    }
    return positions, nil
}

func UpdatePositionPrice(positionID int64, currentPrice, pnl float64) error {
    query := `
        UPDATE live_positions
        SET current_price = @p1, pnl = @p2, updated_at = GETDATE()
        WHERE id = @p3
    `
    _, err := db.Exec(query, currentPrice, pnl, positionID)
    if err != nil {
        return fmt.Errorf("update position: %w", err)
    }
    return nil
}

func ClosePosition(positionID int64, closeReason string) error {
    now := time.Now()
    query := `
        UPDATE live_positions
        SET status = 'CLOSED', closed_at = @p1, close_reason = @p2, updated_at = @p1
        WHERE id = @p3
    `
    _, err := db.Exec(query, now, closeReason, positionID)
    if err != nil {
        return fmt.Errorf("close position: %w", err)
    }
    return nil
}