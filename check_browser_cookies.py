import os
import sqlite3
import shutil

chrome_cookies = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies'
edge_cookies = os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data\Default\Network\Cookies'

for name, path in [('Chrome', chrome_cookies), ('Edge', edge_cookies)]:
    if os.path.exists(path):
        temp_path = f'temp_cookies_{name}.db'
        try:
            shutil.copyfile(path, temp_path)
            conn = sqlite3.connect(temp_path)
            rows = conn.execute("SELECT host_key, name FROM cookies WHERE host_key LIKE '%kufar%'").fetchall()
            print(f'{name} has {len(rows)} kufar cookies.')
            for r in rows[:8]:
                print(' ', r)
            conn.close()
            os.remove(temp_path)
        except Exception as e:
            print(f'{name} error: {e}')
    else:
        print(f'{name} cookies path not found: {path}')
