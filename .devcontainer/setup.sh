#!/bin/bash

# Setup script per dev container modernizzato
set -e

echo "🚀 Setting up Modern Polito Mensa Bot development environment..."

# 1. Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir -r requirements-dev.txt 2>/dev/null || echo "⚠️ requirements-dev.txt not found, skipping"

# 2. Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
if [ -f ".pre-commit-config.yaml" ]; then
    pre-commit install
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️ .pre-commit-config.yaml not found, skipping pre-commit setup"
fi

# 3. Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data
mkdir -p download/stories
mkdir -p download/created_images
mkdir -p alembic/versions

# 4. Wait for PostgreSQL to be ready
echo "🗄️ Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1
while ! nc -z postgresql 5432 2>/dev/null; do
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL not ready after $max_attempts attempts"
        echo "ℹ️ Trying localhost as fallback..."
        if nc -z localhost 5432 2>/dev/null; then
            echo "✅ PostgreSQL available on localhost"
            break
        else
            echo "❌ PostgreSQL not available on localhost either"
            exit 1
        fi
    fi
    echo "⏳ Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
    sleep 2
    ((attempt++))
done
echo "✅ PostgreSQL is ready"

# 5. Initialize database schema with Alembic
echo "🔧 Setting up database schema with Alembic..."
# Check if we need to create initial migration
if [ -z "$(ls -A alembic/versions/ 2>/dev/null)" ]; then
    echo "📝 Creating initial migration..."
    alembic revision --autogenerate -m "Initial migration with User, Canteen, Menu, Subscription tables"
fi

# Apply migrations
echo "⬆️ Running database migrations..."
alembic upgrade head
echo "✅ Database schema ready"

# 6. Setup git hooks (if in git repo)
echo "🔄 Configuring git settings..."
if [ -d ".git" ]; then
    git config --local core.autocrlf false
    git config --local user.email "${GIT_USER_EMAIL:-dev@localhost}" 2>/dev/null || true
    git config --local user.name "${GIT_USER_NAME:-Dev User}" 2>/dev/null || true
    echo "✅ Git configuration updated"
fi

# 7. Install Loguru globally for better logging
echo "📝 Setting up enhanced logging..."
pip install loguru --upgrade

# 8. Test basic imports
echo "🧪 Testing basic imports..."
python3 -c "
try:
    import sqlmodel
    import alembic
    import asyncpg
    import loguru
    import pydantic_settings
    print('✅ All core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# 9. Show summary
echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Summary of available tools:"
echo "  • SQLModel ORM with async support"
echo "  • Alembic for database migrations"  
echo "  • Pre-commit hooks for code quality"
echo "  • Loguru for enhanced logging"
echo "  • PostgreSQL client tools"
echo "  • Redis tools for debugging"
echo ""
echo "🚀 Quick commands:"
echo "  • alembic revision --autogenerate -m 'description'  # Create migration"
echo "  • alembic upgrade head                               # Apply migrations"
echo "  • pre-commit run --all-files                        # Run code quality checks"
echo "  • python main.py                                    # Start the bot"
echo ""
echo "📝 Next steps:"
echo "  1. Configure .env with your credentials"
echo "  2. Run: alembic upgrade head"
echo "  3. Start the bot: python main.py"
echo ""