from typing import Optional, List
import os
import sys
import signal

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from gis4wrf.core import run_program, UserError


_THREADS = [] # type: List[QThread]

class Task(QObject):
    ''' Non-threaded alternative to TaskThread, useful for debugging. '''
    started = pyqtSignal()
    progress = pyqtSignal(int, str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(tuple)
    finished = pyqtSignal()

    def __init__(self, fn, yields_progress: bool=False) -> None:
        super().__init__()
        self.fn = fn
        self.yields_progress = yields_progress
        self.result = None
        self.exc_info = None

    def start(self):
        self.started.emit()
        try:
            if self.yields_progress:
                for percent, status in self.fn():
                    self.progress.emit(percent, status)
            else:
                self.result = self.fn()
            self.succeeded.emit(self.result)
        except:
            self.exc_info = sys.exc_info()
            self.failed.emit(self.exc_info)
        finally:
            self.finished.emit()

class TaskThread(QThread):
    progress = pyqtSignal(int, str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(tuple)
    # QThread provides started & finished signals.

    def __init__(self, fn, yields_progress: bool=False) -> None:
        super().__init__()
        
        task = Task(fn, yields_progress)
        task.progress.connect(self.progress)
        task.succeeded.connect(self.succeeded)
        task.failed.connect(self.failed)
        self.task = task

        # need to keep reference alive while thread is running
        _THREADS.append(self)

    def run(self):
        self.task.start()

class ProgramThread(QThread):
    output = pyqtSignal(str)

    def __init__(self, path: str, cwd: str, error_pattern: Optional[str]=None,
                 use_mpi: bool=False, mpi_processes: Optional[int]=None) -> None:
        super().__init__()
        self.path = path
        self.cwd = cwd
        self.error_pattern = error_pattern
        self.use_mpi = use_mpi
        self.mpi_processes = mpi_processes
        self.pid = -1
        self.error = None
        self.exc_info = None

        # need to keep reference alive while thread is running
        _THREADS.append(self)

    def run(self):
        try:
            for msg_type, msg_val in run_program(self.path, self.cwd, self.error_pattern,
                                                 self.use_mpi, self.mpi_processes):
                if msg_type == 'pid':
                    self.pid = msg_val
                elif msg_type == 'log':
                    self.output.emit(msg_val)
                elif msg_type == 'error':
                    self.error = msg_val
                else:
                    raise RuntimeError('Invalid output received: {}'.format(msg_type))
        except:
            self.exc_info = sys.exc_info()

    def kill_program(self):
        if self.pid == -1:
            raise UserError('Program not started yet')
        os.kill(self.pid, signal.SIGTERM)