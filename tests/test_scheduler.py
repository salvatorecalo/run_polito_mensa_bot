"""
Test suite per bot.scheduler
"""
import pytest
import time
from unittest.mock import Mock, patch
from bot.scheduler import BotScheduler


@pytest.fixture
def scheduler():
    """Crea un'istanza di BotScheduler per i test"""
    return BotScheduler()


class TestBotSchedulerInit:
    """Test per inizializzazione BotScheduler"""
    
    def test_initializes_with_correct_defaults(self, scheduler):
        """Verifica inizializzazione con valori di default corretti"""
        assert scheduler.running is False
        assert scheduler.thread is None


class TestAddDailyTask:
    """Test per add_daily_task"""
    
    @patch('bot.scheduler.schedule.every')
    def test_adds_task_at_specific_time(self, mock_schedule, scheduler):
        """Verifica aggiunta task a un orario specifico"""
        mock_task = Mock()
        mock_day = Mock()
        mock_schedule.return_value.day = mock_day
        
        scheduler.add_daily_task(mock_task, 14, 30)
        
        mock_day.at.assert_called_once_with("14:30")
    
    @patch('bot.scheduler.schedule.every')
    def test_formats_time_with_leading_zeros(self, mock_schedule, scheduler):
        """Verifica formattazione orario con zeri iniziali"""
        mock_task = Mock()
        mock_day = Mock()
        mock_schedule.return_value.day = mock_day
        
        scheduler.add_daily_task(mock_task, 9, 5)
        
        mock_day.at.assert_called_once_with("09:05")
    
    @patch('bot.scheduler.schedule.every')
    def test_accepts_midnight(self, mock_schedule, scheduler):
        """Verifica accettazione mezzanotte come orario"""
        mock_task = Mock()
        mock_day = Mock()
        mock_schedule.return_value.day = mock_day
        
        scheduler.add_daily_task(mock_task, 0, 0)
        
        mock_day.at.assert_called_once_with("00:00")
    
    @patch('bot.scheduler.schedule.every')
    def test_accepts_end_of_day(self, mock_schedule, scheduler):
        """Verifica accettazione 23:59 come orario"""
        mock_task = Mock()
        mock_day = Mock()
        mock_schedule.return_value.day = mock_day
        
        scheduler.add_daily_task(mock_task, 23, 59)
        
        mock_day.at.assert_called_once_with("23:59")


class TestAddDefaultSchedules:
    """Test per add_default_schedules"""
    
    @patch('bot.scheduler.BotScheduler.add_daily_task')
    @patch('bot.scheduler.SCHEDULE_TIMES', [{"hour": 11, "minute": 25}, {"hour": 20, "minute": 0}])
    def test_adds_all_default_schedules(self, mock_add_task, scheduler):
        """Verifica aggiunta di tutti gli orari di default"""
        mock_task = Mock()
        
        scheduler.add_default_schedules(mock_task)
        
        assert mock_add_task.call_count == 2
        mock_add_task.assert_any_call(mock_task, 11, 25)
        mock_add_task.assert_any_call(mock_task, 20, 0)
    
    @patch('bot.scheduler.BotScheduler.add_daily_task')
    @patch('bot.scheduler.SCHEDULE_TIMES', [])
    def test_handles_empty_schedule_times(self, mock_add_task, scheduler):
        """Verifica gestione lista orari vuota"""
        mock_task = Mock()
        
        scheduler.add_default_schedules(mock_task)
        
        mock_add_task.assert_not_called()


class TestStart:
    """Test per start"""
    
    def test_sets_running_to_true(self, scheduler):
        """Verifica che running venga impostato a True"""
        with patch.object(scheduler, '_run'):
            scheduler.start()
            
            assert scheduler.running is True
    
    def test_creates_thread(self, scheduler):
        """Verifica creazione thread"""
        with patch.object(scheduler, '_run'):
            scheduler.start()
            
            assert scheduler.thread is not None
            assert scheduler.thread.daemon is True
    
    def test_does_not_start_if_already_running(self, scheduler):
        """Verifica che non avvii se già in esecuzione"""
        scheduler.running = True
        original_thread = Mock()
        scheduler.thread = original_thread
        
        scheduler.start()
        
        # Thread non dovrebbe essere cambiato
        assert scheduler.thread is original_thread


class TestStop:
    """Test per stop"""
    
    def test_sets_running_to_false(self, scheduler):
        """Verifica che running venga impostato a False"""
        scheduler.running = True
        
        scheduler.stop()
        
        assert scheduler.running is False
    
    def test_waits_for_thread_to_finish(self, scheduler):
        """Verifica attesa completamento thread"""
        mock_thread = Mock()
        scheduler.thread = mock_thread
        scheduler.running = True
        
        scheduler.stop()
        
        mock_thread.join.assert_called_once_with(timeout=5)
    
    def test_handles_no_thread(self, scheduler):
        """Verifica gestione caso senza thread"""
        scheduler.thread = None
        scheduler.running = True
        
        # Non dovrebbe sollevare eccezioni
        scheduler.stop()
        
        assert scheduler.running is False


class TestRun:
    """Test per _run (metodo interno)"""
    
    @patch('bot.scheduler.schedule.run_pending')
    @patch('bot.scheduler.time.sleep')
    def test_runs_pending_tasks(self, mock_sleep, mock_run_pending, scheduler):
        """Verifica esecuzione task pendenti"""
        scheduler.running = True
        
        # Simula stop dopo una iterazione
        def stop_after_one(*args, **kwargs):
            scheduler.running = False
        
        mock_sleep.side_effect = stop_after_one
        
        scheduler._run()
        
        mock_run_pending.assert_called()
    
    @patch('bot.scheduler.schedule.run_pending')
    @patch('bot.scheduler.time.sleep')
    def test_sleeps_between_checks(self, mock_sleep, mock_run_pending, scheduler):
        """Verifica pausa tra controlli"""
        scheduler.running = True
        
        def stop_after_one(*args, **kwargs):
            scheduler.running = False
        
        mock_sleep.side_effect = stop_after_one
        
        scheduler._run()
        
        mock_sleep.assert_called_with(30)
    
    @patch('bot.scheduler.schedule.run_pending')
    @patch('bot.scheduler.time.sleep')
    def test_stops_when_running_becomes_false(self, mock_sleep, mock_run_pending, scheduler):
        """Verifica interruzione quando running diventa False"""
        scheduler.running = True
        iteration_count = [0]
        
        def count_and_stop(*args):
            iteration_count[0] += 1
            if iteration_count[0] >= 3:
                scheduler.running = False
        
        mock_sleep.side_effect = count_and_stop
        
        scheduler._run()
        
        # Dovrebbe aver fatto 3 iterazioni
        assert iteration_count[0] == 3


class TestIntegration:
    """Test di integrazione"""
    
    @patch('bot.scheduler.time.sleep')
    def test_full_lifecycle(self, mock_sleep, scheduler):
        """Test ciclo completo: start -> run -> stop"""
        mock_task = Mock()
        
        # Simula sleep che ferma dopo poche iterazioni
        iteration = [0]
        def limited_sleep(*args):
            iteration[0] += 1
            if iteration[0] >= 2:
                scheduler.stop()
        
        mock_sleep.side_effect = limited_sleep
        
        # Aggiungi task
        scheduler.add_daily_task(mock_task, 12, 0)
        
        # Avvia scheduler
        scheduler.start()
        
        # Attendi un momento
        time.sleep(0.1)
        
        # Ferma
        scheduler.stop()
        
        assert scheduler.running is False
