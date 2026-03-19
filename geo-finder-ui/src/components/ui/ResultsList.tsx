import { useCommerceStore } from "@/store/useCommerceStore";
import type { BBox, Commerce } from "@/types";

function pointInPolygon(lat: number, lon: number, poly: [number, number][]): boolean {
  let inside = false;
  const n = poly.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const pi = poly[i];
    const pj = poly[j];
    if (!pi || !pj) continue;
    const [yi, xi] = pi;
    const [yj, xj] = pj;
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

const TAG_LABELS: Record<string, string> = {
  "addr:street": "Calle",
  "addr:housenumber": "Número",
  "addr:city": "Ciudad",
  "addr:postcode": "CP",
  "addr:suburb": "Barrio",
  "addr:state": "Provincia",
  "addr:country": "País",
  phone: "Teléfono",
  "contact:phone": "Teléfono (alt)",
  mobile: "Móvil",
  email: "Email",
  "contact:email": "Email (alt)",
  website: "Web",
  "contact:website": "Web (alt)",
  opening_hours: "Horario",
  cuisine: "Cocina",
  outdoor_seating: "Terraza",
  takeaway: "Para llevar",
  delivery: "Delivery",
  wheelchair: "Accesibilidad",
  wifi: "WiFi",
  smoking: "Fumadores",
  drive_through: "Drive-through",
  brand: "Marca",
  "brand:wikidata": "Marca Wikidata",
  "brand:wikipedia": "Marca Wikipedia",
  operator: "Operador",
  description: "Descripción",
  "diet:vegan": "Vegano",
  "diet:vegetarian": "Vegetariano",
  "diet:halal": "Halal",
  "diet:kosher": "Kosher",
  "contact:facebook": "Facebook",
  "contact:instagram": "Instagram",
  "contact:twitter": "Twitter",
  "contact:youtube": "YouTube",
  "ref:vatin": "NIF/CIF",
};

function tagLabel(key: string): string {
  return TAG_LABELS[key] ?? key;
}

function escapeCell(val: string): string {
  if (val.includes(",") || val.includes('"') || val.includes("\n")) {
    return `"${val.replace(/"/g, '""')}"`;
  }
  return val;
}

function exportToCSV(
  items: Commerce[],
  cLat: number,
  cLon: number,
  neighborhoodName: string | null,
) {
  const tagKeys = Array.from(
    new Set(items.flatMap((item) => Object.keys(item.tags))),
  ).sort();

  const fixedHeaders = [
    "Nombre",
    "Categoría",
    "Subcategoría",
    "OSM ID",
    "Latitud",
    "Longitud",
    "Distancia",
    ...(neighborhoodName ? ["Zona"] : []),
  ];

  const headers = [...fixedHeaders, ...tagKeys.map(tagLabel)];

  const rows = items.map((item) => {
    const distKm = haversineKm(cLat, cLon, item.lat, item.lon);
    const distStr =
      distKm < 1
        ? `${Math.round(distKm * 1000)} m`
        : `${distKm.toFixed(1)} km`;

    const fixed = [
      item.name,
      item.category,
      item.subcategory,
      item.osmId.toString(),
      item.lat.toString(),
      item.lon.toString(),
      distStr,
      ...(neighborhoodName ? [neighborhoodName] : []),
    ];

    const tags = tagKeys.map((k) => item.tags[k] ?? "");
    return [...fixed, ...tags];
  });

  const csv =
    "\uFEFF" +
    [headers, ...rows].map((row) => row.map(escapeCell).join(",")).join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `comercios_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const CATEGORY_COLORS: Record<string, string> = {
  amenity: "#f97316",
  shop: "#3b82f6",
  tourism: "#22c55e",
  leisure: "#14b8a6",
  office: "#6b7280",
};

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function bboxCenter(bbox: BBox): [number, number] {
  return [(bbox.south + bbox.north) / 2, (bbox.west + bbox.east) / 2];
}

interface ResultRowProps {
  item: Commerce;
  distanceKm: number;
  onFocus: () => void;
}

function ResultRow({ item, distanceKm, onFocus }: ResultRowProps) {
  const color = CATEGORY_COLORS[item.category] ?? "#6b7280";
  const name = item.name || "(sin nombre)";

  const street = [item.tags["addr:street"], item.tags["addr:housenumber"]]
    .filter(Boolean)
    .join(" ");
  const phone = item.tags["phone"] ?? item.tags["contact:phone"];
  const hours = item.tags["opening_hours"];
  const website = item.tags["website"] ?? item.tags["contact:website"];

  return (
    <button className="result-row" onClick={onFocus}>
      <div className="result-row__name">{name}</div>
      <div className="result-row__meta">
        <span className="result-row__chip" style={{ background: color }}>
          {item.subcategory}
        </span>
        <span className="result-row__dist">
          {distanceKm < 1
            ? `${Math.round(distanceKm * 1000)} m`
            : `${distanceKm.toFixed(1)} km`}
        </span>
      </div>
      {street && <div className="result-row__detail">{street}</div>}
      {hours  && <div className="result-row__detail result-row__detail--hours">{hours}</div>}
      {phone  && <div className="result-row__detail">{phone}</div>}
      {website && (
        <div className="result-row__detail">
          <a
            href={website.startsWith("http") ? website : `https://${website}`}
            target="_blank"
            rel="noopener"
            onClick={(e) => e.stopPropagation()}
          >
            {website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
          </a>
        </div>
      )}
    </button>
  );
}

function hasPhone(item: Commerce): boolean {
  return !!(item.tags["phone"] ?? item.tags["contact:phone"]);
}

function hasWebsite(item: Commerce): boolean {
  return !!(item.tags["website"] ?? item.tags["contact:website"]);
}

export function ResultsList() {
  const {
    results,
    bbox,
    isLoading,
    isDrawing,
    focusMarker,
    clearResults,
    filterPhone,
    filterWebsite,
    toggleFilterPhone,
    toggleFilterWebsite,
    neighborhoodName,
    selectedCategories,
    drawnPolygon,
    openCampaignPanel,
  } = useCommerceStore();

  if (isLoading) {
    return <div className="results-state">Buscando comercios...</div>;
  }

  if (isDrawing) {
    return (
      <div className="results-state drawing-hint">
        <div className="drawing-hint__title">Dibujando zona</div>
        <div className="drawing-hint__steps">
          <span>Click para agregar puntos</span>
          <span>Click en el primer punto para cerrar</span>
          <span>Escape para cancelar</span>
        </div>
      </div>
    );
  }

  if (!bbox) {
    return (
      <div className="results-state">
        Dibujá una zona en el mapa o buscá un barrio arriba.
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="results-state">
        No se encontraron comercios en esta zona.
        <button className="btn-clear" onClick={clearResults}>
          Limpiar
        </button>
      </div>
    );
  }

  const [cLat, cLon] = bboxCenter(bbox);

  const filtered = results.filter((item) => {
    if (selectedCategories.length > 0) {
      const match = selectedCategories.some(
        (c) => c.key === item.category && c.value === item.subcategory,
      );
      if (!match) return false;
    }
    if (drawnPolygon && drawnPolygon.length >= 3) {
      if (!pointInPolygon(item.lat, item.lon, drawnPolygon)) return false;
    }
    if (filterPhone && !hasPhone(item)) return false;
    if (filterWebsite && !hasWebsite(item)) return false;
    return true;
  });

  if (filtered.length === 0) {
    return (
      <div className="results-state">
        No se encontraron comercios en esta zona.
        <button className="btn-clear" onClick={clearResults}>
          Limpiar
        </button>
      </div>
    );
  }

  const sorted = [...filtered].sort((a, b) => {
    return (
      haversineKm(cLat, cLon, a.lat, a.lon) -
      haversineKm(cLat, cLon, b.lat, b.lon)
    );
  });

  const phoneCount = results.filter(hasPhone).length;
  const webCount = results.filter(hasWebsite).length;

  return (
    <div className="results-list">
      <div className="results-header">
        <span>
          {filtered.length}
          {filtered.length !== results.length && ` / ${results.length}`}{" "}
          comercios
        </span>
        <div className="results-header__actions">
          <button
            className="btn-export"
            onClick={() => exportToCSV(sorted, cLat, cLon, neighborhoodName)}
            title={`Exportar ${sorted.length} comercios a CSV`}
          >
            ↓ CSV
          </button>
          <button
            className="btn-campaign"
            onClick={() => openCampaignPanel(sorted)}
            title={`Crear campaña con ${sorted.length} comercios`}
          >
            + Campaña WA
          </button>
          <button className="btn-clear" onClick={clearResults}>
            Limpiar
          </button>
        </div>
      </div>
      <div className="results-data-filters">
        <button
          className={`data-filter-btn ${filterPhone ? "data-filter-btn--active" : ""}`}
          onClick={toggleFilterPhone}
          title="Mostrar solo comercios con teléfono"
        >
          📞 Teléfono ({phoneCount})
        </button>
        <button
          className={`data-filter-btn ${filterWebsite ? "data-filter-btn--active" : ""}`}
          onClick={toggleFilterWebsite}
          title="Mostrar solo comercios con web"
        >
          🌐 Web ({webCount})
        </button>
      </div>
      <div className="results-scroll">
        {sorted.map((item) => (
          <ResultRow
            key={item.osmId}
            item={item}
            distanceKm={haversineKm(cLat, cLon, item.lat, item.lon)}
            onFocus={() => focusMarker(item.osmId)}
          />
        ))}
      </div>
    </div>
  );
}
