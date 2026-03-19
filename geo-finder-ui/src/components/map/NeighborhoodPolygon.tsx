import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { useCommerceStore } from "@/store/useCommerceStore";

const POLYGON_STYLE: L.PathOptions = {
  color: "#2563eb",
  weight: 2,
  fillColor: "#3b82f6",
  fillOpacity: 0.08,
  dashArray: "6 4",
};

export function NeighborhoodPolygon() {
  const map = useMap();
  const { neighborhoodPolygon } = useCommerceStore();
  const layerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      layerRef.current.remove();
      layerRef.current = null;
    }

    if (!neighborhoodPolygon) return;

    const layer = L.geoJSON(neighborhoodPolygon as any, { style: POLYGON_STYLE });
    layer.addTo(map);
    map.fitBounds(layer.getBounds(), { padding: [24, 24] });
    layerRef.current = layer;

    return () => {
      layer.remove();
      layerRef.current = null;
    };
  }, [neighborhoodPolygon, map]);

  return null;
}
