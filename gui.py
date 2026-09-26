"""Simple desktop chat UI for the local RAG project. Run: python gui.py"""
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from app import ROOT, answer, load_settings
from data.input.local_models import Ollama
from storage import connect

DB_PATH = ROOT / 'data' / 'memory.sqlite3'


class ChatWindow:
    def __init__(self, window):
        self.window = window
        style = ttk.Style()
        style.configure('Danger.TButton', text='white', background='#d32f2f')
        #style.map('Danger.TButton', background=[('active', '#b71c1c'), ('pressed', '#b71c1c')])
        window.title('Assistente local')
        window.geometry('850x650')
        window.minsize(600, 420)
        self.results = queue.Queue()
        self.busy = False
        self.session = tk.StringVar(value='main')
        self.question = tk.StringVar()
        self.status = tk.StringVar(value='Pronto')

        bar = ttk.Frame(window, padding=10)
        bar.pack(fill='x')
        ttk.Label(bar, text='Sessão:').pack(side='left')
        self.sessions = ttk.Combobox(bar, textvariable=self.session, width=28)
        self.sessions.pack(side='left', padx=6)
        self.sessions.bind('<<ComboboxSelected>>', self.show_history)
        self.sessions.bind('<Return>', self.show_history)
        self.refresh_button = ttk.Button(bar, text='Atualizar', command=self.refresh_sessions)
        self.refresh_button.pack(side='left')
        self.delete_button = ttk.Button(bar, text='Excluir', command=self.delete_session, style='Danger.TButton')
        self.delete_button.pack(side='left', padx=(6, 0))
        self.index_button = ttk.Button(bar, text='Indexar arquivos', command=self.start_index)
        self.index_button.pack(side='right')

        self.transcript = scrolledtext.ScrolledText(window, wrap='word', state='disabled')
        self.transcript.pack(fill='both', expand=True, padx=10, pady=10)

        bottom = ttk.Frame(window, padding=10)
        bottom.pack(fill='x')
        entry = ttk.Entry(bottom, textvariable=self.question)
        entry.pack(side='left', fill='x', expand=True)
        entry.bind('<Return>', self.send)
        self.send_button = ttk.Button(bottom, text='Enviar', command=self.send)
        self.send_button.pack(side='left', padx=(8, 0))
        ttk.Label(window, textvariable=self.status, padding=(10, 0, 10, 10)).pack(anchor='w')

        self.refresh_sessions()
        self.window.after(100, self.poll_results)
        entry.focus_set()

    def db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return connect(DB_PATH)

    def append(self, content):
        self.transcript.configure(state='normal')
        self.transcript.insert('end', content)
        self.transcript.see('end')
        self.transcript.configure(state='disabled')

    def refresh_sessions(self):
        db = self.db()
        try:
            names = [row['session'] for row in db.execute(
                'SELECT session FROM turns GROUP BY session ORDER BY MAX(id) DESC')]
        finally:
            db.close()
        self.sessions['values'] = names
        if self.session.get().strip() in names:
            self.show_history()
        else:
            self.transcript.configure(state='normal')
            self.transcript.delete('1.0', 'end')
            self.transcript.configure(state='disabled')

    def show_history(self, _event=None):
        if self.busy:
            return
        name = self.session.get().strip()
        self.transcript.configure(state='normal')
        self.transcript.delete('1.0', 'end')
        self.transcript.configure(state='disabled')
        if not name:
            return
        db = self.db()
        try:
            rows = db.execute(
                'SELECT question, answer FROM turns WHERE session=? ORDER BY id', (name,)).fetchall()
            for row in rows:
                self.append(f"Você: {row['question']}\n\nAssistente: {row['answer']}\n\n")
        finally:
            db.close()

    def delete_session(self):
        name = self.session.get().strip()
        if not name:
            messagebox.showinfo('Sessão vazia', 'Selecione uma sessão para excluir.')
            return
        if not messagebox.askyesno('Excluir sessão', f'Deseja realmente excluir a sessão "{name}"?'):
            return

        db = self.db()
        try:
            db.execute('DELETE FROM turns WHERE session=?', (name,))
            db.commit()
        finally:
            db.close()

        self.session.set('')
        self.refresh_sessions()

    def set_busy(self, value, label='Pronto'):
        self.busy = value
        state = 'disabled' if value else 'normal'
        for widget in (self.sessions, self.refresh_button, self.delete_button, self.index_button, self.send_button):
            widget.configure(state=state)
        self.status.set(label)

    def send(self, _event=None):
        if self.busy:
            return
        name = self.session.get().strip()
        question = self.question.get().strip()
        if not name or not question:
            messagebox.showinfo('Faltam dados', 'Informe uma sessão e uma pergunta.')
            return
        self.question.set('')
        self.append(f'Você: {question}\n\n')
        self.set_busy(True, 'Gerando resposta...')
        threading.Thread(target=self.answer_worker, args=(name, question), daemon=True).start()

    def answer_worker(self, name, question):
        db = None
        try:
            settings = load_settings()
            db = self.db()
            result = answer(db, settings, Ollama(settings), question, session=name)
            self.results.put(('answer', result))
        except Exception as exc:
            self.results.put(('error', str(exc)))
        finally:
            if db is not None:
                db.close()

    def start_index(self):
        if self.busy:
            return
        self.set_busy(True, 'Indexando arquivos... Isso pode demorar.')
        threading.Thread(target=self.index_worker, daemon=True).start()

    def index_worker(self):
        try:
            process = subprocess.run(
                [sys.executable, str(ROOT / 'app.py'), 'index'],
                cwd=ROOT, capture_output=True, text=True, errors='replace',
            )
            log = (process.stdout + '\n' + process.stderr).strip()
            self.results.put(('index', process.returncode, log))
        except Exception as exc:
            self.results.put(('error', str(exc)))

    def poll_results(self):
        try:
            while True:
                result = self.results.get_nowait()
                self.set_busy(False)
                if result[0] == 'answer':
                    self.append(f'Assistente: {result[1]}\n\n')
                    self.refresh_sessions()
                elif result[0] == 'index':
                    code, log = result[1:]
                    self.status.set('Indexação concluída.' if code == 0 else 'Indexação com erros.')
                    self.append(f'Indexação:\n{log or "Sem mensagens."}\n\n')
                else:
                    self.status.set('Erro.')
                    self.append(f'Erro: {result[1]}\n\n')
        except queue.Empty:
            pass
        self.window.after(100, self.poll_results)


if __name__ == '__main__':
    root = tk.Tk()
    ChatWindow(root)
    root.mainloop()
