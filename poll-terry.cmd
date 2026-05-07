@echo off
REM poll-terry.cmd -- Check BinkP feedback during Terry's active hours (ET)
REM Terry is in Cairns AEST (UTC+10).  Active roughly 7am-midnight AEST
REM = 5pm-10am ET.  Run this every 30 min; skip if outside that window.
REM Scheduled via Task Scheduler: WcBinkP-Terry-Poll (daily 17:00, 30min repeat, 17h)

set HOUR=%TIME:~0,2%
set HOUR=%HOUR: =0%

REM Outside window: 10am-17pm ET (skip)
if %HOUR% GEQ 10 if %HOUR% LSS 17 (
    echo %DATE% %TIME% -- outside Terry active window (10am-5pm ET), skipping.
    exit /b 0
)

echo %DATE% %TIME% -- polling BinkP feedback...
python "c:\local\claude\wcBinkp\check-binkp-feedback.py" >> "c:\local\claude\wcBinkp\feedback.log" 2>&1
