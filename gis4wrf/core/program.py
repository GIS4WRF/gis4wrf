from typing import Optional, List, Iterable, Tuple, Any
import os
import sys
import platform
import subprocess
import multiprocessing
import time

from gis4wrf.core.util import export

@export
def run_program(path: str, cwd: str, error_pattern: Optional[str]=None,
                use_mpi: bool=False, mpi_processes: Optional[int]=None) -> Iterable[Tuple[str,Any]]:
    if use_mpi:
        if mpi_processes is None:
            mpi_processes = multiprocessing.cpu_count()
        plat = platform.system()
        if plat == 'Windows':
            # Microsoft MPI
            mpi_path = os.path.join(os.environ['MSMPI_BIN'], 'mpiexec.exe')
        elif plat in ['Darwin', 'Linux']:
            # MPICH (most likely)
            mpi_path = 'mpiexec'
        else:
            raise NotImplementedError('MPI not supported on ' + plat)
        args = [mpi_path, '-n', str(mpi_processes), path]
    else:
        args = [path]

    return _run_program(args, cwd, error_pattern)

def _run_program(args: List[str], cwd: str, error_pattern: Optional[str]=None) -> Iterable[Tuple[str,Any]]:
    yield ('log', 'Command: ' + ' '.join(args))
    yield ('log', 'Working directory: ' + cwd)
    startupinfo = None
    if os.name == 'nt':
        # hides the console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    t0 = time.time()
    process = subprocess.Popen(args, cwd=cwd,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             bufsize=1, universal_newlines=True,
                             startupinfo=startupinfo)
    yield ('pid', process.pid)
    stdout = ''
    while True:
        line = process.stdout.readline()
        if line != '':
            stdout += line
            yield ('log', line.rstrip())
        else:
            break
    process.wait()
    if process.returncode != 0:
        yield ('log', 'Exit code: {}'.format(process.returncode))
    yield ('log', 'Runtime: {} s'.format(int(time.time() - t0)))

    error = process.returncode != 0
    if not error and error_pattern:
        error = error_pattern in stdout
    yield ('error', error)