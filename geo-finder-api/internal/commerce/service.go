package commerce

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.uber.org/zap"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

type OverpassFetcher interface {
	Fetch(ctx context.Context, req models.SearchRequest) ([]models.Commerce, error)
}

type Cache interface {
	Get(ctx context.Context, key string) ([]models.Commerce, error)
	Set(ctx context.Context, key string, items []models.Commerce, ttl time.Duration) error
}

var ErrCacheMiss = errors.New("cache miss")

type Service interface {
	Search(ctx context.Context, req models.SearchRequest) (models.SearchResponse, error)
}

type service struct {
	repo     Repository
	cache    Cache
	overpass OverpassFetcher
	ttl      time.Duration
	log      *zap.Logger
}

func NewService(repo Repository, cache Cache, overpass OverpassFetcher, ttl time.Duration, log *zap.Logger) Service {
	return &service{
		repo:     repo,
		cache:    cache,
		overpass: overpass,
		ttl:      ttl,
		log:      log,
	}
}

func (s *service) Search(ctx context.Context, req models.SearchRequest) (models.SearchResponse, error) {
	key := BuildCacheKey(req.BBox, req.Categories)

	if items, err := s.cache.Get(ctx, key); err == nil {
		s.log.Debug("cache hit", zap.String("key", key))
		return models.SearchResponse{Items: items, Source: "cache", Count: len(items)}, nil
	}

	fetched, err := s.repo.IsBBoxFetched(ctx, req.BBox, req.Categories)
	if err != nil {
		s.log.Warn("IsBBoxFetched error", zap.Error(err))
	}

	if fetched {
		items, dbErr := s.repo.FindByBBox(ctx, req.BBox, req.Categories)
		if dbErr != nil {
			return models.SearchResponse{}, fmt.Errorf("db query: %w", dbErr)
		}
		_ = s.cache.Set(ctx, key, items, s.ttl)
		s.log.Debug("db hit", zap.Int("count", len(items)))
		return models.SearchResponse{Items: items, Source: "db", Count: len(items)}, nil
	}

	items, overpassErr := s.overpass.Fetch(ctx, req)
	if overpassErr != nil {
		s.log.Warn("overpass fetch failed, falling back to db", zap.Error(overpassErr))
		partial, dbErr := s.repo.FindByBBox(ctx, req.BBox, req.Categories)
		if dbErr == nil && len(partial) > 0 {
			return models.SearchResponse{Items: partial, Source: "db", Count: len(partial)}, nil
		}
		return models.SearchResponse{}, fmt.Errorf("overpass fetch: %w", overpassErr)
	}

	if saveErr := s.repo.Save(ctx, items); saveErr != nil {
		s.log.Warn("failed to persist commerce items", zap.Error(saveErr))
	}
	if markErr := s.repo.MarkBBoxFetched(ctx, req.BBox, req.Categories); markErr != nil {
		s.log.Warn("failed to mark bbox as fetched", zap.Error(markErr))
	}
	_ = s.cache.Set(ctx, key, items, s.ttl)

	s.log.Info("overpass fetch success", zap.Int("count", len(items)))
	return models.SearchResponse{Items: items, Source: "overpass", Count: len(items)}, nil
}
