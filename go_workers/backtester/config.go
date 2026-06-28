package config

import (
    "log"
    "os"
    "strconv"
    "time"

    "github.com/spf13/viper"
)

type Config struct {
    GRPCPort           string
    LogLevel           string
    DefaultRR          float64
    SpreadPips         float64
    CommissionPerLot   float64
    MinDataPoints      int
    MaxDurationHours   int
    DefaultTPStrategy  string
    SlippageModel      string
    CacheTTLSeconds    int
}

func LoadConfig() *Config {
    viper.SetConfigName("config")
    viper.SetConfigType("yaml")
    viper.AddConfigPath("/app/config")
    viper.AddConfigPath(".")

    if err := viper.ReadInConfig(); err != nil {
        log.Printf("Warning: config file not found, using defaults: %v", err)
    }

    // Set defaults
    viper.SetDefault("backtester.grpc_port", "50052")
    viper.SetDefault("backtester.log_level", "info")
    viper.SetDefault("backtester.default_rr", 2.0)
    viper.SetDefault("backtester.spread_pips", 1.5)
    viper.SetDefault("backtester.commission_per_lot", 3.5)
    viper.SetDefault("backtester.min_data_points", 100)
    viper.SetDefault("backtester.max_duration_hours", 200)
    viper.SetDefault("backtester.default_tp_strategy", "sequential")
    viper.SetDefault("backtester.slippage_model", "fixed")
    viper.SetDefault("backtester.cache_ttl_seconds", 3600)

    // Environment override
    if port := os.Getenv("BACKTESTER_GRPC_PORT"); port != "" {
        viper.Set("backtester.grpc_port", port)
    }

    return &Config{
        GRPCPort:          viper.GetString("backtester.grpc_port"),
        LogLevel:          viper.GetString("backtester.log_level"),
        DefaultRR:         viper.GetFloat64("backtester.default_rr"),
        SpreadPips:        viper.GetFloat64("backtester.spread_pips"),
        CommissionPerLot:  viper.GetFloat64("backtester.commission_per_lot"),
        MinDataPoints:     viper.GetInt("backtester.min_data_points"),
        MaxDurationHours:  viper.GetInt("backtester.max_duration_hours"),
        DefaultTPStrategy: viper.GetString("backtester.default_tp_strategy"),
        SlippageModel:     viper.GetString("backtester.slippage_model"),
        CacheTTLSeconds:   viper.GetInt("backtester.cache_ttl_seconds"),
    }
}