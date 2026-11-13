@echo off
rem Starts the NHL 94 Helper in its stream mode: every game is recorded as usual, and live stats for OBS are
rem written to Documents\NHL94 Viewer\live (overlay: http://localhost:9494/overlay.html). Keep this file next to
rem "NHL94 Helper.exe".
"%~dp0NHL94 Helper.exe" --live-local
