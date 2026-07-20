package main

import (
    "database/sql"
    "fmt"
    "log"
    "time"

    _ "github.com/denisenkom/go-mssqldb"
)

var db *sql.DB

func InitDB(cfg *Config) error {
    if cfg.DBURL == "" {
        return fmt.Errorf("DATABASE_URL is required")
    }

    var err error
    db, err = sql.Open("sqlserver", cfg.DBURL)
    if err != nil {
        return fmt.Errorf("failed to open DB: %w", err)
    }

    db.SetMaxOpenConns(cfg.DBMaxOpenConns)
    db.SetMaxIdleConns(cfg.DBMaxIdleConns)
    db.SetConnMaxLifetime(cfg.DBConnMaxLifetime)

    if err := db.Ping(); err != nil {
        return fmt.Errorf("failed to ping DB: %w", err)
    }

    log.Println("Database connection established")
    return nil
}

func GetDB() *sql.DB {
    return db
}

func CloseDB() error {
    if db != nil {
        return db.Close()
    }
    return nil
}

type Job struct {
    ID         string
    SignalID   int64
    AccountID  int64
    UserID     int64
    LotSize    float64
    Status     string
    Payload    []byte
    Result     []byte
    ClaimedAt  *time.Time
    StartedAt  *time.Time
    FinishedAt *time.Time
    CreatedAt  time.Time
    UpdatedAt  *time.Time
}

func ClaimNextJob() (*Job, error) {
    tx, err := db.Begin()
    if err != nil {
        return nil, fmt.Errorf("begin tx: %w", err)
    }
    defer tx.Rollback()

    query := `
        SELECT TOP 1
            id, signal_id, account_id, user_id, lot_size, status,
            payload, result, claimed_at, started_at, finished_at, created_at, updated_at
        FROM live_jobs WITH (UPDLOCK, READPAST)
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
    `
    row := tx.QueryRow(query)

    var job Job
    var claimedAt, startedAt, finishedAt, updatedAt sql.NullTime
    var payloadBytes, resultBytes []byte

    err = row.Scan(
        &job.ID, &job.SignalID, &job.AccountID, &job.UserID,
        &job.LotSize, &job.Status,
        &payloadBytes, &resultBytes,
        &claimedAt, &startedAt, &finishedAt,
        &job.CreatedAt, &updatedAt,
    )
    if err == sql.ErrNoRows {
        return nil, nil
    }
    if err != nil {
        return nil, fmt.Errorf("scan job: %w", err)
    }
    job.Payload = payloadBytes
    job.Result = resultBytes
    if claimedAt.Valid {
        job.ClaimedAt = &claimedAt.Time
    }
    if startedAt.Valid {
        job.StartedAt = &startedAt.Time
    }
    if finishedAt.Valid {
        job.FinishedAt = &finishedAt.Time
    }
    if updatedAt.Valid {
        job.UpdatedAt = &updatedAt.Time
    }

    now := time.Now()
    updateQuery := `
        UPDATE live_jobs
        SET status = 'CLAIMED', claimed_at = @p1, started_at = @p2, updated_at = @p3
        WHERE id = @p4
    `
    _, err = tx.Exec(updateQuery, now, now, now, job.ID)
    if err != nil {
        return nil, fmt.Errorf("update job to CLAIMED: %w", err)
    }

    if err := tx.Commit(); err != nil {
        return nil, fmt.Errorf("commit claim: %w", err)
    }

    job.Status = "CLAIMED"
    job.ClaimedAt = &now
    job.StartedAt = &now
    return &job, nil
}

func UpdateJobStatus(jobID string, status string, resultJSON []byte) error {
    now := time.Now()
    query := `
        UPDATE live_jobs
        SET status = @p1, result = @p2, finished_at = @p3, updated_at = @p3
        WHERE id = @p4
    `
    _, err := db.Exec(query, status, resultJSON, now, jobID)
    if err != nil {
        return fmt.Errorf("update job status: %w", err)
    }
    return nil
}

func GetSignalData(signalID int64) (map[string]interface{}, error) {
    query := `
        SELECT
            id, symbol, action, order_type, entry_price, stop_loss,
            take_profit, confidence, created_by, created_at
        FROM signals
        WHERE id = @p1
    `
    row := db.QueryRow(query, signalID)

    var id int64
    var symbol, action, orderType string
    var entryPrice, stopLoss sql.NullFloat64
    var takeProfit []byte
    var confidence int
    var createdBy int64
    var createdAt time.Time

    err := row.Scan(
        &id, &symbol, &action, &orderType,
        &entryPrice, &stopLoss, &takeProfit,
        &confidence, &createdBy, &createdAt,
    )
    if err == sql.ErrNoRows {
        return nil, fmt.Errorf("signal %d not found", signalID)
    }
    if err != nil {
        return nil, fmt.Errorf("scan signal: %w", err)
    }

    result := map[string]interface{}{
        "id":          id,
        "symbol":      symbol,
        "action":      action,
        "order_type":  orderType,
        "entry_price": entryPrice.Float64,
        "stop_loss":   stopLoss.Float64,
        "take_profit": takeProfit,
        "confidence":  confidence,
        "created_by":  createdBy,
        "created_at":  createdAt,
    }
    return result, nil
}