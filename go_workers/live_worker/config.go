package main

import (
	"log"
	"os"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	// Database connection
	DBDriver          string
	DBHost            string
	DBPort            int
	DBUser            string
	DBPassword        string
	DBName            string
	DBMaxOpenConns    int
	DBMaxIdleConns    int
	DBConnMaxLifetime time.Duration

	// Queue polling
	PollIntervalSeconds int
	MaxClaimAttempts    int

	// MT5 Bridge
	MT5BridgeURL string
	MT5Timeout   time.Duration

	// Risk defaults (can be overridden per job)
	DefaultMaxLot           float64
	DefaultMinLot           float64
	DefaultMaxDailyDrawdown float64
	DefaultMinRR            float64
	DefaultMaxPositions     int

	// Logging
	LogLevel string
}

func LoadConfig() *Config {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("/app/config")
	viper.AddConfigPath(".")

	if err := viper.ReadInConfig(); err != nil {
		log.Printf("Warning: config file not found, using defaults: %v", err)
	}

	// Defaults
	viper.SetDefault("live_worker.poll_interval_seconds", 2)
	viper.SetDefault("live_worker.max_claim_attempts", 3)
	viper.SetDefault("live_worker.mt5_timeout_seconds", 10)
	viper.SetDefault("live_worker.max_open_conns", 10)
	viper.SetDefault("live_worker.max_idle_conns", 5)
	viper.SetDefault("live_worker.conn_max_lifetime_minutes", 30)

	// Risk defaults (fallback)
	viper.SetDefault("risk_limits.max_lot", 100.0)
	viper.SetDefault("risk_limits.min_lot", 0.01)
	viper.SetDefault("risk_limits.max_daily_drawdown_percent", 5.0)
	viper.SetDefault("risk_limits.min_rr_ratio", 1.5)
	viper.SetDefault("risk_limits.max_positions", 10)

	// Override from env
	if url := os.Getenv("MT5_BRIDGE_URL"); url != "" {
		viper.Set("live_worker.mt5_bridge_url", url)
	}
	if dbURL := os.Getenv("DATABASE_URL"); dbURL != "" {
		// We could parse the URL, but we'll use standard env vars for simplicity
	}
	// Fallback env vars for DB
	if host := os.Getenv("DB_HOST"); host != "" {
		viper.Set("live_worker.db_host", host)
	}
	if user := os.Getenv("DB_USER"); user != "" {
		viper.Set("live_worker.db_user", user)
	}
	if password := os.Getenv("DB_PASSWORD"); password != "" {
		viper.Set("live_worker.db_password", password)
	}
	if dbname := os.Getenv("DB_NAME"); dbname != "" {
		viper.Set("live_worker.db_name", dbname)
	}
	if port := os.Getenv("DB_PORT"); port != "" {
		viper.Set("live_worker.db_port", port)
	}

	cfg := &Config{
		PollIntervalSeconds: viper.GetInt("live_worker.poll_interval_seconds"),
		MaxClaimAttempts:    viper.GetInt("live_worker.max_claim_attempts"),
		MT5BridgeURL:        viper.GetString("live_worker.mt5_bridge_url"),
		MT5Timeout:          time.Duration(viper.GetInt("live_worker.mt5_timeout_seconds")) * time.Second,
		DBMaxOpenConns:      viper.GetInt("live_worker.max_open_conns"),
		DBMaxIdleConns:      viper.GetInt("live_worker.max_idle_conns"),
		DBConnMaxLifetime:   time.Duration(viper.GetInt("live_worker.conn_max_lifetime_minutes")) * time.Minute,
		DefaultMaxLot:       viper.GetFloat64("risk_limits.max_lot"),
		DefaultMinLot:       viper.GetFloat64("risk_limits.min_lot"),
		DefaultMaxDailyDrawdown: viper.GetFloat64("risk_limits.max_daily_drawdown_percent"),
		DefaultMinRR:        viper.GetFloat64("risk_limits.min_rr_ratio"),
		DefaultMaxPositions: viper.GetInt("risk_limits.max_positions"),
		LogLevel:            viper.GetString("live_worker.log_level"),
	}

	// Ensure required fields
	if cfg.MT5BridgeURL == "" {
		log.Fatal("MT5_BRIDGE_URL must be set (env or config)")
	}

	return cfg
}
