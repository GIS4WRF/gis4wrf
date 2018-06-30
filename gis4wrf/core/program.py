from typing import Optional, Iterable, Tuple, Any
import os
import sys
import subprocess

from gis4wrf.core.util import export

@export
def run_program(path: str, cwd: str, error_pattern: Optional[str]=None) -> Iterable[Tuple[str,Any]]:
    startupinfo = None
    if os.name == 'nt':
        # hides the console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen([path], cwd=cwd,
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

    error = process.returncode != 0
    if not error and error_pattern:
        error = error_pattern in stdout
    yield ('error', error)