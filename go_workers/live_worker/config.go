package main

import (
    "log"
    "os"
    "time"

    "github.com/joho/godotenv"
    "github.com/spf13/viper"
)

type Config struct {
    DBURL          string
    MT5BridgeURL   string
    PollIntervalSeconds int
    MaxClaimAttempts    int
    MT5Timeout          time.Duration
    DBMaxOpenConns      int
    DBMaxIdleConns      int
    DBConnMaxLifetime   time.Duration
    DefaultMaxLot           float64
    DefaultMinLot           float64
    DefaultMaxDailyDrawdown float64
    DefaultMinRR            float64
    DefaultMaxPositions     int
    LogLevel                string
}

func LoadConfig() *Config {
    // Load .env file (same as FastAPI uses)
    if err := godotenv.Load(); err != nil {
        log.Println("Warning: .env file not found, using environment variables")
    }

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

    viper.SetDefault("risk_limits.max_lot", 100.0)
    viper.SetDefault("risk_limits.min_lot", 0.01)
    viper.SetDefault("risk_limits.max_daily_drawdown_percent", 5.0)
    viper.SetDefault("risk_limits.min_rr_ratio", 1.5)
    viper.SetDefault("risk_limits.max_positions", 10)

    cfg := &Config{
        // Read from environment first (via .env), fallback to config
        DBURL:                  getEnv("DATABASE_URL", ""),
        MT5BridgeURL:           getEnv("MT5_BRIDGE_URL", viper.GetString("live_worker.mt5_bridge_url")),
        PollIntervalSeconds:    viper.GetInt("live_worker.poll_interval_seconds"),
        MaxClaimAttempts:       viper.GetInt("live_worker.max_claim_attempts"),
        MT5Timeout:             time.Duration(viper.GetInt("live_worker.mt5_timeout_seconds")) * time.Second,
        DBMaxOpenConns:         viper.GetInt("live_worker.max_open_conns"),
        DBMaxIdleConns:         viper.GetInt("live_worker.max_idle_conns"),
        DBConnMaxLifetime:      time.Duration(viper.GetInt("live_worker.conn_max_lifetime_minutes")) * time.Minute,
        DefaultMaxLot:          viper.GetFloat64("risk_limits.max_lot"),
        DefaultMinLot:          viper.GetFloat64("risk_limits.min_lot"),
        DefaultMaxDailyDrawdown: viper.GetFloat64("risk_limits.max_daily_drawdown_percent"),
        DefaultMinRR:           viper.GetFloat64("risk_limits.min_rr_ratio"),
        DefaultMaxPositions:    viper.GetInt("risk_limits.max_positions"),
        LogLevel:               viper.GetString("live_worker.log_level"),
    }

    if cfg.DBURL == "" {
        log.Fatal("DATABASE_URL must be set in .env")
    }
    if cfg.MT5BridgeURL == "" {
        log.Fatal("MT5_BRIDGE_URL must be set in .env or config")
    }

    return cfg
}

func getEnv(key, fallback string) string {
    if value, exists := os.LookupEnv(key); exists && value != "" {
        return value
    }
    return fallback
}