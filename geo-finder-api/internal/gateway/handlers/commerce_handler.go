package handlers

import (
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net/http"

	"go.uber.org/zap"

	"github.com/luisforni/geo-finder-api/internal/commerce"
	"github.com/luisforni/geo-finder-api/internal/overpass"
	"github.com/luisforni/geo-finder-api/pkg/models"
)

const maxBBoxAreaDegrees = 1.0

type CommerceHandler struct {
	service commerce.Service
	log     *zap.Logger
}

func NewCommerceHandler(svc commerce.Service, log *zap.Logger) *CommerceHandler {
	return &CommerceHandler{service: svc, log: log}
}

func (h *CommerceHandler) Search(w http.ResponseWriter, r *http.Request) {
	var req models.SearchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	if err := validateSearchRequest(req); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	resp, err := h.service.Search(r.Context(), req)
	if err != nil {
		h.log.Warn("search error", zap.Error(err))
		switch {
		case errors.Is(err, overpass.ErrRateLimited):
			w.Header().Set("Retry-After", "1")
			respondError(w, http.StatusTooManyRequests, "rate limit exceeded, try again shortly")
		case errors.Is(err, overpass.ErrCircuitOpen):
			respondError(w, http.StatusServiceUnavailable, "Overpass API temporarily unavailable")
		default:
			respondError(w, http.StatusInternalServerError, "internal error")
		}
		return
	}

	w.Header().Set("X-Source", resp.Source)
	respondJSON(w, http.StatusOK, resp)
}

func validateSearchRequest(req models.SearchRequest) error {
	b := req.BBox
	if math.IsNaN(b.South) || math.IsNaN(b.North) || math.IsNaN(b.West) || math.IsNaN(b.East) {
		return fmt.Errorf("bbox coordinates must be finite numbers")
	}
	if b.South >= b.North {
		return fmt.Errorf("bbox.south must be less than bbox.north")
	}
	if b.West >= b.East {
		return fmt.Errorf("bbox.west must be less than bbox.east")
	}
	if b.South < -90 || b.North > 90 || b.West < -180 || b.East > 180 {
		return fmt.Errorf("bbox coordinates out of valid geographic range")
	}
	if b.Area() > maxBBoxAreaDegrees {
		return fmt.Errorf("bbox area exceeds maximum of %.1f square degrees", maxBBoxAreaDegrees)
	}
	return nil
}

func respondJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func respondError(w http.ResponseWriter, status int, msg string) {
	respondJSON(w, status, map[string]string{"error": msg})
}
