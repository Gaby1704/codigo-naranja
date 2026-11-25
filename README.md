# Código Naranja

Tablero territorial de demanda de atención y cobertura de servicios para municipios de Tlaxcala. El equipo es **Código Naranja by muegan-ing**, edición Datathon 2026.

La interfaz muestra dónde la demanda registrada se acerca o supera la capacidad de atención, y sugiere una acción operativa (unidad móvil, jornada de detección, ampliar turnos o mantener la oferta). Los datos de arranque son sintéticos y no representan cifras oficiales.

## Estructura

```
codigo-naranja/
├── apps/
│   ├── web/                 # React, Vite y Tailwind. Rutas, vistas y estado.
│   └── api/                 # FastAPI. Auth, reglas, carga y limpieza.
├── packages/
│   └── shared/              # Constantes, tipos TypeScript y esquemas JSON.
├── docker-compose.yml
├── .env.example
└── README.md
```

| Ruta | Responsabilidad |
| --- | --- |
| `apps/web` | Tablero, mapa, filtros, sesión en el navegador y formulario de carga. No calcula prioridades ni limpia Excel. |
| `apps/api` | Sesión de administrador, agregados del tablero, lectura de Excel y reglas de limpieza. |
| `packages/shared` | Catálogo de municipios, umbrales de clasificación, fórmula de datos demo, patrones de columnas y el contrato JSON entre ambos lados. |

`packages/shared/constants.json` es la fuente que lee Python. `packages/shared/types.ts` son los tipos del frontend. `packages/shared/schemas/` documenta los mismos DTO en JSON Schema.

## Cómo se reparte el trabajo

```text
Navegador (React)
  filtros, mapa, gráficas, tabla, sesión visible
        │  /api  (cookie httpOnly)
        ▼
FastAPI
  login · agregados · clasificación · Excel · deduplicación
        │
        ▼
SQLite
  usuarios, sesiones y dataset activo
```

El tablero público no pide cuenta. La carga de archivos sí: solo la cuenta administradora.

## Requisitos

- Node.js 22 y npm, para el frontend.
- Python 3.12 o 3.13, para la API.
- Docker y Docker Compose, solo si vas a usar el contenedor.

## Configuración

```bash
cp .env.example .env
```

| Variable | Uso |
| --- | --- |
| `APP_ENV` | `development` o `production`. No cambia la cookie por sí solo. |
| `ADMIN_EMAIL` | Correo de la cuenta que puede cargar archivos. |
| `ADMIN_PASSWORD` | Mínimo 12 caracteres y máximo 72 bytes. Si no cumple, la API arranca igual y no crea la cuenta. |
| `CORS_ORIGINS` | Orígenes permitidos si el navegador llama a la API sin proxy. Lista separada por comas. |
| `COOKIE_SECURE` | `true` solo detrás de HTTPS. En `http://localhost` debe quedar `false`, si no el navegador ignora la cookie. |
| `TRUST_PROXY` | `true` cuando Nginx manda `X-Real-IP`. El compose lo activa. En local déjalo en `false`. |
| `DATABASE_PATH` | Opcional. Si no está, la base se crea en `apps/api/data/codigo_naranja.sqlite`. |

La contraseña no se imprime en logs ni se expone por ningún endpoint. El archivo `.env` está en `.gitignore`.

## Desarrollo local

Terminal 1, API:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Terminal 2, frontend:

```bash
cd apps/web
npm install
npm run dev
```

Abre [http://localhost:5173](http://localhost:5173). Vite reenvía `/api` a `http://127.0.0.1:8000`, así que la cookie de sesión queda en el mismo origen.

Pruebas de la API:

```bash
cd apps/api
source .venv/bin/activate
pytest
```

Compilación del frontend:

```bash
cd apps/web
npm run build
```

## Docker

Desde la raíz, con `ADMIN_EMAIL` y `ADMIN_PASSWORD` definidos en el entorno o en `.env`:

```bash
docker compose up --build
```

La interfaz queda en [http://localhost:8080](http://localhost:8080). Nginx sirve el build de React y reenvía `/api` al contenedor de la API. La base vive en el volumen `api-data`.

`COOKIE_SECURE` sigue en `false` porque ese puerto es HTTP. Si publicas el compose detrás de HTTPS, pon `COOKIE_SECURE=true`.

## Frontend

Rutas con React Router:

| Ruta | Vista | Quién entra |
| --- | --- | --- |
| `/` | Tablero territorial: filtros, indicadores, mapa, gráficas y tabla. | Cualquiera |
| `/admin` | Carga de Excel, mapeo de columnas y aplicación del dataset. | Solo administrador. Si no hay sesión, regresa a `/`. |

Estado:

- `AuthProvider` pide `GET /api/auth/me` al cargar y guarda el usuario en memoria. La sesión real está en la cookie `cn_session`.
- `BoardProvider` pide el tablero cada vez que cambian los filtros. El municipio seleccionado, la búsqueda de la tabla y la vista móvil viven en la vista, no en el servidor.
- Tailwind CSS v4 entra por `@tailwindcss/vite`. La apariencia del tablero está en `apps/web/src/index.css` (clases del diseño original) y las utilidades de Tailwind cubren detalles como `sr-only`.

El mapa proyecta `apps/web/public/tlaxcala.geojson` con `d3-geo` (Mercator centrado en Tlaxcala). Los puntos de los 20 municipios y sus coordenadas están en `packages/shared/constants.json`.

## API

Base: `http://127.0.0.1:8000`. Documentación interactiva: `http://127.0.0.1:8000/docs`.

Todas las respuestas llevan `Cache-Control: no-store`. Las peticiones que modifican estado exigen el encabezado `X-Codigo-Naranja: 1` para que un formulario de otro sitio no pueda usar la cookie.

| Método | Ruta | Auth | Qué hace |
| --- | --- | --- | --- |
| `GET` | `/api/health` | No | `{ "status": "ok" }` |
| `POST` | `/api/auth/login` | No | Crea la sesión. Cuerpo: `{ "email", "password" }`. |
| `POST` | `/api/auth/logout` | Cookie | Borra la sesión. Responde `204`. |
| `GET` | `/api/auth/me` | Cookie opcional | `{ "user": null }` o el usuario público (`name`, `email`, `role`). |
| `GET` | `/api/dashboard` | No | Agregados filtrados. |
| `GET` | `/api/datasets/template` | Admin | Descarga `plantilla-smet.xlsx`. |
| `POST` | `/api/datasets/uploads` | Admin | Multipart, campo `file`. Devuelve vista previa y mapeo sugerido. |
| `POST` | `/api/datasets/uploads/{id}/sheet` | Admin | Cambia la hoja de una carga pendiente. |
| `POST` | `/api/datasets/uploads/{id}/apply` | Admin | Limpia y reemplaza el dataset activo. |

Filtros de `GET /api/dashboard` (query string):

| Parámetro | Vacío equivale a |
| --- | --- |
| `period` | `2026` |
| `municipality` | `Todas las zonas` |
| `violence` | `Todos los tipos` |
| `service` | `Todos los servicios` |

Ejemplo de acceso:

```bash
curl -c cookies.txt \
  -H 'Content-Type: application/json' \
  -H 'X-Codigo-Naranja: 1' \
  -d '{"email":"admin@ejemplo.mx","password":"una-clave-larga"}' \
  http://127.0.0.1:8000/api/auth/login
```

La respuesta del tablero trae `periods`, `municipalities`, `violenceTypes`, `serviceTypes`, `summaries`, `trends`, `totalCases`, `totalCapacity`, `priorityCount` y `source`. Cada municipio en `summaries` incluye `classification` con `label`, `action` y `color` (`priority`, `watch`, `elevated` o `stable`).

`source.synthetic` es `true` mientras sigue el dataset de demostración. Después de una carga válida pasa a `false` y `source.audit` resume la limpieza. `source.fileName` es el nombre del libro.

## Reglas de negocio

Clasificación de un municipio, en este orden, con los umbrales de `packages/shared/constants.json`:

1. **Atención prioritaria** si `casos / capacidad >= 1.3`. Acción: programar unidad móvil.
2. **Posible subregistro** si hay menos de 35 casos y la razón es mayor que 0.8. Acción: jornada de detección.
3. **Optimizar capacidad** si la razón es mayor o igual que 0.9. Acción: ampliar turnos.
4. **Cobertura estable** en cualquier otro caso. Acción: mantener la oferta.

Si la capacidad es 0, la razón se toma como 99 y el municipio cae en atención prioritaria. Los indicadores del encabezado suman casos y capacidad de la selección; la brecha de ese encabezado es `casos totales / capacidad total`, no el promedio de las razones municipales.

La tendencia ignora el periodo, el tipo de violencia y el tipo de servicio. Solo respeta el municipio elegido y muestra hasta los últimos cinco periodos.

Limpieza al aplicar un Excel:

1. Se exige una columna de persona o expediente. Sin ella la API rechaza la carga.
2. Las filas se ordenan por periodo (más reciente primero) y, a igualdad de periodo, por la razón casos/capacidad.
3. Se descartan filas vacías y filas idénticas.
4. Si el identificador de persona ya apareció, se conserva solo la primera fila de ese orden (la más reciente o la de mayor presión) y las demás cuentan como alerta duplicada.
5. Un número vacío o ilegible en casos o capacidad se imputa con 0 y se cuenta en `imputed`. Los negativos válidos se guardan como 0.
6. El municipio se escribe con el nombre del catálogo si coincide sin importar mayúsculas ni acentos (`apizaco` → `Apizaco`). Si no está en el catálogo, se guarda en mayúsculas sin acentos y aparece en la tabla, no en el mapa.
7. Violencia y servicio se normalizan a mayúsculas sin acentos. El periodo se conserva recortado. Un texto vacío pasa a `NO ESPECIFICADO`.

El mapeo sugerido busca, en el nombre de la columna, las pistas de `constants.json` (`MUNICIPIO`, `PERIODO`, `VIOLENCIA`, `IDENTIFICADOR`, etc.).

Límites de carga: 8 MB, 20 000 filas y 40 columnas. La carga pendiente vive en memoria 30 minutos y solo la puede aplicar quien la subió. Al aplicar, reemplaza por completo el dataset anterior.

La plantilla trae la columna `Identificador` porque la deduplicación la necesita.

## Datos de demostración

Si no hay dataset activo, la API inserta 20 municipios × 3 años (2024, 2025 y 2026). La fórmula está en `constants.json` y la cubre `apps/api/tests/test_rules.py`. Esos registros no salen de una fuente oficial.

## Autenticación

- No hay registro público. La única cuenta nace de `ADMIN_EMAIL` y `ADMIN_PASSWORD` al arrancar.
- Si el correo ya existe, el arranque solo asegura el rol `admin`. No reescribe la contraseña.
- La contraseña se guarda con bcrypt (factor 12).
- El navegador recibe un token aleatorio en la cookie `cn_session` (`HttpOnly`, `SameSite=Lax`, 7 días). En la base solo se guarda su SHA-256.
- Un correo o contraseña incorrectos responden igual: no se dice cuál falló. Hay un tope de 8 intentos por IP cada 10 minutos.
- Una cuenta que no es `admin` no recibe sesión.

## Seguridad

- El endpoint que devolvía el correo y la contraseña de demo no existe en esta versión.
- Los errores de validación no repiten el cuerpo recibido, para no devolver la contraseña en un 422.
- El Excel se lee con `openpyxl` o `xlrd` (`data_only` en xlsx). No se ejecutan macros ni fórmulas.
- Se comprueba la firma del archivo (`PK` para xlsx, OLE para xls), no solo la extensión.
- La exportación CSV del navegador antepone una comilla a celdas que empiezan por `=`, `+`, `-`, `@` o un tabulador.
- Encabezados: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y `Permissions-Policy`. `Strict-Transport-Security` solo si `COOKIE_SECURE=true`.
- El contenedor de la API corre con un usuario sin privilegios.

## Qué no hace este tablero

- No estima población ni incidencia real. Una zona con pocos registros puede ser subregistro.
- El mapa marca 20 municipios del catálogo. Otros nombres válidos se ven en la tabla.
- La posición de los puntos es esquemática, no es una coordenada geográfica oficial.
- Una sola réplica de la API guarda las cargas pendientes en memoria. Varios workers no comparten esa vista previa; el dataset ya aplicado sí está en SQLite