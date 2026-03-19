package overpass

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/sony/gobreaker"
	"go.uber.org/zap"
	"golang.org/x/time/rate"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

var ErrRateLimited = fmt.Errorf("overpass rate limit exceeded")

var ErrCircuitOpen = fmt.Errorf("overpass circuit breaker open")

type Client struct {
	httpClient *http.Client
	baseURL    string
	limiter    *rate.Limiter
	breaker    *gobreaker.CircuitBreaker
	log        *zap.Logger
}

func NewClient(baseURL string, log *zap.Logger) *Client {
	cb := gobreaker.NewCircuitBreaker(gobreaker.Settings{
		Name:        "overpass",
		MaxRequests: 1,
		Interval:    60 * time.Second,
		Timeout:     60 * time.Second,
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			return counts.ConsecutiveFailures >= 5
		},
		OnStateChange: func(name string, from, to gobreaker.State) {
			log.Warn("circuit breaker state change",
				zap.String("name", name),
				zap.String("from", from.String()),
				zap.String("to", to.String()),
			)
		},
	})

	return &Client{
		httpClient: &http.Client{Timeout: 30 * time.Second},
		baseURL:    baseURL,
		limiter:    rate.NewLimiter(rate.Every(time.Second), 1),
		breaker:    cb,
		log:        log,
	}
}

func (c *Client) Fetch(ctx context.Context, req models.SearchRequest) ([]models.Commerce, error) {
	if !c.limiter.Allow() {
		if err := c.limiter.Wait(ctx); err != nil {
			return nil, ErrRateLimited
		}
	}

	query := BuildQuery(req.BBox, req.Categories)

	result, err := c.breaker.Execute(func() (interface{}, error) {
		return c.do(ctx, query)
	})
	if err != nil {
		if err == gobreaker.ErrOpenState || err == gobreaker.ErrTooManyRequests {
			return nil, ErrCircuitOpen
		}
		return nil, fmt.Errorf("overpass fetch: %w", err)
	}

	return result.([]models.Commerce), nil
}

func (c *Client) do(ctx context.Context, query string) ([]models.Commerce, error) {
	body := url.Values{}
	body.Set("data", query)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL,
		strings.NewReader(body.Encode()))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("User-Agent", "biz-geo-reach/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("overpass returned HTTP %d", resp.StatusCode)
	}

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response body: %w", err)
	}

	items, err := ParseResponse(data)
	if err != nil {
		return nil, err
	}

	c.log.Debug("overpass response", zap.Int("elements", len(items)))
	return items, nil
}
