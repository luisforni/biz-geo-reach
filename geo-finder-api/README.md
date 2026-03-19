# commerce-finder-backend

API REST en Go para el proyecto Commerce Finder. Expone endpoints para buscar comercios por zona geográfica usando datos de OpenStreetMap.

## Stack

| | |
|---|---|
| Lenguaje | Go 1.23 |
| Router | Chi v5 |
| Base de datos | PostgreSQL 15 + PostGIS |
| Caché | Redis 7 |
| Datos | Overpass API (OpenStreetMap) |

## Estructura

```
commerce-finder-backend/
├── cmd/server/          # Entrypoint
├── internal/
│   ├── cache/           # Cliente Redis
│   ├── commerce/        # Servicio + interfaz Repository + generador de cache key
│   ├── config/          # Variables de entorno
│   ├── gateway/         # Router Chi, middleware, handlers HTTP
│   ├── geo/             # Implementación PostGIS del Repository
│   └── overpass/        # Cliente HTTP Overpass + query builder + parser
└── pkg/models/          # Tipos compartidos (BBox, Commerce, SearchRequest…)
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/categories` | Lista de rubros disponibles |
| `POST` | `/api/commerce/search` | Busca comercios en un bounding box |

### POST /api/commerce/search

```json
{
  "bbox": { "south": -34.62, "west": -58.44, "north": -34.58, "east": -58.38 },
  "categories": [
    { "key": "amenity", "value": "restaurant" }
  ]
}
```

El header de respuesta `X-Source` indica el origen del dato: `cache`, `db` u `overpass`.

## Variables de entorno

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | — | Requerido |
| `REDIS_URL` | — | Requerido |
| `OVERPASS_URL` | `https://overpass-api.de/api/interpreter` | |
| `PORT` | `8080` | |
| `RATE_LIMIT_RPM` | `60` | Requests por minuto por IP |
| `CACHE_TTL` | `1h` | TTL de entradas en Redis |

## Desarrollo local

```bash
go mod download
go build ./cmd/server
DATABASE_URL=... REDIS_URL=... ./server
```

## Tests

```bash
go test ./...
```
