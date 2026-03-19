# commerce-finder-frontend

SPA React para el proyecto Commerce Finder. Permite seleccionar una zona en el mapa y explorar los comercios de esa área con filtros por rubro.

## Stack

| | |
|---|---|
| Framework | React 18 + TypeScript (strict) |
| Mapa | Leaflet.js + react-leaflet |
| Estado | Zustand |
| Data fetching | TanStack Query v5 |
| Build | Vite 6 |

## Estructura

```
commerce-finder-frontend/
└── src/
    ├── components/
    │   ├── map/
    │   │   ├── MapCanvas.tsx          # Contenedor del mapa Leaflet
    │   │   ├── DrawingTool.tsx        # Selección rectangular nativa
    │   │   └── CommerceMarkerLayer.tsx # Markers con popup de datos OSM
    │   └── ui/
    │       ├── CategoryFilter.tsx     # Chips de filtro por rubro
    │       └── ResultsList.tsx        # Lista de resultados ordenada por distancia
    ├── hooks/
    │   └── useCommerceSearch.ts       # Dispara búsqueda al cambiar bbox o filtros
    ├── services/
    │   └── api.ts                     # Cliente HTTP tipado
    ├── store/
    │   └── useCommerceStore.ts        # Estado global (Zustand)
    └── types/
        └── index.ts                   # Tipos compartidos con el backend
```

## Uso

1. Hacer clic en el botón **⬚** del mapa para activar la herramienta de selección.
2. Clic y arrastrar sobre el mapa para dibujar la zona.
3. Usar los chips de **Rubros** para filtrar por tipo de comercio.
4. Hacer clic en un resultado del sidebar para centrar el mapa en ese comercio.

## Desarrollo local

```bash
npm install
npm run dev
```

Requiere el backend corriendo en `:8080`. Vite proxea `/api` automáticamente.

## Build

```bash
npm run build
```

## Variables de entorno

| Variable | Default | |
|---|---|---|
| `VITE_API_URL` | `/api` | URL base del backend |
