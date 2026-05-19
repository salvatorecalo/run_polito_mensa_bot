# 🍽️ Polito Mensa Bot

Bot Telegram che monitora automaticamente le stories Instagram delle mense Edisu del Politecnico di Torino e invia i menu tradotti in inglese.

## 🎯 Funzionalità

- **Monitoraggio automatico** delle stories Instagram delle mense Edisu
- **Estrazione del testo** dai menu usando groq ai, perchè le immagini che carica attualmente edisu sono difficili da estrapolare con semplice tesseract (22/01/2026)
- **Traduzione automatica** nella lingua scelta dall'utente usando il pacchetto googletrans
- **Invio programmato** su Telegram agli orari dei pasti:
  - 🍝 **11:45** - Menu pranzo
  - 🍕 **18:45** - Menu cena
- **Sistema di iscrizioni** per ricevere aggiornamenti automatici
- **Supporto gruppi** - Aggiungi il bot a un gruppo Telegram

## 🚀 Setup

### Prerequisiti

- Docker e Visual Studio Code con Remote Containers
- Account Instagram
- Bot Telegram (ottieni il token da [@BotFather](https://t.me/botfather))

### Installazione

1. **Clona il repository**
   ```bash
   git clone https://github.com/itsPinguiz/run_polito_mensa_bot.git
   cd run_polito_mensa_bot
   ```

2. **Configura le variabili d'ambiente**
   
   Crea un file `.env` nella root del progetto:
   ```env
   TARGET_USER=target_instagram_account
   TELEGRAM_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

3. **Apri in Dev Container**
   
   - Apri il progetto in VS Code
   - Premi `Ctrl+Shift+P` (o `Cmd+Shift+P` su Mac)
   - Seleziona "Dev Containers: Reopen in Container"
   - Attendi che il container venga costruito

4. **Avvia il bot**
   ```bash
   python main.py
   ```

## 📁 Struttura del Progetto

```
run_polito_mensa_bot/
├── .devcontainer/          # Configurazione Dev Container
├── config/                 # Configurazioni e costanti
│   ├── settings.py        # Variabili d'ambiente
│   └── constants.py       # Costanti applicazione
├── services/              # Servizi esterni
│   ├── instagram_service.py
│   └── telegram_service.py
├── bot/                   # Logica bot Telegram
│   ├── handlers.py        # Command handlers
│   └── scheduler.py       # Task scheduling
├── core/                  # Business logic
│   └── story_processor.py # Download e elaborazione storie
├── data/                  # Storage dati
│   └── subscribers.py     # Gestione iscritti
├── utils/                 # Utilities
│   ├── logger.py
│   ├── file_operations.py
│   └── image_processing.py
├── downloads/             # File temporanei (gitignored)
│   ├── stories/
│   └── created_images/
└── main.py               # Entry point

```

## 🤖 Comandi del Bot

| Comando | Descrizione |
|---------|-------------|
| `/start` | Iscriviti agli aggiornamenti automatici |
| `/cancel` | Disiscriviti dagli aggiornamenti |
| `/help` | Mostra i comandi disponibili |

## 🛠️ Tecnologie Utilizzate

- **Python 3.13**
- **python-telegram-bot** - Interazione con Telegram
- **googletrans** - Traduzione automatica
- **Groq & Pillow** - Elaborazione immagini
- **Docker** - Containerizzazione

## 📝 Note

- Il bot usa un middleman (mollygram attualmente 07/02/2026 per scaricare le storie instagram evitando di essere bannati da instagram, usiamo playwright perchè il sito carica le informazioni in differita con javascript)
- Le immagini vengono create con sfondo arancione e testo bianco
- I file temporanei vengono puliti automaticamente ad ogni esecuzione
- Il bot supporta l'invio di max 10 immagini per volta (limite Telegram)

## 🐛 Troubleshooting

### Bot non riceve comandi
Verifica che il bot abbia i permessi necessari nel gruppo e che il token sia corretto.

## 📄 Licenza

MIT License

## 👤 Autore

[@itsPinguiz](https://github.com/itsPinguiz)
[@SalvatoreCalo]('https://www.github.com/salvatorecalo)
