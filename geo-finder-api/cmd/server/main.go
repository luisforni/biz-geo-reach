package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/luisforni/geo-finder-api/internal/cache"
	"github.com/luisforni/geo-finder-api/internal/commerce"
	"github.com/luisforni/geo-finder-api/internal/config"
	"github.com/luisforni/geo-finder-api/internal/gateway"
	"github.com/luisforni/geo-finder-api/internal/gateway/handlers"
	"github.com/luisforni/geo-finder-api/internal/geo"
	"github.com/luisforni/geo-finder-api/internal/overpass"
)

func main() {
	log, _ := zap.NewProduction()
	defer log.Sync()

	if err := run(log); err != nil {
		log.Fatal("server error", zap.Error(err))
		os.Exit(1)
	}
}

func run(log *zap.Logger) error {
	cfg, err := config.Load()
	if err != nil {
		return fmt.Errorf("load config: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		return fmt.Errorf("connect postgres: %w", err)
	}
	defer pool.Close()

	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("ping postgres: %w", err)
	}
	log.Info("connected to postgres")

	redisOpts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		return fmt.Errorf("parse redis URL: %w", err)
	}
	redisClient := redis.NewClient(redisOpts)
	defer redisClient.Close()

	if err := redisClient.Ping(context.Background()).Err(); err != nil {
		return fmt.Errorf("ping redis: %w", err)
	}
	log.Info("connected to redis")

	repo := geo.NewPostGISRepository(pool)
	redisCache := cache.NewRedisCache(redisClient)
	overpassClient := overpass.NewClient(cfg.OverpassURL, log)
	commerceSvc := commerce.NewService(repo, redisCache, overpassClient, cfg.CacheTTL, log)

	commerceHandler := handlers.NewCommerceHandler(commerceSvc, log)
	categoriesHandler := handlers.NewCategoriesHandler()

	router := gateway.NewRouter(commerceHandler, categoriesHandler, cfg.RateLimit)

	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 35 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		log.Info("server listening", zap.String("addr", srv.Addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- err
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	select {
	case err := <-errCh:
		return err
	case sig := <-quit:
		log.Info("shutdown signal received", zap.String("signal", sig.String()))
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()
	return srv.Shutdown(shutdownCtx)
}
