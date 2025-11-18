#!/bin/bash
# Script di test del database e validazione dell'ambiente

set -e

echo "🔧 Avvio test ambiente di sviluppo..."

# Verifica Python e pacchetti
echo "🐍 Verifica Python e dipendenze..."
python --version
pip list | grep -E "(sqlmodel|alembic|asyncpg|pydantic)" || echo "⚠️  Alcune dipendenze potrebbero mancare"

# Test connessione PostgreSQL
echo "🗄️  Test connessione PostgreSQL..."
# Try Docker service first
if nc -z postgresql 5432 2>/dev/null; then
    echo "✅ PostgreSQL raggiungibile su postgresql:5432 (Docker service)"
elif nc -z localhost 5432 2>/dev/null; then
    echo "✅ PostgreSQL raggiungibile su localhost:5432"
else
    echo "⚠️  PostgreSQL non raggiungibile (normale senza servizi Docker avviati)"
fi

# Test connessione Redis
echo "🔄 Test connessione Redis..."
# Try Docker service first
if nc -z redis 6379 2>/dev/null; then
    echo "✅ Redis raggiungibile su redis:6379 (Docker service)"
elif nc -z localhost 6379 2>/dev/null; then
    echo "✅ Redis raggiungibile su localhost:6379"
else
    echo "⚠️  Redis non raggiungibile (normale senza servizi Docker avviati)"
fi

# Test Alembic
echo "🔄 Verifica configurazione Alembic..."
if alembic check 2>/dev/null; then
    echo "✅ Alembic configurato correttamente"
else
    echo "⚠️  Alembic: potrebbero essere necessarie migrazioni"
fi

# Test import SQLModel
echo "🧪 Test import modelli database..."
python -c "
try:
    from models_simple import User, Canteen, Menu, Subscription
    print('✅ Tutti i modelli semplificati importati correttamente')
    
    # Test creazione modelli
    user = User(chat_id=123, username='test')
    print('✅ Test creazione User successful')
    
    canteen = Canteen(name='Test Canteen', slug='test')
    print('✅ Test creazione Canteen successful')
    
except Exception as e:
    print(f'❌ Errore import modelli: {e}')
    exit(1)
" || echo "❌ Errore nell'importazione dei modelli"

# Test configurazione
echo "⚙️  Test configurazione..."
python -c "
try:
    from config.settings import settings
    print(f'✅ Configurazione caricata: DB={settings.database_url_sync[:20]}...')
except Exception as e:
    print(f'❌ Errore configurazione: {e}')
" || echo "❌ Errore nella configurazione"

echo "🎉 Test ambiente completato!"
echo ""
echo "📋 Prossimi passi suggeriti:"
echo "   1. Esegui 'alembic revision --autogenerate -m \"Initial schema\"'"
echo "   2. Esegui 'alembic upgrade head'"
echo "   3. Testa l'applicazione con 'python main.py'"
echo ""