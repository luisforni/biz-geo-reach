package cache

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/luisforni/geo-finder-api/internal/commerce"
	"github.com/luisforni/geo-finder-api/pkg/models"
)

type RedisCache struct {
	client *redis.Client
}

func NewRedisCache(client *redis.Client) *RedisCache {
	return &RedisCache{client: client}
}

func (c *RedisCache) Get(ctx context.Context, key string) ([]models.Commerce, error) {
	data, err := c.client.Get(ctx, key).Bytes()
	if errors.Is(err, redis.Nil) {
		return nil, commerce.ErrCacheMiss
	}
	if err != nil {
		return nil, fmt.Errorf("redis GET %q: %w", key, err)
	}

	var items []models.Commerce
	if err := json.Unmarshal(data, &items); err != nil {
		return nil, fmt.Errorf("unmarshal cache value for %q: %w", key, err)
	}
	return items, nil
}

func (c *RedisCache) Set(ctx context.Context, key string, items []models.Commerce, ttl time.Duration) error {
	data, err := json.Marshal(items)
	if err != nil {
		return fmt.Errorf("marshal cache value for %q: %w", key, err)
	}
	if err := c.client.Set(ctx, key, data, ttl).Err(); err != nil {
		return fmt.Errorf("redis SET %q: %w", key, err)
	}
	return nil
}
