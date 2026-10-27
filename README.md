# Mystic Explorers - Backend (Text RPG)

Servidor backend para Mystic Explorers construido con Python 3.10+, FastAPI y Arquitectura Hexagonal.

## Requisitos Previos

- Python 3.10 o superior (probado con Python 3.14 en Fedora).
- SQLite3 (incluido con Python por defecto).

---

## Instalación y Configuración

1. **Crear el Entorno Virtual (`venv`)**:
   ```bash
   cd /var/www/html/ME_backend
   python3 -m venv venv
   ```

2. **Activar el entorno e instalar dependencias**:
   ```bash
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configurar Variables de Entorno (`.env`)**:
   Copia el archivo de ejemplo si no existe:
   ```bash
   cp .env.example .env
   ```
   *La configuración por defecto utiliza SQLite (`database.db`).*

---

## Ejecución del Servidor

### Opción A: Mediante el script de inicio
```bash
cd /var/www/html/ME_backend
./start.sh
```

### Opción B: Ejecución directa con Uvicorn
```bash
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

* **Documentación interactiva de la API (Swagger UI)**: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
* **Especificación OpenAPI (JSON)**: [http://127.0.0.1:8001/openapi.json](http://127.0.0.1:8001/openapi.json)

> [!NOTE]
> El servidor escucha en `0.0.0.0:8001` para permitir conexiones tanto desde la web local como desde dispositivos móviles o emuladores en la red.

---

## Mantenimiento y Base de Datos

### Reiniciar el Mundo y la Base de Datos
Para borrar el progreso y regenerar el mundo limpio:
```bash
./reset_db.sh
```

---

## Herramientas de Desarrollo

### Visualizador del Mundo en Terminal
Script utilitario para visualizar la cuadrícula del mapa y la posición del jugador en tiempo real:

```bash
# Con el entorno virtual activo:
python scripts/visualize_world.py [NombreDelJugador]

# Ejemplo:
./venv/bin/python scripts/visualize_world.py Hero
```

---

## Pruebas Automatizadas

Ejecutar la suite de tests con `pytest`:
```bash
./venv/bin/pytest
# o con el venv activo:
pytest
```

---

## Cliente Frontend y Aplicación Móvil (Android / APK)

Para instrucciones sobre cómo ejecutar la web, sincronizar Capacitor y compilar el APK para Android:
- [Guía del Frontend (README)](file:///var/www/html/ME_frontend/README.md)
- [Guía de Compilación Móvil Android (Capacitor)](file:///var/www/html/ME_frontend/docs/mobile_build_guide.md)
