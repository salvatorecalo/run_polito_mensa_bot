# Database Schema - Polito Mensa Bot

## Overview

Il database è strutturato per supportare l'evoluzione da script semplice a servizio scalabile, seguendo i principi del **Repository Pattern** e utilizzando **SQLModel** per l'ORM asincrono.

## Entity Relationship Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│      User       │    │   Subscription  │    │     Canteen     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (PK)         │◄──┐│ id (PK)         │┌──►│ id (PK)         │
│ chat_id (UQ)    │   ││ user_id (FK)    ││   │ name            │
│ username        │   ││ canteen_id (FK) ││   │ slug (UQ)       │
│ first_name      │   ││ meal_types      ││   │ instagram_user  │
│ preferences     │   ││ is_active       ││   │ location        │
│ created_at      │   └┤ created_at      │└───┤ is_active       │
│ updated_at      │    │ updated_at      │    │ created_at      │
└─────────────────┘    └─────────────────┘    │ updated_at      │
                                              └─────────────────┘
                                                       │
                                                       │
                                              ┌─────────────────┐
                                              │      Menu       │
                                              ├─────────────────┤
                                              │ id (PK)         │
                                              │ canteen_id (FK) │◄──┘
                                              │ date            │
                                              │ meal_type       │
                                              │ raw_text        │
                                              │ processed_cont  │
                                              │ status          │
                                              │ created_at      │
                                              │ updated_at      │
                                              └─────────────────┘
```

## Tables

### users
Gestisce gli utenti Telegram e le loro preferenze.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,  -- Telegram chat ID
    username VARCHAR(255),           -- Telegram username (@username)
    first_name VARCHAR(255),         -- Nome dell'utente
    preferences JSON,                -- Preferenze meal types e notifiche
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_chat_id ON users(chat_id);
CREATE INDEX idx_users_username ON users(username) WHERE username IS NOT NULL;
```

**Esempio preferences JSON:**
```json
{
  "meal_types": ["LUNCH", "DINNER"],
  "notifications_enabled": true,
  "language": "it",
  "timezone": "Europe/Rome"
}
```

### canteens
Definisce le mense disponibili e i loro metadati.

```sql
CREATE TYPE canteen_status AS ENUM ('ACTIVE', 'INACTIVE', 'MAINTENANCE');

CREATE TABLE canteens (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- "Mensa Centrale"
    slug VARCHAR(100) NOT NULL UNIQUE,       -- "centrale" 
    instagram_username VARCHAR(255) NOT NULL, -- "polito_centrale"
    location VARCHAR(255),                   -- "Corso Duca degli Abruzzi, 24"
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_canteens_slug ON canteens(slug);
CREATE INDEX idx_canteens_instagram ON canteens(instagram_username);
CREATE INDEX idx_canteens_active ON canteens(is_active) WHERE is_active = true;
```

### menus
Archivia i menu estratti con stato di processing.

```sql
CREATE TYPE meal_type AS ENUM ('LUNCH', 'DINNER');
CREATE TYPE menu_status AS ENUM ('RAW', 'PROCESSED', 'SENT', 'ERROR');

CREATE TABLE menus (
    id SERIAL PRIMARY KEY,
    canteen_id INTEGER NOT NULL REFERENCES canteens(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    meal_type meal_type NOT NULL,
    raw_text TEXT NOT NULL,                  -- Testo estratto da Instagram
    processed_content JSON,                  -- Menu processato e strutturato
    status menu_status DEFAULT 'RAW',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes e Constraints
CREATE UNIQUE INDEX idx_menus_canteen_date_meal ON menus(canteen_id, date, meal_type);
CREATE INDEX idx_menus_date ON menus(date);
CREATE INDEX idx_menus_status ON menus(status);
CREATE INDEX idx_menus_canteen ON menus(canteen_id);
```

**Esempio processed_content JSON:**
```json
{
  "primi": ["Pasta al pomodoro", "Risotto ai funghi"],
  "secondi": ["Cotoletta alla milanese", "Pesce al forno"],
  "contorni": ["Insalata mista", "Verdure grigliate"],
  "dessert": ["Tiramisù", "Frutta"],
  "note": "Menu soggetto a disponibilità",
  "prezzo_completo": "€ 4,50",
  "prezzo_ridotto": "€ 3,50"
}
```

### subscriptions
Gestisce le sottoscrizioni utenti alle mense.

```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    canteen_id INTEGER NOT NULL REFERENCES canteens(id) ON DELETE CASCADE,
    meal_types meal_type[] NOT NULL DEFAULT '{LUNCH}',  -- Array di meal types
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes e Constraints
CREATE UNIQUE INDEX idx_subscriptions_user_canteen ON subscriptions(user_id, canteen_id);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_canteen ON subscriptions(canteen_id);
CREATE INDEX idx_subscriptions_active ON subscriptions(is_active) WHERE is_active = true;
CREATE INDEX idx_subscriptions_meal_types ON subscriptions USING GIN(meal_types);
```

## Business Logic

### User Management
```python
# Repository pattern per operazioni utente
async def get_or_create_user_by_chat_id(chat_id: int) -> User:
    """Trova o crea utente per chat_id Telegram"""
    
async def update_user_preferences(user_id: int, preferences: dict) -> User:
    """Aggiorna preferenze utente"""
```

### Menu Processing Pipeline
```python
# 1. Scraping (Producer)
menu = await menu_repo.create_raw_menu(canteen_id, date, meal_type, raw_text)

# 2. Processing (Background Worker)
processed = await process_menu_text(menu.raw_text)
await menu_repo.mark_as_processed(menu.id, processed)

# 3. Distribution (Bot Consumer) 
subscribers = await subscription_repo.get_subscribers_for_canteen_and_meal(
    canteen_id, meal_type
)
await telegram_service.send_menu_to_subscribers(menu, subscribers)
await menu_repo.mark_as_sent(menu.id)
```

### Subscription Management
```python
# Subscribe utente a una mensa
await subscription_repo.subscribe_user_to_canteen(
    user_id, canteen_id, meal_types=['LUNCH', 'DINNER']
)

# Unsubscribe
await subscription_repo.unsubscribe_user_from_canteen(user_id, canteen_id)

# Get subscribers per delivery
subscribers = await subscription_repo.get_active_subscribers_for_delivery(
    canteen_id, meal_type='LUNCH'
)
```

## Data Migration Strategy

### Phase 1: Coexistence
- Mantenere JSON files come fallback
- Implementare graduale migration dei dati
- Repository pattern per interfaccia unificata

### Phase 2: Full Migration  
- Migrare tutti i dati da JSON a PostgreSQL
- Disabilitare file-based storage
- Cleanup codice legacy

### Phase 3: Optimization
- Indici per performance queries
- Archivio dati storici (monthly partitioning)
- Caching layer con Redis

## Performance Considerations

### Indexing Strategy
```sql
-- Query per subscribers attivi
CREATE INDEX idx_active_subscriptions 
ON subscriptions(canteen_id, meal_types) 
WHERE is_active = true;

-- Query per menu recenti
CREATE INDEX idx_recent_menus 
ON menus(date DESC, status) 
WHERE date >= CURRENT_DATE - INTERVAL '30 days';

-- Search utenti per username/nome
CREATE INDEX idx_users_search 
ON users USING gin(to_tsvector('italian', coalesce(username, '') || ' ' || coalesce(first_name, '')));
```

### Connection Pooling
```python
# AsyncPG connection pool
database_manager = DatabaseManager(
    database_url=settings.database_url,
    min_connections=5,
    max_connections=20,
    max_idle=300  # 5 minutes
)
```

### Caching Strategy
- **Redis**: Cache utenti attivi e loro preferenze
- **Application**: Cache configurazioni mense
- **Database**: Materialized views per statistiche

## Monitoring & Analytics

### Key Metrics
```sql
-- Utenti attivi per periodo
SELECT COUNT(DISTINCT user_id) 
FROM subscriptions 
WHERE is_active = true;

-- Menu processati per giorno
SELECT date, COUNT(*) 
FROM menus 
WHERE status = 'SENT' 
GROUP BY date 
ORDER BY date DESC;

-- Mense più popolari
SELECT c.name, COUNT(s.id) as subscribers
FROM canteens c
LEFT JOIN subscriptions s ON c.id = s.canteen_id AND s.is_active = true
GROUP BY c.id, c.name
ORDER BY subscribers DESC;
```

### Health Checks
- Connessione database disponibile
- Alembic migrations aggiornate  
- Indici database ottimali
- Storage space disponibile

## Backup & Recovery

### Automated Backups
```bash
# Daily backup con rotation
pg_dump "postgresql://user:pass@host:5432/polito_mensa" \
  | gzip > "backup_$(date +%Y%m%d).sql.gz"
  
# Retention: 7 daily, 4 weekly, 6 monthly
```

### Point-in-Time Recovery
- PostgreSQL WAL archiving
- Backup continuo su storage object
- RTO: < 15 minuti, RPO: < 5 minuti