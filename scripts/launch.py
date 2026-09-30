"""Standard-library launcher and visible key-entry dialog for Windows beginners."""
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent.parent


def stored_key(root=None):
    root=root or ROOT
    env=root/'.env'
    if not env.exists():return ''
    for line in env.read_text(encoding='utf-8').splitlines():
        if line.strip().startswith('GEMINI_API_KEY='):
            return line.strip().split('=',1)[1].strip().strip('"').strip("'")
    return ''


def save_key(key, root=None):
    root=root or ROOT
    key=key.strip()
    if not key or any(c.isspace() for c in key) or any(c in key for c in ('"',"'",'#')):
        raise ValueError('Paste one valid API key, without spaces or extra text.')
    env=root/'.env'
    text=env.read_text(encoding='utf-8') if env.exists() else (root/'.env.example').read_text(encoding='utf-8')
    lines=text.splitlines(); replaced=False
    for i,line in enumerate(lines):
        if line.strip().startswith('GEMINI_API_KEY='):
            lines[i]='GEMINI_API_KEY='+key; replaced=True
    if not replaced:lines.append('GEMINI_API_KEY='+key)
    env.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    try:env.chmod(0o600)
    except OSError:pass


def key_dialog():
    import tkinter as tk
    from tkinter import messagebox
    window=tk.Tk(); window.title('Express Docs - API key setup'); window.geometry('560x290'); window.resizable(False,False)
    window.configure(bg='#f8f7f3')
    saved=[False]
    tk.Label(window,text='Connect your Gemini API key',font=('Segoe UI',17,'bold'),bg='#f8f7f3').pack(pady=(22,8))
    tk.Label(window,text='Paste once with Ctrl+V. Dots confirm that the paste worked.\nYour key stays in this project\'s private .env file.',
        font=('Segoe UI',10),bg='#f8f7f3').pack(pady=5)
    value=tk.StringVar(value=stored_key())
    entry=tk.Entry(window,textvariable=value,show='*',width=55,font=('Segoe UI',12)); entry.pack(pady=13); entry.focus_set()
    reveal=tk.BooleanVar(value=False)
    tk.Checkbutton(window,text='Show key on this screen',variable=reveal,bg='#f8f7f3',
        command=lambda:entry.configure(show='' if reveal.get() else '*')).pack()
    def save():
        try:save_key(value.get())
        except ValueError as exc:messagebox.showerror('Check the key',str(exc)); return
        saved[0]=True; window.destroy()
    tk.Button(window,text='Save key and continue',command=save,font=('Segoe UI',11,'bold'),
        bg='#182b3b',fg='white',padx=25,pady=8).pack(pady=12)
    window.bind('<Return>',lambda event:save())
    window.mainloop()
    return saved[0]


def ensure_environment():
    python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():
        print('Creating the project environment...',flush=True)
        subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True)
    requirements=ROOT/'requirements.txt'; marker=ROOT/'.venv/install.sha256'
    digest=hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not marker.exists() or marker.read_text().strip()!=digest:
        print('Installing dependencies. First run needs internet; keep this window open.',flush=True)
        subprocess.run([str(python),'-m','pip','install','-r',str(requirements)],check=True)
        marker.write_text(digest)
    return python


def open_ready():
    for _ in range(120):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1):
                webbrowser.open('http://127.0.0.1:8000');return
        except OSError:time.sleep(.5)


def main():
    os.chdir(ROOT)
    if sys.version_info<(3,10):raise SystemExit('Python 3.10+ required; verified environment uses Python 3.12.')
    setup_only='--setup-only' in sys.argv
    if setup_only or not (os.getenv('GEMINI_API_KEY','').strip() or stored_key()):
        try:saved=key_dialog()
        except Exception:
            raise SystemExit('Key window could not open. Copy .env.example to .env, enter GEMINI_API_KEY using Notepad, then restart. Never publish .env.')
        if not saved:raise SystemExit('Setup cancelled. Run START.cmd when ready.')
    if setup_only:
        print('Key saved. Restart the application using START.cmd.');return
    python=ensure_environment()
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',8000))
        except OSError:raise SystemExit('Port 8000 is in use. Stop the previous app terminal and try again.')
    print(f'\nProject folder: {ROOT}\nOpening http://127.0.0.1:8000\nKeep this terminal open. Ctrl+C stops the app.\n',flush=True)
    threading.Thread(target=open_ready,daemon=True).start()
    process=subprocess.Popen([str(python),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=ROOT)
    try:code=process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:process.terminate()
        process.wait();code=0
    raise SystemExit(code)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print('Setup failed:',exc);raise SystemExit(1)
