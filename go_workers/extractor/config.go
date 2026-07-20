package main

import (
    "log"
    "os"
    //"strconv"

    "github.com/spf13/viper"
)

type Config struct {
    GRPCPort    string
    PatternsDir string
    LogLevel    string
}

func LoadConfig() *Config {
    viper.SetConfigName("config")
    viper.SetConfigType("yaml")
    viper.AddConfigPath("/app/config")   // Docker path
    viper.AddConfigPath(".")             // fallback

    if err := viper.ReadInConfig(); err != nil {
        log.Printf("Warning: config file not found, using env defaults: %v", err)
    }

    viper.SetDefault("extractor.grpc_port", "50051")
    viper.SetDefault("extractor.patterns_dir", "/app/config/patterns")
    viper.SetDefault("extractor.log_level", "info")

    // Allow environment override
    if port := os.Getenv("EXTRACTOR_GRPC_PORT"); port != "" {
        viper.Set("extractor.grpc_port", port)
    }

    cfg := &Config{
        GRPCPort:    viper.GetString("extractor.grpc_port"),
        PatternsDir: viper.GetString("extractor.patterns_dir"),
        LogLevel:    viper.GetString("extractor.log_level"),
    }

    return cfg
}
