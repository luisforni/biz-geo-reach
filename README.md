# Commerce Finder

Herramienta para explorar comercios y servicios en cualquier zona del mundo. Dibujás un rectángulo en el mapa, elegís los rubros que te interesan y obtenés la lista de establecimientos de esa área usando datos de **OpenStreetMap** — 100% gratuito, sin API key.

## Demo

1. Dibujá un rectángulo en el mapa con la herramienta de dibujo.
2. Filtrá por rubro (restaurantes, farmacias, hoteles, comercios, etc.).
3. Hacé clic en un resultado de la lista para centrar el mapa en ese comercio.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Go 1.23 · Chi router |
| Base de datos | PostgreSQL 15 + PostGIS |
| Caché | Redis 7 |
| Datos | OpenStreetMap · Overpass API (gratuita) |
| Frontend | React 18 · TypeScript · Leaflet.js · Zustand · TanStack Query |
| Infraestructura | Docker Compose · Nginx |

## Estructura del proyecto

```
commerce-finder/
├── commerce-finder-backend/    # API Go (gateway, servicios, repositorios)
├── commerce-finder-frontend/   # SPA React + Leaflet
├── docker-compose.yml
├── nginx.conf
└── init.sql
```

## Arquitectura

```
Browser (Leaflet Draw)
  └─► Nginx
        └─► Go API Gateway
              └─► Commerce Service
                    ├─► Redis          (cache hit → < 50 ms)
                    ├─► PostGIS        (bbox ya descargado)
                    └─► Overpass API   (circuit breaker + rate limit)
                          └─► persiste en PostGIS + Redis
```

**Flujo de caché tiered:**
1. Redis — clave `geo:{bbox_hash}:{categories_hash}`, TTL configurable (default 1 h).
2. PostGIS — `ST_Covers` verifica si el bbox ya fue descargado anteriormente.
3. Overpass API — solo se llama cuando no hay datos locales; circuit breaker abre tras 5 fallos consecutivos.

## Clonar el repositorio

```bash
git clone --recurse-submodules https://github.com/luisforni/commerce-finder.git
```

Si ya lo clonaste sin submodulos:

```bash
git submodule update --init --recursive
```

## Levantarlo localmente

### Requisitos

- Docker >= 24
- Docker Compose >= 2.20

### Producción (todo en contenedores)

```bash
docker compose up --build
```

Luego abrí `http://localhost:8090`.

### Desarrollo frontend (hot-reload)

```bash
# Terminal 1 — backend + DB + Redis
docker compose up postgres redis backend

# Terminal 2 — frontend con Vite
cd commerce-finder-frontend
npm install
npm run dev        # http://localhost:5173
```

Vite proxea `/api` al backend en `:8080` automáticamente.

## Variables de entorno (backend)

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | — | DSN de PostgreSQL (requerido) |
| `REDIS_URL` | — | URL de Redis (requerido) |
| `OVERPASS_URL` | `https://overpass-api.de/api/interpreter` | Endpoint de Overpass |
| `PORT` | `8080` | Puerto HTTP del servidor |
| `RATE_LIMIT_RPM` | `60` | Requests por minuto por IP |
| `CACHE_TTL` | `1h` | TTL de entradas en Redis |

## API

### `POST /api/commerce/search`

```json
{
  "bbox": { "south": -34.62, "west": -58.44, "north": -34.58, "east": -58.38 },
  "categories": [
    { "key": "amenity", "value": "restaurant" },
    { "key": "shop",    "value": "bakery" }
  ]
}
```

Respuesta:

```json
{
  "items": [ { "osmId": 123, "name": "...", "category": "amenity", "subcategory": "restaurant", "lat": -34.60, "lon": -58.41, "tags": {} } ],
  "source": "cache",
  "count": 1
}
```

El header `X-Source` indica si la respuesta vino de `cache`, `db` u `overpass`.

### `GET /api/categories`

Devuelve la lista de rubros disponibles para el filtro del frontend.

### `GET /api/health`

```json
{ "status": "ok" }
```

## Rubros soportados

| Clave OSM | Label | Ejemplos |
|---|---|---|
| `amenity` | Servicios | restaurant, cafe, pharmacy, bank, hospital |
| `shop` | Comercios | supermarket, bakery, clothes, electronics |
| `tourism` | Turismo | hotel, hostel, museum, gallery |
| `leisure` | Ocio | fitness_centre, cinema, park |
| `office` | Oficinas | company, lawyer, accountant |

## Principios de diseño

- **SOLID** — el `CommerceService` depende de interfaces (`Repository`, `Cache`, `OverpassFetcher`), nunca de implementaciones concretas.
- **Clean Architecture** — lógica de negocio en `internal/commerce/`, persistencia en `internal/geo/`, transporte en `internal/gateway/`.
- **TypeScript strict** — `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, sin `any` en código de producción.
