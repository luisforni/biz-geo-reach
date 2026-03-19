package models

type BBox struct {
	South float64 `json:"south"`
	West  float64 `json:"west"`
	North float64 `json:"north"`
	East  float64 `json:"east"`
}

func (b BBox) Area() float64 {
	return (b.North - b.South) * (b.East - b.West)
}

type Category struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

type Commerce struct {
	ID          int64             `json:"id"`
	OsmID       int64             `json:"osmId"`
	Name        string            `json:"name"`
	Category    string            `json:"category"`
	Subcategory string            `json:"subcategory"`
	Tags        map[string]string `json:"tags"`
	Lat         float64           `json:"lat"`
	Lon         float64           `json:"lon"`
}

type SearchRequest struct {
	BBox       BBox       `json:"bbox"`
	Categories []Category `json:"categories"`
}

type SearchResponse struct {
	Items  []Commerce `json:"items"`
	Source string     `json:"source"`
	Count  int        `json:"count"`
}

type CategoryGroup struct {
	Key    string   `json:"key"`
	Label  string   `json:"label"`
	Values []string `json:"values"`
}
