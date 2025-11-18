# Polito Mensa Bot - Development Environment

Environment di sviluppo modernizzato per il bot Telegram delle mense del Politecnico di Torino.

## 🚀 Quick Start

### 1. Apri in Dev Container
```bash
# VS Code: Command Palette > "Dev Containers: Reopen in Container"
# O clona e apri direttamente
git clone <repo-url>
code run_polito_mensa_bot
```

### 2. Verifica Environment 
```bash
# Testa l'ambiente di sviluppo
./scripts/test-environment.sh
```

### 3. Configura le Variabili
```bash
# Copia e modifica il file .env
cp .env.example .env
# Modifica con i tuoi token Telegram e credenziali Instagram
```

### 4. Avvia il Bot
```bash
python main.py
```

## 🏗️ Architettura

### Database (PostgreSQL + SQLModel)
- **Models**: User, Canteen, Menu, Subscription con relationships
- **Repositories**: Pattern Repository per clean data access
- **Migrations**: Alembic per gestione schema database

### Bot Framework
- **Handlers**: Gestori comandi Telegram
- **Scheduler**: Invio automatico menu con APScheduler  
- **Services**: Instagram scraping e Telegram messaging

### Code Quality
- **Pre-commit**: Black, isort, mypy, flake8
- **Testing**: pytest con supporto async
- **Logging**: Loguru per logging strutturato

## 🗃️ Database Models

### User
```python
- id: int (PK)
- chat_id: int (Unique) 
- username: str (Optional)
- first_name: str (Optional)
- preferences: JSON (meal types, notifications)
- created_at: datetime
- updated_at: datetime
```

### Canteen
```python
- id: int (PK)
- name: str
- slug: str (Unique) 
- instagram_username: str
- location: str (Optional)
- is_active: bool
```

### Menu  
```python
- id: int (PK)
- canteen_id: int (FK)
- date: date
- meal_type: MealType (LUNCH/DINNER)
- raw_text: str
- processed_content: JSON (Optional)
- status: MenuStatus (RAW/PROCESSED/SENT)
```

### Subscription
```python
- id: int (PK)
- user_id: int (FK)
- canteen_id: int (FK)  
- meal_types: List[MealType]
- is_active: bool
```

## 🔧 Commands

### Database
```bash
# Crea migration
alembic revision --autogenerate -m "Description"

# Applica migrations
alembic upgrade head

# Rollback migration 
alembic downgrade -1
```

### Development
```bash
# Code quality checks
pre-commit run --all-files

# Run tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html
```

### Services
```bash
# PostgreSQL (via docker-compose)
docker-compose up postgresql -d

# Redis (via docker-compose)  
docker-compose up redis -d

# Management UIs
docker-compose up pgadmin redis-commander -d
```

## 📊 Development Services

### PostgreSQL
- **Port**: 5432
- **Database**: polito_mensa
- **User**: polito_mensa
- **Password**: polito_mensa_password

### Redis
- **Port**: 6379
- **Password**: None (development)

### Management UIs
- **PgAdmin**: http://localhost:8080 (admin@admin.com / admin)
- **Redis Commander**: http://localhost:8081

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_handlers.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run async tests
pytest tests/test_async_features.py
```

## 📝 Environment Variables

```bash
# .env file template
BOT_TOKEN=your_telegram_bot_token
INSTAGRAM_USERNAME=your_instagram_username  
INSTAGRAM_PASSWORD=your_instagram_password

# Database
DATABASE_URL=postgresql+asyncpg://polito_mensa:polito_mensa_password@localhost:5432/polito_mensa
DATABASE_URL_SYNC=postgresql://polito_mensa:polito_mensa_password@localhost:5432/polito_mensa

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

## 🔄 Development Workflow

1. **Branch/Feature Development**
   ```bash
   git checkout -b feature/new-feature
   # Sviluppa la feature
   pre-commit run --all-files  # Code quality
   pytest                      # Run tests
   ```

2. **Database Changes**
   ```bash
   # Modifica i models in models/
   alembic revision --autogenerate -m "Add new field"
   alembic upgrade head
   ```

3. **Commit & Push**
   ```bash
   git add .
   git commit -m "feat: add new feature"  # Conventional commits
   git push origin feature/new-feature
   ```

## 🚨 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose ps postgresql

# Check database connection
psql postgresql://polito_mensa:polito_mensa_password@localhost:5432/polito_mensa
```

### Migration Issues
```bash
# Check migration status
alembic current
alembic history

# Reset migrations (development only)
rm alembic/versions/*.py
alembic revision --autogenerate -m "Reset initial schema"
```

### Dependencies Issues
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Rebuild dev container
# VS Code: Command Palette > "Dev Containers: Rebuild Container"
```

## 📚 Resources

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/)
- [Pydantic Settings](https://pydantic-docs.helpmanual.io/usage/settings/)