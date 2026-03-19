package commerce

import (
	"crypto/sha256"
	"fmt"
	"math"
	"sort"
	"strings"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

const (
	bboxPrecision = 5
	keyPrefix     = "geo"
	hashLen       = 12
)

func BuildCacheKey(bbox models.BBox, cats []models.Category) string {
	bboxStr := fmt.Sprintf("%.5f,%.5f,%.5f,%.5f",
		truncate(bbox.South),
		truncate(bbox.West),
		truncate(bbox.North),
		truncate(bbox.East),
	)

	catParts := make([]string, len(cats))
	for i, c := range cats {
		catParts[i] = c.Key + "=" + c.Value
	}
	sort.Strings(catParts)
	catsStr := strings.Join(catParts, ",")

	return fmt.Sprintf("%s:%s:%s", keyPrefix, hashStr(bboxStr), hashStr(catsStr))
}

func truncate(f float64) float64 {
	factor := math.Pow(10, bboxPrecision)
	return math.Trunc(f*factor) / factor
}

func hashStr(s string) string {
	h := sha256.Sum256([]byte(s))
	return fmt.Sprintf("%x", h[:])[:hashLen]
}
