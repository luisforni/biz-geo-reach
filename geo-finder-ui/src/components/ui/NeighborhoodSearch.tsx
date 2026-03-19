import { useState, useRef, type ChangeEvent, type FocusEvent } from "react";
import { useCommerceStore } from "@/store/useCommerceStore";
import { searchNominatim, type NominatimResult } from "@/services/nominatim";
import type { BBox } from "@/types";

function shortName(displayName: string): string {
  return displayName.split(",")[0]?.trim() ?? displayName;
}

function subName(displayName: string): string {
  return displayName.split(",").slice(1, 3).join(",").trim();
}

export function NeighborhoodSearch() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<NominatimResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const { setNeighborhood, clearNeighborhood, neighborhoodName } =
    useCommerceStore();

  const runSearch = async (q: string) => {
    if (q.trim().length < 3) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }
    setIsSearching(true);
    try {
      const data = await searchNominatim(q);
      setSuggestions(data);
      setIsOpen(data.length > 0);
    } catch {
      setSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { void runSearch(val); }, 500);
  };

  const handleSelect = (result: NominatimResult) => {
    const [south, north, west, east] = result.boundingbox;
    const bbox: BBox = {
      south: parseFloat(south),
      north: parseFloat(north),
      west: parseFloat(west),
      east: parseFloat(east),
    };
    const name = shortName(result.display_name);
    setNeighborhood(result.geojson, bbox, name);
    setQuery(name);
    setIsOpen(false);
    setSuggestions([]);
  };

  const handleClear = () => {
    setQuery("");
    setSuggestions([]);
    setIsOpen(false);
    clearNeighborhood();
  };

  const handleBlur = (e: FocusEvent<HTMLDivElement>) => {
    if (!containerRef.current?.contains(e.relatedTarget)) {
      setIsOpen(false);
    }
  };

  return (
    <div
      className="neighborhood-search"
      ref={containerRef}
      onBlur={handleBlur}
    >
      <div className="neighborhood-search__row">
        <input
          type="text"
          className={`neighborhood-search__input${neighborhoodName ? " neighborhood-search__input--active" : ""}`}
          placeholder="Buscar barrio o zona..."
          value={query}
          onChange={handleChange}
          onFocus={() => { if (suggestions.length > 0) setIsOpen(true); }}
        />
        {query && (
          <button
            className="neighborhood-search__clear"
            onClick={handleClear}
            tabIndex={0}
          >
            ✕
          </button>
        )}
      </div>

      {isSearching && (
        <div className="neighborhood-search__status">Buscando...</div>
      )}

      {isOpen && (
        <ul className="neighborhood-search__dropdown">
          {suggestions.map((r) => (
            <li key={r.place_id}>
              <button
                className="neighborhood-search__option"
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(r);
                }}
              >
                <span className="neighborhood-search__option-name">
                  {shortName(r.display_name)}
                </span>
                <span className="neighborhood-search__option-sub">
                  {subName(r.display_name)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
