import type { CategoryGroup, SearchRequest, SearchResponse } from "@/types";
import { ApiError } from "@/types";

const BASE_URL = import.meta.env["VITE_API_URL"] ?? "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = (await response.json()) as { error?: string };
      if (body.error) message = body.error;
    } catch {
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}

export async function searchCommerce(
  req: SearchRequest,
): Promise<SearchResponse> {
  return fetchJSON<SearchResponse>("/commerce/search", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getCategories(): Promise<CategoryGroup[]> {
  return fetchJSON<CategoryGroup[]>("/categories");
}
