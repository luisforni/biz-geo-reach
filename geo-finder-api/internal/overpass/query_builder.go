package overpass

import (
	"fmt"
	"strings"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

var defaultKeys = []string{"amenity", "shop", "tourism", "leisure", "office"}

func BuildQuery(bbox models.BBox, cats []models.Category) string {
	bboxStr := fmt.Sprintf("%.6f,%.6f,%.6f,%.6f",
		bbox.South, bbox.West, bbox.North, bbox.East)

	var lines []string
	if len(cats) == 0 {
		for _, key := range defaultKeys {
			lines = append(lines, nodeWayLines(key, "", bboxStr)...)
		}
	} else {
		seen := map[string]bool{}
		for _, cat := range cats {
			tag := tagFilter(cat)
			if seen[tag] {
				continue
			}
			seen[tag] = true
			lines = append(lines, nodeWayLines(cat.Key, cat.Value, bboxStr)...)
		}
	}

	return fmt.Sprintf("[out:json][timeout:25];\n(\n%s\n);\nout body center;",
		strings.Join(lines, "\n"))
}

func nodeWayLines(key, value, bboxStr string) []string {
	filter := tagFilter(models.Category{Key: key, Value: value})
	return []string{
		fmt.Sprintf("  node[%s](%s);", filter, bboxStr),
		fmt.Sprintf("  way[%s](%s);", filter, bboxStr),
	}
}

func tagFilter(cat models.Category) string {
	if cat.Value == "" {
		return fmt.Sprintf("%q", cat.Key)
	}
	return fmt.Sprintf("%q=%q", cat.Key, cat.Value)
}
