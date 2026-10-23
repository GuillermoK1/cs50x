# Proyecto final CS50x: Filtro genérico de ofertas de empleo

## Rol

Actúa como un arquitecto de software experto en Python y FastAPI. Vamos a desarrollar el proyecto final de CS50x: un sistema genérico que consume diferentes APIs de empleo mediante el **patrón Adapter** y filtra ofertas sospechosas (estafas u ofertas fantasma).

## Contexto técnico

- **Python 3.11 o superior.** Usa sintaxis moderna de tipado (`str | None`, `list[str]`, etc.).
- **Pydantic v2** y `pydantic-settings`.
- Todo el código debe estar completamente tipado (type hints) y preparado para ser testeado.
- Los métodos de extracción de datos son **asíncronos** (`async def`).

## Plan por fases (para tu referencia)

| Fase | Contenido |
|------|-----------|
| 1 | Arquitectura base y modelos de datos (**esta es la fase actual**) |
| 2 | Adaptadores concretos (`AdzunaProvider`, `MockProvider`) y módulo `ScamDetector` |
| 3 | Tests con pytest + pytest-asyncio; simulación de HTTP con `respx` |
| 4 | Capa de API (FastAPI) y persistencia (SQLite) |
| 5 | Interfaz (Jinja2) y entrega (README y vídeo) |

## Alcance de ESTA conversación

Trabajamos **exclusivamente en la Fase 1** y dejamos preparado el entorno para la Fase 3.

**No implementes todavía:** rutas de FastAPI, base de datos, adaptadores concretos ni el `ScamDetector`.

## Qué debes generar

### 1. Estructura de carpetas

Propón un árbol de carpetas profesional que incluya como mínimo `adapters/`, `core/`, `api/` y `tests/`. Incluye también:

- Los archivos `__init__.py` necesarios.
- `.env.example` y `.gitignore`.
- `pyproject.toml` con la configuración de pytest (ver punto 5).

Explica en una línea el propósito de cada carpeta.

### 2. `requirements.txt`

Debe incluir:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic-settings`
- `httpx`
- `pytest`
- `pytest-asyncio`
- `respx` (para simular llamadas `httpx` en los tests; **no** uses `responses`, que solo funciona con `requests`)

### 3. `core/config.py`

Configuración con `pydantic-settings` (`BaseSettings`) que lea variables desde `.env`. Incluye campos de ejemplo para credenciales de una API externa (por ejemplo `adzuna_app_id` y `adzuna_app_key`) con valores opcionales o por defecto seguros. Entrega también el `.env.example` correspondiente.

### 4. `core/schemas.py`

Modelo unificado de oferta de empleo llamado **`JobSummary`** (usa siempre este nombre; no `JobSchema`), con Pydantic v2.

Campos sugeridos: `id`, `title`, `company`, `description`, `location`, `salary_min`, `salary_max`, `currency`, `url`, `posted_at`, `source` (nombre del proveedor).

Validaciones mínimas:

- `salary_min` y `salary_max` no pueden ser negativos si existen.
- Si ambos existen, `salary_min <= salary_max`.
- `title` no puede estar vacío.
- `url` debe ser una URL válida.

Usa `field_validator` / `model_validator` de Pydantic v2.

Los modelos de **entrada nativa** de cada API (el formato crudo de Adzuna, etc.) irán dentro de cada adaptador en la Fase 2. Indica en un comentario o docstring que el adaptador será el responsable de traducir el formato nativo a `JobSummary`.

### 5. `adapters/base.py`

Clase abstracta `JobProvider` usando el módulo `abc` (`ABC` y `@abstractmethod`):

- Un método `async def fetch_jobs(self, query: str, ...) -> list[JobSummary]` abstracto.
- Un atributo o propiedad abstracta `name` que identifique al proveedor.
- Docstrings claros que expliquen el contrato que debe cumplir cada adaptador.

### 6. Entorno de pytest

- `pyproject.toml` con la sección `[tool.pytest.ini_options]` que incluya `asyncio_mode = "auto"` y `testpaths = ["tests"]`.
- `tests/conftest.py` con un fixture de ejemplo que devuelva un `JobSummary` válido.
- `tests/test_filters.py` como esqueleto: un test síncrono y un test `async` de ejemplo (pueden validar `JobSummary`), más comentarios `# TODO` indicando dónde irán los tests del `ScamDetector` en la Fase 2/3.

## Criterios de calidad

- Código limpio, sin lógica innecesaria y con nombres descriptivos.
- Docstrings breves y type hints en todas las funciones y métodos.
- Cada archivo debe presentarse con su ruta completa en un bloque de código separado.
- Al final, indica cómo instalar dependencias y ejecutar `pytest` para comprobar que el esqueleto funciona.

## Notas para fases posteriores (no actuar todavía)

- Persistencia: preferir SQLAlchemy 2.0 con `aiosqlite`, ya que `cs50.SQL` es síncrona y bloquea el event loop en rutas `async`.
- Endpoint de búsqueda previsto: `GET /jobs/search?query=python&exclude_scams=true`.
- Jinja2 requiere instalar `jinja2` por separado (Fase 5).
- Las reglas heurísticas del detector producirán falsos positivos; debe documentarse como limitación en el README.
- Requisitos de entrega de CS50x (verificar en la web del curso, pueden cambiar): README de al menos 750 palabras y vídeo de máximo 3 minutos.

Antes de generar el código, resume en 3 o 4 líneas cómo entiendes el alcance. Si algo es ambiguo, haz como máximo una pregunta.
