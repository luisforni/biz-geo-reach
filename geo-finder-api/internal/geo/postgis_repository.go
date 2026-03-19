package geo

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

type PostGISRepository struct {
	pool *pgxpool.Pool
}

func NewPostGISRepository(pool *pgxpool.Pool) *PostGISRepository {
	return &PostGISRepository{pool: pool}
}

func (r *PostGISRepository) FindByBBox(ctx context.Context, bbox models.BBox, cats []models.Category) ([]models.Commerce, error) {
	query := `
		SELECT id, osm_id, COALESCE(name, ''), category, subcategory, tags,
		       ST_Y(location::geometry) AS lat,
		       ST_X(location::geometry) AS lon
		FROM   commerce
		WHERE  ST_Within(location::geometry, ST_MakeEnvelope($1, $2, $3, $4, 4326))
	`
	args := []any{bbox.West, bbox.South, bbox.East, bbox.North}

	if len(cats) > 0 {
		pairs := make([]string, len(cats))
		for i, c := range cats {
			keyIdx := len(args) + 1
			valIdx := len(args) + 2
			pairs[i] = fmt.Sprintf("(category = $%d AND subcategory = $%d)", keyIdx, valIdx)
			args = append(args, c.Key, c.Value)
		}
		query += ` AND (` + strings.Join(pairs, " OR ") + `)`
	}

	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("FindByBBox query: %w", err)
	}
	defer rows.Close()

	return scanCommerce(rows)
}

func (r *PostGISRepository) Save(ctx context.Context, items []models.Commerce) error {
	if len(items) == 0 {
		return nil
	}

	batch := &pgx.Batch{}
	for _, c := range items {
		tagsJSON, err := json.Marshal(c.Tags)
		if err != nil {
			return fmt.Errorf("marshal tags for osm_id %d: %w", c.OsmID, err)
		}
		batch.Queue(`
			INSERT INTO commerce (osm_id, name, category, subcategory, tags, location)
			VALUES ($1, $2, $3, $4, $5, ST_SetSRID(ST_MakePoint($6, $7), 4326))
			ON CONFLICT (osm_id) DO UPDATE
			    SET name        = EXCLUDED.name,
			        category    = EXCLUDED.category,
			        subcategory = EXCLUDED.subcategory,
			        tags        = EXCLUDED.tags,
			        updated_at  = NOW()
		`, c.OsmID, c.Name, c.Category, c.Subcategory, tagsJSON, c.Lon, c.Lat)
	}

	br := r.pool.SendBatch(ctx, batch)
	defer br.Close()

	for i := range items {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("upsert item %d: %w", i, err)
		}
	}
	return nil
}

func (r *PostGISRepository) IsBBoxFetched(ctx context.Context, bbox models.BBox, cats []models.Category) (bool, error) {
	catKeys := categoryKeys(cats)

	var exists bool
	err := r.pool.QueryRow(ctx, `
		SELECT EXISTS (
			SELECT 1 FROM fetched_areas
			WHERE  categories @> $1
			AND    ST_Covers(bbox, ST_MakeEnvelope($2, $3, $4, $5, 4326))
		)
	`, catKeys, bbox.West, bbox.South, bbox.East, bbox.North).Scan(&exists)
	if err != nil {
		return false, fmt.Errorf("IsBBoxFetched: %w", err)
	}
	return exists, nil
}

func (r *PostGISRepository) MarkBBoxFetched(ctx context.Context, bbox models.BBox, cats []models.Category) error {
	catKeys := categoryKeys(cats)
	_, err := r.pool.Exec(ctx, `
		INSERT INTO fetched_areas (bbox, categories)
		VALUES (ST_MakeEnvelope($1, $2, $3, $4, 4326), $5)
	`, bbox.West, bbox.South, bbox.East, bbox.North, catKeys)
	if err != nil {
		return fmt.Errorf("MarkBBoxFetched: %w", err)
	}
	return nil
}

func scanCommerce(rows pgx.Rows) ([]models.Commerce, error) {
	var items []models.Commerce
	for rows.Next() {
		var c models.Commerce
		var tagsJSON []byte
		if err := rows.Scan(&c.ID, &c.OsmID, &c.Name, &c.Category, &c.Subcategory, &tagsJSON, &c.Lat, &c.Lon); err != nil {
			return nil, fmt.Errorf("scan commerce row: %w", err)
		}
		if len(tagsJSON) > 0 {
			if err := json.Unmarshal(tagsJSON, &c.Tags); err != nil {
				return nil, fmt.Errorf("unmarshal tags: %w", err)
			}
		}
		items = append(items, c)
	}
	return items, rows.Err()
}

func categoryKeys(cats []models.Category) []string {
	if len(cats) == 0 {
		return []string{}
	}
	keys := make([]string, 0, len(cats))
	for _, c := range cats {
		keys = append(keys, c.Key)
	}
	return keys
}
