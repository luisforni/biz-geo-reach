package commerce

import (
	"context"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

type Repository interface {
	FindByBBox(ctx context.Context, bbox models.BBox, cats []models.Category) ([]models.Commerce, error)

	Save(ctx context.Context, items []models.Commerce) error

	IsBBoxFetched(ctx context.Context, bbox models.BBox, cats []models.Category) (bool, error)

	MarkBBoxFetched(ctx context.Context, bbox models.BBox, cats []models.Category) error
}
