# PantryPilot
Helps families plan the weekly meals and grocery list

## Proposed structure

```text
pantrypilot/
├── apps/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── api/                  # Routers, endpoints
│   │   │   ├── core/                 # Config, settings, security
│   │   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── crud/                 # Database operations/services
│   │   │   └── dependencies/         # FastAPI dependencies
│   │   ├── alembic/                  # DB migrations
│   │   │   ├── env.py                # Migration environment setup
│   │   │   └── versions/             # Auto-generated migration scripts
│   │   ├── alembic.ini               # Alembic configuration file
│   │   ├── tests/                    # Backend unit & integration tests
│   │   ├── Dockerfile
│   │   └── requirements.txt or pyproject.toml
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/           # UI components
│   │   │   ├── pages/routes/
│   │   │   ├── api/                  # API wrapper (fetch/axios client)
│   │   │   ├── hooks/                # Custom React hooks
│   │   │   ├── types/                # Shared TS types
│   │   │   └── App.tsx, main.tsx, etc.
│   │   ├── public/
│   │   ├── vite.config.ts
│   │   └── package.json
│   └── shared/ (optional)
│       ├── types/                    # Shared types/interfaces
│       └── utils/                    # Shared helper code
├── db/
│   ├── schema.sql or other seeds
│   └── docker-entrypoint scripts
├── docker-compose.yml
├── .env
├── Makefile or tools scripts
├── README.md
└── .gitignore
```
