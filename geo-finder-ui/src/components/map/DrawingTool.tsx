import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { useCommerceStore } from "@/store/useCommerceStore";
import type { BBox } from "@/types";

const VERTEX_STYLE: L.CircleMarkerOptions = {
  radius: 5,
  color: "#2563eb",
  fillColor: "#ffffff",
  fillOpacity: 1,
  weight: 2,
  interactive: false,
};

const VERTEX_CLOSE_STYLE: L.CircleMarkerOptions = {
  ...VERTEX_STYLE,
  fillColor: "#2563eb",
  radius: 7,
};

const EDGE_STYLE: L.PolylineOptions = {
  color: "#2563eb",
  weight: 2,
  interactive: false,
};

const RUBBER_STYLE: L.PolylineOptions = {
  color: "#2563eb",
  weight: 1.5,
  dashArray: "5 5",
  interactive: false,
};

const POLYGON_STYLE: L.PolylineOptions = {
  color: "#2563eb",
  weight: 2,
  fillColor: "#2563eb",
  fillOpacity: 0.1,
  interactive: false,
};

const POLYGON_SVG = `
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
       fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 20 L8 4 L16 10 L21 5 L20 20 Z"/>
    <circle cx="3"  cy="20" r="2" fill="currentColor" stroke="none"/>
    <circle cx="8"  cy="4"  r="2" fill="currentColor" stroke="none"/>
    <circle cx="16" cy="10" r="2" fill="currentColor" stroke="none"/>
    <circle cx="21" cy="5"  r="2" fill="currentColor" stroke="none"/>
    <circle cx="20" cy="20" r="2" fill="currentColor" stroke="none"/>
  </svg>`;

export function DrawingTool() {
  const map = useMap();

  const setIsDrawing = useCommerceStore((s) => s.setIsDrawing);
  const setDrawnPolygon = useCommerceStore((s) => s.setDrawnPolygon);
  const drawnPolygon = useCommerceStore((s) => s.drawnPolygon);

  const finalPolygonRef = useRef<L.Polygon | null>(null);
  const edgesRef = useRef<L.Polyline | null>(null);
  const rubberRef = useRef<L.Polyline | null>(null);
  const markersRef = useRef<L.CircleMarker[]>([]);
  const btnRef = useRef<HTMLButtonElement | null>(null);

  const activeRef = useRef(false);
  const pointsRef = useRef<L.LatLng[]>([]);

  const setIsDrawingRef = useRef(setIsDrawing);
  const setDrawnPolygonRef = useRef(setDrawnPolygon);
  setIsDrawingRef.current = setIsDrawing;
  setDrawnPolygonRef.current = setDrawnPolygon;

  useEffect(() => {
    if (!drawnPolygon && finalPolygonRef.current) {
      map.removeLayer(finalPolygonRef.current);
      finalPolygonRef.current = null;
    }
  }, [drawnPolygon, map]);

  useEffect(() => {
    const clearDrawingLayers = () => {
      edgesRef.current?.remove();
      edgesRef.current = null;
      rubberRef.current?.remove();
      rubberRef.current = null;
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
    };

    const deactivate = () => {
      activeRef.current = false;
      setIsDrawingRef.current(false);
      map.getContainer().style.cursor = "";
      btnRef.current?.classList.remove("leaflet-select-btn--active");
    };

    const cancelDrawing = () => {
      clearDrawingLayers();
      pointsRef.current = [];
      deactivate();
    };

    const finishPolygon = () => {
      const pts = pointsRef.current;
      if (pts.length < 3) {
        cancelDrawing();
        return;
      }

      clearDrawingLayers();

      finalPolygonRef.current?.remove();
      const poly = L.polygon(pts, POLYGON_STYLE).addTo(map);
      finalPolygonRef.current = poly;

      const bounds = poly.getBounds();
      const bbox: BBox = {
        south: bounds.getSouth(),
        west: bounds.getWest(),
        north: bounds.getNorth(),
        east: bounds.getEast(),
      };
      const latLons = pts.map((p) => [p.lat, p.lng] as [number, number]);
      setDrawnPolygonRef.current(latLons, bbox);

      pointsRef.current = [];
      deactivate();
    };

    const SelectControl = L.Control.extend({
      onAdd() {
        const btn = L.DomUtil.create(
          "button",
          "leaflet-select-btn",
        ) as HTMLButtonElement;
        btn.title =
          "Dibujar zona — click para agregar puntos, click en el primer punto para cerrar, Escape para cancelar";
        btn.innerHTML = POLYGON_SVG;
        btnRef.current = btn;

        L.DomEvent.disableClickPropagation(btn);
        L.DomEvent.on(btn, "click", () => {
          if (activeRef.current) {
            cancelDrawing();
          } else {
            activeRef.current = true;
            btn.classList.add("leaflet-select-btn--active");
            map.getContainer().style.cursor = "crosshair";
          }
        });

        return btn;
      },
      onRemove() {
        btnRef.current = null;
      },
    });

    const control = new SelectControl({ position: "topleft" });
    map.addControl(control);

    const onClick = (e: L.LeafletMouseEvent) => {
      if (!activeRef.current) return;
      L.DomEvent.preventDefault(e.originalEvent);

      const pts = pointsRef.current;

      if (pts.length >= 3) {
        const first = pts[0];
        if (first) {
          const pxFirst = map.latLngToContainerPoint(first);
          const pxClick = map.latLngToContainerPoint(e.latlng);
          if (pxClick.distanceTo(pxFirst) < 15) {
            finishPolygon();
            return;
          }
        }
      }

      pts.push(e.latlng);
      setIsDrawingRef.current(true);

      const dot = L.circleMarker(e.latlng, VERTEX_STYLE).addTo(map);
      markersRef.current.push(dot);

      edgesRef.current?.remove();
      if (pts.length >= 2) {
        edgesRef.current = L.polyline(pts, EDGE_STYLE).addTo(map);
      }
    };

    const onMouseMove = (e: L.LeafletMouseEvent) => {
      if (!activeRef.current || pointsRef.current.length === 0) return;

      const pts = pointsRef.current;
      const last = pts[pts.length - 1];
      if (!last) return;

      rubberRef.current?.remove();
      rubberRef.current = L.polyline([last, e.latlng], RUBBER_STYLE).addTo(map);

      const firstMarker = markersRef.current[0];
      const firstPoint = pts[0];
      if (pts.length >= 3 && firstMarker && firstPoint) {
        const pxFirst = map.latLngToContainerPoint(firstPoint);
        const pxCursor = map.latLngToContainerPoint(e.latlng);
        const near = pxCursor.distanceTo(pxFirst) < 15;
        firstMarker.setStyle(near ? VERTEX_CLOSE_STYLE : VERTEX_STYLE);
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && activeRef.current) cancelDrawing();
    };

    map.on("click", onClick);
    map.on("mousemove", onMouseMove);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      map.off("click", onClick);
      map.off("mousemove", onMouseMove);
      document.removeEventListener("keydown", onKeyDown);
      map.removeControl(control);
      clearDrawingLayers();
      finalPolygonRef.current?.remove();
      finalPolygonRef.current = null;
    };
  }, [map]);

  return null;
}
