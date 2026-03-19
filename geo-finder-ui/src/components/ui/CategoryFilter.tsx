import { useQuery } from "@tanstack/react-query";
import { getCategories } from "@/services/api";
import { useCommerceStore } from "@/store/useCommerceStore";
import type { Category } from "@/types";

export function CategoryFilter() {
  const { data: groups = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
    staleTime: Infinity,
  });

  const { selectedCategories, setSelectedCategories } = useCommerceStore();

  const isSelected = (key: string, value: string) =>
    selectedCategories.some((c) => c.key === key && c.value === value);

  const toggle = (cat: Category) => {
    if (isSelected(cat.key, cat.value)) {
      setSelectedCategories(
        selectedCategories.filter(
          (c) => !(c.key === cat.key && c.value === cat.value),
        ),
      );
    } else {
      setSelectedCategories([...selectedCategories, cat]);
    }
  };

  const clearAll = () => setSelectedCategories([]);

  if (isLoading) {
    return <div className="filter-loading">Cargando rubros...</div>;
  }

  return (
    <div className="category-filter">
      <div className="filter-header">
        <h3>Rubros</h3>
        {selectedCategories.length > 0 && (
          <button onClick={clearAll} className="btn-clear">
            Limpiar ({selectedCategories.length})
          </button>
        )}
      </div>

      {groups.map((group) => (
        <div key={group.key} className="filter-group">
          <div className="filter-group-label">{group.label}</div>
          <div className="filter-chips">
            {group.values.map((value) => {
              const selected = isSelected(group.key, value);
              return (
                <button
                  key={value}
                  onClick={() => toggle({ key: group.key, value })}
                  className={`chip ${selected ? "chip--selected" : ""}`}
                >
                  {value}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
