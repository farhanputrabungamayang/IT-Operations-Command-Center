Set WshShell = CreateObject("WScript.Shell")
' Kita paksa pakai pythonw (Windowless) bukan python biasa
WshShell.Run "pythonw commander.py", 0
Set WshShell = Nothing