from typing import Optional, List, Iterable, Tuple, Any
import os
import sys
import platform
import subprocess
import multiprocessing
import time

from gis4wrf.core.util import export
from gis4wrf.core.errors import UserError, UnsupportedError

def get_startup_info():
    # This is a function instead of a global because the STARTUPINFO
    # object has to be freshly created for each subprocess call to
    # work around a bug in Python 3.7.0 which was fixed in 3.7.1.
    # See https://bugs.python.org/issue34044.
    if os.name == 'nt':
        # hides the console window
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    else:
        info = None
    return info

@export
def find_mpiexec() -> str:
    plat = platform.system()

    paths = []

    if plat == 'Windows':
        help_option = []
        if 'MSMPI_BIN' in os.environ:
            paths.append(os.path.join(os.environ['MSMPI_BIN'], 'mpiexec.exe'))
    elif plat in ['Darwin', 'Linux']:
        help_option = ['-h']
        paths.append('mpiexec')
        # Sometimes /usr/local/bin is not in PATH.
        paths.append('/usr/local/bin/mpiexec')
    else:
        raise UnsupportedError(f'Platform "{plat}" is not supported')
    
    mpiexec_path = None
    for path in paths:
        try: 
            subprocess.check_output([path] + help_option, startupinfo=get_startup_info())
        except FileNotFoundError:
            pass
        else:
            mpiexec_path = path
            break
    
    if mpiexec_path is None:
        raise UserError('MPI not found')
    
    return mpiexec_path

@export
def run_program(path: str, cwd: str, error_pattern: Optional[str]=None,
                use_mpi: bool=False, mpi_processes: Optional[int]=None) -> Iterable[Tuple[str,Any]]:
    if use_mpi:
        if mpi_processes is None:
            mpi_processes = multiprocessing.cpu_count()
        mpi_path = find_mpiexec()
        args = [mpi_path, '-n', str(mpi_processes), path]
    else:
        args = [path]

    return _run_program(args, cwd, error_pattern)

def _run_program(args: List[str], cwd: str, error_pattern: Optional[str]=None) -> Iterable[Tuple[str,Any]]:
    yield ('log', 'Command: ' + ' '.join(args))
    yield ('log', 'Working directory: ' + cwd)

    t0 = time.time()
    process = subprocess.Popen(args, cwd=cwd,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             bufsize=1, universal_newlines=True,
                             startupinfo=get_startup_info())
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