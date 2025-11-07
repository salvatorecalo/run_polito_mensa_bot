"""
Scheduler per esecuzione periodica di task
"""
import schedule
import time
from threading import Thread
from typing import Callable
from config import SCHEDULE_TIMES
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BotScheduler:
    """Gestisce la schedulazione di task periodici"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def add_daily_task(self, task: Callable, hour: int, minute: int) -> None:
        """
        Aggiunge un task da eseguire giornalmente a un orario specifico.
        
        Args:
            task: Funzione da eseguire
            hour: Ora di esecuzione (0-23)
            minute: Minuto di esecuzione (0-59)
        """
        time_str = f"{hour:02d}:{minute:02d}"
        schedule.every().day.at(time_str).do(task)
        logger.info(f"⏰ Task schedulato per le {time_str}")
    
    def add_default_schedules(self, task: Callable) -> None:
        """
        Aggiunge gli orari di default dalla configurazione.
        
        Args:
            task: Funzione da eseguire agli orari configurati
        """
        for schedule_time in SCHEDULE_TIMES:
            self.add_daily_task(
                task,
                schedule_time["hour"],
                schedule_time["minute"]
            )
    
    def _run(self) -> None:
        """Loop interno dello scheduler"""
        logger.info("▶️ Scheduler avviato")
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check ogni 30 secondi
        logger.info("⏹️ Scheduler fermato")
    
    def start(self) -> None:
        """Avvia lo scheduler in un thread separato"""
        if self.running:
            logger.warning("⚠️ Scheduler già in esecuzione")
            return
        
        self.running = True
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("✅ Scheduler avviato in background")
    
    def stop(self) -> None:
        """Ferma lo scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✅ Scheduler fermato")
