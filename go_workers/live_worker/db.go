package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/denisenkom/go-mssqldb"
	"sphere-fx-manager-api/go_workers/live_worker/config"
)

var (
	db *sql.DB
)

// InitDB initializes the database connection pool.
func InitDB(cfg *config.Config) error {
	// Build connection string
	// We assume the standard SQL Server connection string format
	connStr := fmt.Sprintf(
		"server=%s;user id=%s;password=%s;database=%s;port=%d;encrypt=disable",
		cfg.DBHost, cfg.DBUser, cfg.DBPassword, cfg.DBName, cfg.DBPort,
	)

	// If we have a full URL, use it directly (override)
	if fullURL := cfg.DBURL; fullURL != "" {
		connStr = fullURL
	}

	var err error
	db, err = sql.Open("sqlserver", connStr)
	if err != nil {
		return fmt.Errorf("failed to open DB: %w", err)
	}

	db.SetMaxOpenConns(cfg.DBMaxOpenConns)
	db.SetMaxIdleConns(cfg.DBMaxIdleConns)
	db.SetConnMaxLifetime(cfg.DBConnMaxLifetime)

	// Ping to verify connection
	if err := db.Ping(); err != nil {
		return fmt.Errorf("failed to ping DB: %w", err)
	}

	log.Println("Database connection established")
	return nil
}

// GetDB returns the database connection pool.
func GetDB() *sql.DB {
	return db
}

// CloseDB closes the database connection pool.
func CloseDB() error {
	if db != nil {
		return db.Close()
	}
	return nil
}

// Job represents a row from the live_jobs table.
type Job struct {
	ID        string
	SignalID  int64
	AccountID int64
	UserID    int64
	LotSize   float64
	Status    string
	Payload   []byte // JSON
	Result    []byte // JSON
	ClaimedAt *time.Time
	StartedAt *time.Time
	FinishedAt *time.Time
	CreatedAt time.Time
	UpdatedAt *time.Time
}

// ClaimNextJob atomically claims the next PENDING job using ROWLOCK, READPAST.
func ClaimNextJob() (*Job, error) {
	tx, err := db.Begin()
	if err != nil {
		return nil, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	// Use WITH (UPDLOCK, READPAST) to atomically select and lock a row
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
	var resultBytes, payloadBytes []byte

	err = row.Scan(
		&job.ID, &job.SignalID, &job.AccountID, &job.UserID,
		&job.LotSize, &job.Status,
		&payloadBytes, &resultBytes,
		&claimedAt, &startedAt, &finishedAt,
		&job.CreatedAt, &updatedAt,
	)
	if err == sql.ErrNoRows {
		return nil, nil // no pending jobs
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

	// Mark as CLAIMED
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

// UpdateJobStatus updates the job status and result.
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

// GetSignalData retrieves the full signal details for a signal ID.
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
	var takeProfit []byte // JSON
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
