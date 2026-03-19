package handlers

import (
	_ "embed"
	"net/http"
)

var categoriesJSON []byte

type CategoriesHandler struct{}

func NewCategoriesHandler() *CategoriesHandler {
	return &CategoriesHandler{}
}

func (h *CategoriesHandler) List(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "public, max-age=86400")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(categoriesJSON)
}
