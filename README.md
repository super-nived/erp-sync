# ERP Sync Service

ERP data synchronization service following the MPS BE architecture.

This is a **boilerplate template** with infrastructure code ready for implementing sync-specific features.

## 🏗️ Architecture

This project follows the same architecture as **MPS BE** as defined in `spec.md`:

```
erp-sync/
├── app/
│   ├── core/          # Global concerns (settings, logging, exceptions)
│   ├── db/            # Database layer (PocketBase, SQL clients)
│   ├── utils/         # Utility functions
│   ├── middlewares/   # FastAPI middlewares
│   ├── api/           # API endpoints (health check)
│   ├── features/      # Feature modules (add sync logic here)
│   └── main.py        # Application entry point
├── .env               # Environment configuration (create from .env.example)
├── requirements.txt   # Python dependencies
└── spec.md            # Project specification
```

## ✅ What's Included (Reused from MPS BE)

### Core Layer
- ✅ Settings management (`settings.py`)
- ✅ Logging configuration (`logging.py`)
- ✅ Exception handling (`exceptions.py`, `handlers.py`)
- ✅ Lifespan events (`events.py`, `startup.py`)
- ✅ Security/Authentication (`security.py`)

### Database Layer
- ✅ PocketBase client (`client.py`)
- ✅ SQL client (`sql_client.py`)
- ✅ Collection management (`collections.py`)

### Utilities
- ✅ Response helpers (`response.py`)
- ✅ Pagination utilities (`pagination.py`)

### Middlewares
- ✅ Request logging (`logging_middleware.py`)
- ✅ Authentication (`auth.py`)

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- PocketBase instance running
- SQL Server (optional, if using SQL client)

### Installation

1. **Clone/Navigate to the project**
   ```bash
   cd erp-sync
   ```

2. **Create virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The service will start at: `http://localhost:8000`

### Verify Installation

- **Health Check**: `http://localhost:8000/health`
- **API Docs**: `http://localhost:8000/docs`

Expected health check response:
```json
{
  "status": "healthy",
  "service": "erp-sync",
  "version": "1.0.0"
}
```

## 📝 Environment Variables

Create a `.env` file based on `.env.example`:

```env
# PocketBase Configuration
POCKETBASE_URL=http://127.0.0.1:8090
POCKETBASE_ADMIN_EMAIL=admin@example.com
POCKETBASE_ADMIN_PASSWORD=your_password

# SQL Server Configuration (Optional)
SQL_SERVER=your_sql_server
SQL_DATABASE=your_database
SQL_USERNAME=your_username
SQL_PASSWORD=your_password

# Plant Configuration
PLANT_CODE=ASWNDUBAI

# Application
DEBUG=True
LOG_LEVEL=INFO
```

## 🔧 Adding Sync Features

To add new sync features, create modules in `app/features/`:

### Example: Create a data sync feature

```
app/features/data_sync/
├── __init__.py
├── router.py       # API endpoints
├── service.py      # Business logic
├── repo.py         # Data access
└── schema.py       # Pydantic models
```

Then register the router in `app/main.py`:

```python
from app.features.data_sync.router import router as data_sync_router

# In create_app():
app.include_router(data_sync_router)
```

## 📚 Database Collections

The following collections are configured for ERP sync:

- `ASWNDUBAI_erpConsolidateData` - ERP source data
- `ASWNDUBAI_syncLog` - Sync execution logs
- `ASWNDUBAI_syncConfig` - Sync configuration
- `ASWNDUBAI_syncError` - Sync error tracking

To add/modify collections, edit `app/db/collections.py`.

## 🧪 Development

### Run with auto-reload
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Check logs
Logs are written to both console and `logs/app.log`

### Code Standards
Follow the architecture rules in `spec.md`:
- ❌ No business logic in `main.py`
- ❌ No database queries in `core/`
- ❌ No feature code outside `features/`
- ✅ All configuration in `settings.py`
- ✅ Single responsibility per file

## 🔒 Security

- Admin credentials in `.env` (never commit)
- JWT token validation enabled
- CORS configured (adjust in `main.py` for production)

## 📖 Documentation

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`
- **Architecture**: See `spec.md`

## 🎯 Next Steps

1. ✅ Verify the boilerplate runs
2. ✅ Check health endpoint works
3. ✅ Review `spec.md` architecture rules
4. 📝 Design your sync features
5. 🚀 Implement features in `app/features/`

## 📞 Support

For architecture questions, refer to `spec.md` or the MPS BE project.

---

**Built with ❤️ following MPS BE architecture**
