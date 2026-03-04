# Backend Technology Stack - Mystic Explorers

The backend is built with a focus on **Hexagonal Architecture** (Ports and Adapters) to ensure maintainability and testability.

## Core Technologies
- **Language**: [Python 3.10+](https://www.python.org/)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance web framework for building APIs.
- **ORM / Models**: [SQLModel](https://sqlmodel.tiangolo.com/) - Combines SQLAlchemy and Pydantic for robust data modeling.
- **Database**: [SQLite](https://www.sqlite.org/) - Lightweight, file-based relational database.
- **Server**: [Uvicorn](https://www.uvicorn.org/) - ASGI server implementation for Python.

## Architecture
- **Pattern**: Hexagonal Architecture.
  - `app/core/domain`: Enterprise business rules (Models).
  - `app/core/use_cases`: Application business rules (Services).
  - `app/adapters/driving`: Input adapters (FastAPI Routes).
  - `app/adapters/driven`: Output adapters (SQL Repository).
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/).
- **Data Lifecycle**: Automated DB initialization and world seeding. See [DATA_MANAGEMENT.md](file:///var/www/html/ME_backend/docs/DATA_MANAGEMENT.md) for details.

## Development & Testing
- **Testing Framework**: [Pytest](https://docs.pytest.org/).
- **API Testing**: [HTTPX](https://www.python-httpx.org/).
- **Environment**: [Python Virtual Environments (venv)](https://docs.python.org/3/library/venv.html).
