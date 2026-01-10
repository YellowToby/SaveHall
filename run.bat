::@echo off
rem PowershellACC, !QAZXSW@#e21
::echo Starting SaveNexus...
::call venv\Scripts\activate
::python gui\app_gui.py
::pause
@echo off
start cmd /k "cd /d %~dp0 && venv\Scripts\activate && python gui/app_gui.py"
rem PowershellACC, !QAZXSW@#e21
timeout /t 3
start cmd /k "cd /d %~dp0 && venv\Scripts\activate && python gui/web.app.py"
timeout /t 2
start http://localhost:5002