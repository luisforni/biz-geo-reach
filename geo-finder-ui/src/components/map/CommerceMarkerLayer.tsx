import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { useCommerceStore } from "@/store/useCommerceStore";
import type { Commerce } from "@/types";

const CATEGORY_COLORS: Record<string, string> = {
  amenity: "#f97316",
  shop: "#3b82f6",
  tourism: "#22c55e",
  leisure: "#14b8a6",
  office: "#6b7280",
};

function createIcon(category: string): L.DivIcon {
  const color = CATEGORY_COLORS[category] ?? "#6b7280";
  return L.divIcon({
    className: "",
    html: `<div style="
      width:12px;height:12px;border-radius:50%;
      background:${color};border:2px solid white;
      box-shadow:0 1px 3px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

const TAG_LABELS: Record<string, string> = {
  "addr:street":    "Calle",
  "addr:housenumber": "Número",
  "addr:city":      "Ciudad",
  "addr:postcode":  "CP",
  "phone":          "Teléfono",
  "contact:phone":  "Teléfono",
  "mobile":         "Móvil",
  "website":        "Web",
  "contact:website":"Web",
  "email":          "Email",
  "contact:email":  "Email",
  "opening_hours":  "Horario",
  "cuisine":        "Cocina",
  "diet:vegan":     "Vegano",
  "diet:vegetarian":"Vegetariano",
  "outdoor_seating":"Terraza",
  "takeaway":       "Para llevar",
  "delivery":       "Delivery",
  "wheelchair":     "Accesible",
  "wifi":           "WiFi",
  "stars":          "Estrellas",
  "brand":          "Marca",
  "operator":       "Operador",
  "description":    "Descripción",
};

const TAG_ORDER = [
  "addr:street", "addr:housenumber", "addr:city", "addr:postcode",
  "phone", "contact:phone", "mobile",
  "website", "contact:website",
  "email", "contact:email",
  "opening_hours",
  "cuisine", "diet:vegan", "diet:vegetarian",
  "outdoor_seating", "takeaway", "delivery", "wifi", "wheelchair",
  "stars", "brand", "operator", "description",
];

function renderTag(key: string, value: string): string {
  const label = TAG_LABELS[key] ?? key;
  let display = value;

  if (key === "website" || key === "contact:website") {
    const href = value.startsWith("http") ? value : `https://${value}`;
    display = `<a href="${href}" target="_blank" rel="noopener">${value}</a>`;
  } else if (key === "phone" || key === "contact:phone" || key === "mobile") {
    display = `<a href="tel:${value}">${value}</a>`;
  } else if (value === "yes") {
    display = "✓";
  } else if (value === "no") {
    display = "✗";
  }

  return `
    <tr>
      <td style="color:#6b7280;white-space:nowrap;padding:2px 8px 2px 0;font-size:11px">${label}</td>
      <td style="font-size:12px">${display}</td>
    </tr>`;
}

function buildPopupContent(c: Commerce): string {
  const name = c.name || "(sin nombre)";
  const color = CATEGORY_COLORS[c.category] ?? "#6b7280";

  const shownKeys = new Set<string>();
  const rows: string[] = [];

  for (const key of TAG_ORDER) {
    const value = c.tags[key];
    if (value) {
      rows.push(renderTag(key, value));
      shownKeys.add(key);
    }
  }

  const skip = new Set(["name", "amenity", "shop", "tourism", "leisure", "office", "source", "type"]);
  for (const [key, value] of Object.entries(c.tags)) {
    if (!shownKeys.has(key) && !skip.has(key) && value) {
      rows.push(renderTag(key, value));
    }
  }

  const osmUrl = `https://www.openstreetmap.org/${c.osmId > 0 ? "node" : "way"}/${Math.abs(c.osmId)}`;

  return `
    <div style="min-width:220px;max-width:300px;font-family:sans-serif">
      <div style="font-size:15px;font-weight:700;margin-bottom:6px">${name}</div>
      <span style="background:${color};color:white;padding:2px 7px;border-radius:4px;font-size:11px;margin-bottom:8px;display:inline-block">
        ${c.subcategory}
      </span>
      ${rows.length > 0 ? `<table style="margin-top:6px;border-collapse:collapse;width:100%">${rows.join("")}</table>` : ""}
      <div style="margin-top:8px;font-size:10px;color:#9ca3af">
        <a href="${osmUrl}" target="_blank" rel="noopener" style="color:#9ca3af">
          OSM ${c.osmId}
        </a>
      </div>
    </div>
  `;
}

export function CommerceMarkerLayer() {
  const map = useMap();
  const results = useCommerceStore((s) => s.results);
  const focusedOsmId = useCommerceStore((s) => s.focusedOsmId);
  const clusterGroupRef = useRef<L.LayerGroup | null>(null);
  const markerMapRef = useRef<Map<number, L.Marker>>(new Map());

  useEffect(() => {
    const group = L.layerGroup();
    group.addTo(map);
    clusterGroupRef.current = group;

    return () => {
      map.removeLayer(group);
    };
  }, [map]);

  useEffect(() => {
    const group = clusterGroupRef.current;
    if (!group) return;

    group.clearLayers();
    markerMapRef.current.clear();

    results.forEach((c) => {
      const marker = L.marker([c.lat, c.lon], { icon: createIcon(c.category) });
      marker.bindPopup(buildPopupContent(c));
      group.addLayer(marker);
      markerMapRef.current.set(c.osmId, marker);
    });
  }, [results]);

  useEffect(() => {
    if (focusedOsmId === null) return;
    const marker = markerMapRef.current.get(focusedOsmId);
    if (marker) {
      map.setView(marker.getLatLng(), Math.max(map.getZoom(), 16));
      marker.openPopup();
    }
  }, [focusedOsmId, map]);

  return null;
}
