@echo off
REM poll-terry.cmd -- Check BinkP feedback during Terry's active hours (ET)
REM Terry is in Cairns AEST (UTC+10).  Active roughly 7am-midnight AEST
REM = 5pm-10am ET.  Run hourly via wcTaskMgr; time-window guard skips
REM the 10am-5pm ET block when Terry is asleep.
REM WorkingDir set by wcTaskMgr to c:\local\claude\wcBinkp\

set LOG=c:\local\claude\wcBinkp\feedback.log

REM Allow operator escape (press Esc within 10 sec to skip this run)
wait32 10
if errorlevel 1 (
    echo %DATE% %TIME% -- operator escape, skipping. >> "%LOG%"
    goto :eof
)

REM Time-window guard: skip 10am-5pm ET (Terry asleep)
set HOUR=%TIME:~0,2%
set HOUR=%HOUR: =0%

if %HOUR% GEQ 10 if %HOUR% LSS 17 goto :quiet

REM Active window -- poll
echo %DATE% %TIME% -- polling BinkP feedback... >> "%LOG%"
python "c:\local\claude\wcBinkp\check-binkp-feedback.py" --state detect-terry.state >> "%LOG%" 2>&1
goto :eof

:quiet
echo %DATE% %TIME% -- outside Terry active window (10am-5pm ET), skipping. >> "%LOG%"
