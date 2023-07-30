import sys
from subprocess import CompletedProcess as OGCompletedProcess

if sys.version_info < (3, 9):
    CompletedProcess = OGCompletedProcess
else:
    CompletedProcess = OGCompletedProcess[str]
