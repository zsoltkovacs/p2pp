@ECHO OFF
mypath=%~dp1
c:\python27\python.exe $mypath\p2pp.py -i %1
pause
