export interface BBox {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface Category {
  key: string;
  value: string;
}

export interface CategoryGroup {
  key: string;
  label: string;
  values: string[];
}

export interface Commerce {
  id: number;
  osmId: number;
  name: string;
  category: string;
  subcategory: string;
  tags: Record<string, string>;
  lat: number;
  lon: number;
}

export interface SearchRequest {
  bbox: BBox;
  categories: Category[];
}

export interface SearchResponse {
  items: Commerce[];
  source: "cache" | "db" | "overpass";
  count: number;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
