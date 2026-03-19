package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Port        string
	DatabaseURL string
	RedisURL    string
	OverpassURL string
	RateLimit   int
	CacheTTL    time.Duration
}

func Load() (*Config, error) {
	cfg := &Config{
		Port:        getEnv("PORT", "8080"),
		OverpassURL: getEnv("OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
	}

	cfg.DatabaseURL = os.Getenv("DATABASE_URL")
	if cfg.DatabaseURL == "" {
		return nil, fmt.Errorf("DATABASE_URL is required")
	}

	cfg.RedisURL = os.Getenv("REDIS_URL")
	if cfg.RedisURL == "" {
		return nil, fmt.Errorf("REDIS_URL is required")
	}

	rpmStr := getEnv("RATE_LIMIT_RPM", "60")
	rpm, err := strconv.Atoi(rpmStr)
	if err != nil || rpm <= 0 {
		return nil, fmt.Errorf("RATE_LIMIT_RPM must be a positive integer, got: %q", rpmStr)
	}
	cfg.RateLimit = rpm

	ttlStr := getEnv("CACHE_TTL", "1h")
	ttl, err := time.ParseDuration(ttlStr)
	if err != nil || ttl <= 0 {
		return nil, fmt.Errorf("CACHE_TTL must be a valid positive duration, got: %q", ttlStr)
	}
	cfg.CacheTTL = ttl

	return cfg, nil
}

func getEnv(key, defaultValue string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultValue
}
