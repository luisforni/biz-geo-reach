export interface NominatimResult {
  place_id: number;
  display_name: string;
  type: string;
  class: string;
  geojson: object;
  boundingbox: [string, string, string, string];
}

export async function searchNominatim(query: string): Promise<NominatimResult[]> {
  const params = new URLSearchParams({
    q: query,
    format: "json",
    polygon_geojson: "1",
    limit: "6",
    addressdetails: "0",
  });

  const res = await fetch(
    `https://nominatim.openstreetmap.org/search?${params}`,
    { headers: { "Accept-Language": "es" } },
  );

  if (!res.ok) throw new Error("Nominatim error");
  return res.json();
}
