# 🔄 Rebuild Dev Container - Guida Rapida

## Procedura di Rebuild

### 1. Preparazione
```bash
# Assicurarsi che tutti i file siano salvati
# Committare eventuali modifiche importanti
git add -A
git commit -m "Pre-rebuild: prepared Docker setup with PostgreSQL and Redis"
```

### 2. Rebuild Container
**Opzione A - VS Code Command Palette:**
1. `Ctrl+Shift+P` (o `Cmd+Shift+P` su Mac)
2. Cerca: "Dev Containers: Rebuild Container"
3. Seleziona e conferma

**Opzione B - Comando VS Code:**
1. `Ctrl+Shift+P` > "Dev Containers: Rebuild and Reopen in Container"

### 3. Verifica Post-Rebuild
Dopo il rebuild, il container avrà:
- ✅ **PostgreSQL** disponibile su `postgresql:5432`
- ✅ **Redis** disponibile su `redis:6379`  
- ✅ **Setup automatico** tramite `.devcontainer/setup.sh`

### 4. Test Immediato
```bash
# Una volta riaperto il container, esegui:
./scripts/test-environment.sh

# Dovresti vedere:
# ✅ PostgreSQL raggiungibile su postgresql:5432 (Docker service)
# ✅ Redis raggiungibile su redis:6379 (Docker service)
# ✅ Tutti i modelli importati correttamente
```

### 5. Prima Migration
```bash
# Crea la prima migration con i modelli semplificati
alembic revision --autogenerate -m "Initial schema with User, Canteen, Menu, Subscription"

# Applica le migrations
alembic upgrade head

# Verifica il database
python -c "
from sqlalchemy import create_engine, text
from config.settings import settings

engine = create_engine(settings.database_url_sync)
with engine.connect() as conn:
    result = conn.execute(text('SELECT tablename FROM pg_tables WHERE schemaname = \\'public\\';'))
    tables = [row[0] for row in result]
    print('📊 Tables created:', tables)
"
```

## 🚨 Troubleshooting

### Container non si avvia
```bash
# Check dei logs
docker-compose logs devcontainer

# Force rebuild
docker-compose down -v
docker-compose build --no-cache devcontainer
```

### PostgreSQL non raggiungibile
```bash
# Check status servizi
docker-compose ps

# Logs PostgreSQL
docker-compose logs postgresql

# Manual test connection
docker-compose exec postgresql psql -U polito_mensa -d polito_mensa -c "SELECT version();"
```

### Extensions VS Code mancanti
```bash
# Le extensions dovrebbero auto-installarsi
# Se non funziona, installa manualmente:
# - ms-python.python
# - mtxr.sqltools
# - mtxr.sqltools-driver-pg
```

## 📋 Checklist Post-Rebuild

- [ ] Container avviato correttamente
- [ ] PostgreSQL e Redis raggiungibili 
- [ ] Python environment configurato
- [ ] Modelli SQLModel importati
- [ ] Alembic configurato
- [ ] Prima migration creata e applicata
- [ ] Database accessibile e populate

## 🎯 Prossimi Passi

1. **Test completo environment**: `./scripts/test-environment.sh`
2. **Create initial migration**: `alembic revision --autogenerate -m "Initial schema"`
3. **Apply migrations**: `alembic upgrade head`
4. **Start development**: Begin implementing repositories and refactoring handlers
5. **Test bot**: `python main.py` (once ready)

---

**Note**: Il rebuild può richiedere alcuni minuti per scaricare e costruire le immagini Docker. 
Assicurati di avere una connessione internet stabile.