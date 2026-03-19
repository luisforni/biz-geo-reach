package overpass

import (
	"encoding/json"
	"fmt"

	"github.com/luisforni/geo-finder-api/pkg/models"
)

type overpassResponse struct {
	Elements []overpassElement `json:"elements"`
}

type overpassElement struct {
	Type   string            `json:"type"`
	ID     int64             `json:"id"`
	Lat    float64           `json:"lat"`
	Lon    float64           `json:"lon"`
	Center *latLon           `json:"center"`
	Tags   map[string]string `json:"tags"`
}

type latLon struct {
	Lat float64 `json:"lat"`
	Lon float64 `json:"lon"`
}

func ParseResponse(data []byte) ([]models.Commerce, error) {
	var resp overpassResponse
	if err := json.Unmarshal(data, &resp); err != nil {
		return nil, fmt.Errorf("parse overpass response: %w", err)
	}

	items := make([]models.Commerce, 0, len(resp.Elements))
	for _, el := range resp.Elements {
		lat, lon, ok := resolveCoords(el)
		if !ok {
			continue
		}

		cat, sub := resolveCategory(el.Tags)
		if cat == "" {
			continue
		}

		items = append(items, models.Commerce{
			OsmID:       el.ID,
			Name:        el.Tags["name"],
			Category:    cat,
			Subcategory: sub,
			Tags:        el.Tags,
			Lat:         lat,
			Lon:         lon,
		})
	}
	return items, nil
}

func resolveCoords(el overpassElement) (lat, lon float64, ok bool) {
	if el.Type == "node" && (el.Lat != 0 || el.Lon != 0) {
		return el.Lat, el.Lon, true
	}
	if el.Center != nil {
		return el.Center.Lat, el.Center.Lon, true
	}
	return 0, 0, false
}

func resolveCategory(tags map[string]string) (cat, sub string) {
	priority := []string{"amenity", "shop", "tourism", "leisure", "office"}
	for _, key := range priority {
		if v, ok := tags[key]; ok && v != "" {
			return key, v
		}
	}
	return "", ""
}
