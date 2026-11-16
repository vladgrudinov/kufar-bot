Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\grudinov.vi\Downloads\kufar_pc_bot"
WshShell.Run """C:\Python314\pythonw.exe"" main.py", 0, False
