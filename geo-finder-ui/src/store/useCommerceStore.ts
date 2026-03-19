import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { BBox, Category, Commerce } from "@/types";

interface CommerceState {
  bbox: BBox | null;
  selectedCategories: Category[];
  results: Commerce[];
  isLoading: boolean;
  isDrawing: boolean;
  focusedOsmId: number | null;
  filterPhone: boolean;
  filterWebsite: boolean;
  neighborhoodPolygon: object | null;
  neighborhoodName: string | null;
  drawnPolygon: [number, number][] | null;
  showCampaignPanel: boolean;
  showCampaignsManager: boolean;
  campaignContacts: Commerce[];
}

interface CommerceActions {
  setBBox: (bbox: BBox | null) => void;
  setSelectedCategories: (categories: Category[]) => void;
  setResults: (items: Commerce[]) => void;
  setIsLoading: (loading: boolean) => void;
  setIsDrawing: (drawing: boolean) => void;
  focusMarker: (osmId: number | null) => void;
  clearResults: () => void;
  toggleFilterPhone: () => void;
  toggleFilterWebsite: () => void;
  setNeighborhood: (polygon: object, bbox: BBox, name: string) => void;
  clearNeighborhood: () => void;
  setDrawnPolygon: (points: [number, number][], bbox: BBox) => void;
  openCampaignPanel: (items: Commerce[]) => void;
  setShowCampaignPanel: (show: boolean) => void;
  openCampaignsManager: () => void;
  setShowCampaignsManager: (show: boolean) => void;
}

type CommerceStore = CommerceState & CommerceActions;

export const useCommerceStore = create<CommerceStore>()(
  devtools(
    (set) => ({
      bbox: null,
      selectedCategories: [],
      results: [],
      isLoading: false,
      isDrawing: false,
      focusedOsmId: null,
      filterPhone: false,
      filterWebsite: false,
      neighborhoodPolygon: null,
      neighborhoodName: null,
      drawnPolygon: null,
      showCampaignPanel: false,
      showCampaignsManager: false,
      campaignContacts: [],

      setBBox: (bbox) =>
        set(
          { bbox, results: [], neighborhoodPolygon: null, neighborhoodName: null, drawnPolygon: null },
          false,
          "setBBox",
        ),
      setSelectedCategories: (selectedCategories) =>
        set({ selectedCategories }, false, "setSelectedCategories"),
      setResults: (results) => set({ results }, false, "setResults"),
      setIsLoading: (isLoading) =>
        set({ isLoading }, false, "setIsLoading"),
      setIsDrawing: (isDrawing) =>
        set({ isDrawing }, false, "setIsDrawing"),
      focusMarker: (focusedOsmId) =>
        set({ focusedOsmId }, false, "focusMarker"),
      clearResults: () =>
        set(
          { results: [], bbox: null, neighborhoodPolygon: null, neighborhoodName: null, drawnPolygon: null },
          false,
          "clearResults",
        ),
      toggleFilterPhone: () =>
        set((s) => ({ filterPhone: !s.filterPhone }), false, "toggleFilterPhone"),
      toggleFilterWebsite: () =>
        set((s) => ({ filterWebsite: !s.filterWebsite }), false, "toggleFilterWebsite"),
      setNeighborhood: (polygon, bbox, name) =>
        set(
          { neighborhoodPolygon: polygon, neighborhoodName: name, bbox, results: [], drawnPolygon: null },
          false,
          "setNeighborhood",
        ),
      clearNeighborhood: () =>
        set(
          { neighborhoodPolygon: null, neighborhoodName: null, bbox: null, results: [], drawnPolygon: null },
          false,
          "clearNeighborhood",
        ),
      setDrawnPolygon: (points, bbox) =>
        set(
          { drawnPolygon: points, bbox, results: [], neighborhoodPolygon: null, neighborhoodName: null },
          false,
          "setDrawnPolygon",
        ),
      openCampaignPanel: (items) =>
        set({ campaignContacts: items, showCampaignPanel: true }, false, "openCampaignPanel"),
      setShowCampaignPanel: (show) =>
        set({ showCampaignPanel: show }, false, "setShowCampaignPanel"),
      openCampaignsManager: () =>
        set({ showCampaignsManager: true }, false, "openCampaignsManager"),
      setShowCampaignsManager: (show) =>
        set({ showCampaignsManager: show }, false, "setShowCampaignsManager"),
    }),
    { name: "commerce-store" },
  ),
);
