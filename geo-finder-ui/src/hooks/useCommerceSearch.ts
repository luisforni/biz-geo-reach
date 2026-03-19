import { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { searchCommerce } from "@/services/api";
import { useCommerceStore } from "@/store/useCommerceStore";
import { ApiError } from "@/types";

export function useCommerceSearch() {
  const { bbox, selectedCategories, setResults, setIsLoading } =
    useCommerceStore();

  const mutation = useMutation({
    mutationFn: searchCommerce,
    onMutate: () => setIsLoading(true),
    onSettled: () => setIsLoading(false),
    onSuccess: (data) =>
      setResults(data.items.map((item) => ({ ...item, tags: item.tags ?? {} }))),
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          console.warn("Rate limited by Overpass proxy. Retry in 1s.");
        } else if (err.status === 503) {
          console.warn("Overpass API temporarily unavailable.");
        }
      }
    },
  });

  const mutateRef = useRef(mutation.mutate);
  mutateRef.current = mutation.mutate;

  useEffect(() => {
    if (!bbox) return;
    mutateRef.current({ bbox, categories: selectedCategories });
  }, [bbox, selectedCategories]);

  return {
    isLoading: mutation.isPending,
    error: mutation.error instanceof ApiError ? mutation.error : null,
  };
}
