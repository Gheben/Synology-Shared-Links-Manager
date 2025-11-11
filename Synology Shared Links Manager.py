import paramiko
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Listbox, MULTIPLE
import os
from tkinter.font import Font
import webbrowser
import sys
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# Funzione per caricare la configurazione da Synology Shared Links Manager.json
def load_config():
    """Carica la configurazione dal file Synology Shared Links Manager.json nella stessa cartella dell'eseguibile."""
    try:
        # Determina il percorso della cartella dell'eseguibile o dello script
        if getattr(sys, 'frozen', False):
            # Se è un eseguibile .exe
            application_path = os.path.dirname(sys.executable)
        else:
            # Se è uno script Python
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        config_path = os.path.join(application_path, 'Synology Shared Links Manager.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Estrai i valori con valori di default se non presenti
        hostname = config.get('hostname', "server01.com")
        port = config.get('port', 22)
        username = config.get('username', "admin")
        password = config.get('password', "password")
        base_url = config.get('BASE_URL', "https://server02.it/sharing/")
        
        return hostname, port, username, password, base_url
        
    except FileNotFoundError:
        messagebox.showerror(
            "Errore Configurazione", 
            f"File Synology Shared Links Manager.json non trovato in: {application_path}\n\n"
            "Crea un file Synology Shared Links Manager.json con i parametri di connessione."
        )
        sys.exit(1)
    except json.JSONDecodeError as e:
        messagebox.showerror(
            "Errore Configurazione", 
            f"Errore nel parsing del file Synology Shared Links Manager.json: {e}"
        )
        sys.exit(1)
    except Exception as e:
        messagebox.showerror(
            "Errore Configurazione", 
            f"Errore nel caricamento della configurazione: {e}"
        )
        sys.exit(1)

# Carica la configurazione
hostname, port, username, password, BASE_URL = load_config()

# Comando base sqlite (rimane invariato)
sqlite_cmd = 'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT rowid, data FROM entry;"'
command_sqlite = f"sudo -S {sqlite_cmd}"

# Dizionari per la mappatura ID -> nome
group_map = {}
user_map = {}

# Variabile globale per tenere traccia della finestra di dettaglio corrente
current_detail_window = None
current_detail_record_id = None

class ModernSSLM:
    def __init__(self):
        self.root = tb.Window(themename="cosmo")
        self.root.title("SSLM - Synology Shared Links Manager")
        self.root.geometry("1600x880")
        
        # Imposta l'icona
        self.set_window_icon(self.root)
        
        # Variabili per i dati
        self.current_records = []
        
        # Carica configurazione
        self.hostname, self.port, self.username, self.password, self.BASE_URL = load_config()
        
        self.setup_ui()
        
    def set_window_icon(self, window):
        """Imposta l'icona per la finestra"""
        try:
            if getattr(sys, 'frozen', False):
                # Se è un eseguibile .exe
                application_path = os.path.dirname(sys.executable)
            else:
                # Se è uno script Python
                application_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(application_path, 'sslm.ico')
            if os.path.exists(icon_path):
                window.iconbitmap(icon_path)
        except Exception as e:
            print(f"Impossibile caricare l'icona: {e}")
    
    def setup_ui(self):
        """Configura l'interfaccia utente con layout moderno"""
        # Frame principale
        main_frame = tb.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Titolo principale
        title_label = tb.Label(
            main_frame, 
            text="Synology Shared Links Manager", 
            bootstyle="primary", 
            font=('Segoe UI', 18, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Container per i due pannelli principali
        content_frame = tb.Frame(main_frame)
        content_frame.pack(fill=BOTH, expand=True)
        
        # Pannello sinistro - Ricerca e Risultati
        left_panel = tb.Labelframe(
            content_frame, 
            text="RICERCA E RISULTATI", 
            bootstyle="primary",
            padding=15
        )
        left_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        # Frame ricerca
        search_frame = tb.Frame(left_panel)
        search_frame.pack(fill=X, pady=(0, 15))
        
        tb.Label(
            search_frame, 
            text="Nome file/cartella:", 
            bootstyle="dark"
        ).pack(side=LEFT, padx=(0, 10))
        
        self.entry_file = tb.Entry(
            search_frame, 
            width=30,
            bootstyle="primary"
        )
        self.entry_file.pack(side=LEFT, padx=(0, 10))
        self.entry_file.bind('<Return>', lambda e: self.search_files())
        
        tb.Button(
            search_frame, 
            text="Cerca", 
            command=self.search_files,
            bootstyle="primary",
            width=10
        ).pack(side=LEFT, padx=5)
        
        tb.Button(
            search_frame, 
            text="Svuota Mappature", 
            command=self.refresh_maps,
            bootstyle="warning-outline",
            width=15
        ).pack(side=LEFT, padx=5)
        
        # Frame azioni rapide
        actions_frame = tb.Frame(left_panel)
        actions_frame.pack(fill=X, pady=(0, 15))
        
        tb.Button(
            actions_frame, 
            text="Rimuovi Gruppi Specifici", 
            command=self.remove_selected_groups,
            bootstyle="warning-outline",
            width=18
        ).pack(side=LEFT, padx=2)
        
        tb.Button(
            actions_frame, 
            text="Rimuovi Utenti Specifici", 
            command=self.remove_selected_users,
            bootstyle="warning-outline",
            width=20
        ).pack(side=LEFT, padx=2)
        
        tb.Button(
            actions_frame, 
            text="Rimuovi Tutti i Gruppi", 
            command=self.remove_all_groups,
            bootstyle="danger-outline",
            width=20
        ).pack(side=LEFT, padx=2)
        
        tb.Button(
            actions_frame, 
            text="Rimuovi Tutti gli Utenti", 
            command=self.remove_all_users,
            bootstyle="danger-outline",
            width=18
        ).pack(side=LEFT, padx=2)
        
        # Tabella risultati
        table_frame = tb.Frame(left_panel)
        table_frame.pack(fill=BOTH, expand=True)
        
        columns = ("rowid", "name", "path", "protect_gids", "protect_uids")
        self.tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            height=20,
            selectmode="extended"
        )
        
        # Configurazione colonne
        for col, text, w in [
            ("rowid", "RowID", 50),
            ("name", "Nome", 200),
            ("path", "Percorso", 300),
            ("protect_gids", "Gruppi", 200),
            ("protect_uids", "Utenti", 150),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor="w")
        
        # Scrollbar
        scrollbar = tb.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind eventi - SINGOLO CLICK per mostrare dettagli
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        
        # Pannello destro - Dettagli e Azioni
        right_panel = tb.Labelframe(
            content_frame, 
            text="DETTAGLI E AZIONI", 
            bootstyle="primary",
            padding=15
        )
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))
        
        self.setup_details_panel(right_panel)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_details_panel(self, parent):
        """Configura il pannello dettagli e azioni"""
        # Frame per assegnazione rapida
        quick_assign_frame = tb.Labelframe(
            parent,
            text="ASSEGNAZIONE RAPIDA",
            bootstyle="info",
            padding=10
        )
        quick_assign_frame.pack(fill=X, pady=(0, 15))
        
        # Gruppo
        group_frame = tb.Frame(quick_assign_frame)
        group_frame.pack(fill=X, pady=5)
        
        tb.Label(group_frame, text="Gruppo:", bootstyle="dark", width=10).pack(side=LEFT)
        self.group_entry = tb.Entry(group_frame, bootstyle="primary")
        self.group_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.group_entry.bind('<Return>', lambda e: self.assign_group_from_entry())
        
        tb.Button(
            group_frame, 
            text="Assegna Gruppo", 
            command=self.assign_group_from_entry,
            bootstyle="primary",
            width=15
        ).pack(side=RIGHT, padx=5)
        
        # Utente
        user_frame = tb.Frame(quick_assign_frame)
        user_frame.pack(fill=X, pady=5)
        
        tb.Label(user_frame, text="Utente:", bootstyle="dark", width=10).pack(side=LEFT)
        self.user_entry = tb.Entry(user_frame, bootstyle="primary")
        self.user_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.user_entry.bind('<Return>', lambda e: self.assign_user_from_entry())
        
        tb.Button(
            user_frame, 
            text="Assegna Utente", 
            command=self.assign_user_from_entry,
            bootstyle="primary",
            width=15
        ).pack(side=RIGHT, padx=5)
        
        # Frame informazioni selezionate
        self.selected_info_frame = tb.Labelframe(
            parent, 
            text="INFORMAZIONI SELEZIONATE", 
            bootstyle="info",
            padding=10
        )
        self.selected_info_frame.pack(fill=BOTH, expand=True, pady=(0, 15))
        
        # Inizializza con messaggio di default
        self.setup_default_info()
        
        # Log area
        log_frame = tb.Labelframe(
            parent, 
            text="LOG AGGIORNAMENTI", 
            bootstyle="info",
            padding=10
        )
        log_frame.pack(fill=BOTH, expand=False, pady=(0, 0))
        
        # Text area per il log
        self.text_log = tb.ScrolledText(
            log_frame, 
            height=8,
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.text_log.pack(fill=BOTH, expand=True)
    
    def assign_group_from_entry(self):
        """Assegna il gruppo dal campo di testo"""
        group_name = self.group_entry.get().strip()
        if not group_name:
            messagebox.showwarning("Attenzione", "Inserisci un nome gruppo.")
            return
        
        # Cerca il gruppo
        found_groups = self.find_groups_by_name(group_name)
        
        if not found_groups:
            messagebox.showwarning("Attenzione", f"Nessun gruppo trovato con nome: {group_name}")
            return
        
        if len(found_groups) > 1:
            # Se ci sono più gruppi, chiedi all'utente di scegliere
            self.show_group_selection(found_groups, group_name)
        else:
            # Assegna direttamente il gruppo trovato
            gid, name = found_groups[0]
            self.update_with_group(gid, name)
            self.group_entry.delete(0, tk.END)
    
    def assign_user_from_entry(self):
        """Assegna l'utente dal campo di testo"""
        user_name = self.user_entry.get().strip()
        if not user_name:
            messagebox.showwarning("Attenzione", "Inserisci un nome utente.")
            return
        
        # Cerca l'utente
        found_users = self.find_users_by_name(user_name)
        
        if not found_users:
            messagebox.showwarning("Attenzione", f"Nessun utente trovato con nome: {user_name}")
            return
        
        if len(found_users) > 1:
            # Se ci sono più utenti, chiedi all'utente di scegliere
            self.show_user_selection(found_users, user_name)
        else:
            # Assegna direttamente l'utente trovato
            uid, name = found_users[0]
            self.update_with_user(uid, name)
            self.user_entry.delete(0, tk.END)
    
    def find_groups_by_name(self, group_name):
        """Cerca gruppi per nome"""
        found_groups = []
        
        # Prima cerca nella mappa esistente
        for gid, name in group_map.items():
            if group_name.lower() in name.lower():
                found_groups.append((gid, name))
        
        # Se non trovato, cerca sul server
        if not found_groups:
            try:
                cmd = f"sudo -S grep -r -i \"nss_name=.*{group_name}.*\" /usr/syno/etc/private/@accountcache/gid/ 2>/dev/null"
                result = self.run_ssh_command(cmd)
                group_files = result.splitlines()
                
                for line in group_files:
                    if ':' in line:
                        file_path, content = line.split(':', 1)
                        gid = os.path.basename(file_path)
                        
                        # Leggi il contenuto completo del file
                        cmd_content = f"sudo -S cat '{file_path}'"
                        file_content = self.run_ssh_command(cmd_content)
                        
                        display_name = "Sconosciuto"
                        for file_line in file_content.splitlines():
                            if file_line.startswith("nss_name="):
                                nss_value = file_line.split("=", 1)[1].strip()
                                if "\\" in nss_value:
                                    display_name = nss_value.split("\\", 1)[1]
                                else:
                                    display_name = nss_value
                                break
                        
                        found_groups.append((gid, display_name))
                        group_map[gid] = display_name
            except Exception as e:
                self.log_message(f"Errore nella ricerca gruppi: {e}")
        
        return found_groups
    
    def find_users_by_name(self, user_name):
        """Cerca utenti per nome"""
        found_users = []
        
        # Prima cerca nella mappa esistente
        for uid, name in user_map.items():
            if user_name.lower() in name.lower():
                found_users.append((uid, name))
        
        # Se non trovato, cerca sul server
        if not found_users:
            try:
                cmd = f"sudo -S grep -r -i \"nss_name=.*{user_name}.*\" /usr/syno/etc/private/@accountcache/uid/ 2>/dev/null"
                result = self.run_ssh_command(cmd)
                user_files = result.splitlines()
                
                for line in user_files:
                    if ':' in line:
                        file_path, content = line.split(':', 1)
                        uid = os.path.basename(file_path)
                        
                        # Leggi il contenuto completo del file
                        cmd_content = f"sudo -S cat '{file_path}'"
                        file_content = self.run_ssh_command(cmd_content)
                        
                        display_name = "Sconosciuto"
                        for file_line in file_content.splitlines():
                            if file_line.startswith("nss_name="):
                                nss_value = file_line.split("=", 1)[1].strip()
                                if "\\" in nss_value:
                                    display_name = nss_value.split("\\", 1)[1]
                                else:
                                    display_name = nss_value
                                break
                        
                        found_users.append((uid, display_name))
                        user_map[uid] = display_name
            except Exception as e:
                self.log_message(f"Errore nella ricerca utenti: {e}")
        
        return found_users
    
    def show_group_selection(self, groups, search_name):
        """Mostra selezione quando ci sono più gruppi"""
        popup = tb.Toplevel(self.root)
        popup.title("Seleziona Gruppo")
        popup.geometry("600x500")
        popup.resizable(True, True)
        popup.transient(self.root)
        popup.grab_set()
        
        # Imposta l'icona
        self.set_window_icon(popup)

        main_frame = tb.Frame(popup, padding=15)
        main_frame.pack(fill="both", expand=True)

        tb.Label(main_frame, text="Seleziona il gruppo:", bootstyle="dark").pack(anchor="w", pady=(0, 10))
        
        listbox_frame = tb.Frame(main_frame)
        listbox_frame.pack(fill=BOTH, expand=True, pady=10)
        
        listbox = Listbox(listbox_frame, font=('Segoe UI', 10))
        for gid, name in groups:
            listbox.insert(tk.END, f"{name} (ID: {gid})")
        listbox.pack(fill=BOTH, expand=True)

        def confirm_selection():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Attenzione", "Seleziona un gruppo dalla lista.")
                return
            selected_index = selection[0]
            gid, name = groups[selected_index]
            popup.destroy()
            self.update_with_group(gid, name)
            self.group_entry.delete(0, tk.END)

        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        tb.Button(btn_frame, text="Conferma", command=confirm_selection,
                  bootstyle="success", width=10).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Annulla", command=popup.destroy,
                  bootstyle="secondary", width=10).pack(side=LEFT, padx=5)
    
    def show_user_selection(self, users, search_name):
        """Mostra selezione quando ci sono più utenti"""
        popup = tb.Toplevel(self.root)
        popup.title("Seleziona Utente")
        popup.geometry("600x500")
        popup.resizable(True, True)
        popup.transient(self.root)
        popup.grab_set()
        
        # Imposta l'icona
        self.set_window_icon(popup)

        main_frame = tb.Frame(popup, padding=15)
        main_frame.pack(fill="both", expand=True)

        tb.Label(main_frame, text="Seleziona l'utente:", bootstyle="dark").pack(anchor="w", pady=(0, 10))
        
        listbox_frame = tb.Frame(main_frame)
        listbox_frame.pack(fill=BOTH, expand=True, pady=10)
        
        listbox = Listbox(listbox_frame, font=('Segoe UI', 10))
        for uid, name in users:
            listbox.insert(tk.END, f"{name} (ID: {uid})")
        listbox.pack(fill=BOTH, expand=True)

        def confirm_selection():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Attenzione", "Seleziona un utente dalla lista.")
                return
            selected_index = selection[0]
            uid, name = users[selected_index]
            popup.destroy()
            self.update_with_user(uid, name)
            self.user_entry.delete(0, tk.END)

        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        tb.Button(btn_frame, text="Conferma", command=confirm_selection,
                  bootstyle="success", width=10).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Annulla", command=popup.destroy,
                  bootstyle="secondary", width=10).pack(side=LEFT, padx=5)

    def setup_default_info(self):
        """Configura le informazioni di default quando nessun record è selezionato"""
        for widget in self.selected_info_frame.winfo_children():
            widget.destroy()
        
        tb.Label(
            self.selected_info_frame,
            text="Nessun record selezionato",
            bootstyle="secondary",
            font=('Segoe UI', 11)
        ).pack(expand=True, pady=20)
    
    def setup_selected_info(self, record):
        """Mostra le informazioni del record selezionato"""
        for widget in self.selected_info_frame.winfo_children():
            widget.destroy()
        
        # Frame per i dettagli
        details_frame = tb.Frame(self.selected_info_frame)
        details_frame.pack(fill=BOTH, expand=True)
        
        # RowID
        rowid_frame = tb.Frame(details_frame)
        rowid_frame.pack(fill=X, pady=2)
        tb.Label(rowid_frame, text="RowID:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT)
        tb.Label(rowid_frame, text=record["_rowid"], bootstyle="default").pack(side=LEFT)
        
        # Nome
        name_frame = tb.Frame(details_frame)
        name_frame.pack(fill=X, pady=2)
        tb.Label(name_frame, text="Nome:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT)
        tb.Label(name_frame, text=record.get("private_data", {}).get("name", "N/A"), bootstyle="default").pack(side=LEFT)
        
        # Percorso
        path_frame = tb.Frame(details_frame)
        path_frame.pack(fill=X, pady=2)
        tb.Label(path_frame, text="Percorso:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT)
        path_text = record.get("private_data", {}).get("path", "N/A")
        path_label = tb.Label(path_frame, text=path_text, bootstyle="default", wraplength=400, justify="left")
        path_label.pack(side=LEFT, fill=X, expand=True)
        
        # Recupera informazioni aggiuntive
        owner_uid = self.get_owner_uid_by_rowid(record["_rowid"])
        owner_name = "N/A"
        public_url = None
        full_public_url = "N/A"
        
        if owner_uid and owner_uid.isdigit():
            owner_name = self.find_user_name_by_uid(owner_uid)
            if not owner_name:
                owner_name = f"UID: {owner_uid} (Sconosciuto)"
        elif owner_uid:
            owner_name = f"Valore non valido: {owner_uid}"
        
        public_url = self.get_public_url_by_rowid(record["_rowid"])
        if public_url:
            full_public_url = f"{BASE_URL}{public_url}"
        
        # Owner
        owner_frame = tb.Frame(details_frame)
        owner_frame.pack(fill=X, pady=2)
        tb.Label(owner_frame, text="Owner:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT)
        tb.Label(owner_frame, text=owner_name, bootstyle="default").pack(side=LEFT)
        
        # URL pubblico
        url_frame = tb.Frame(details_frame)
        url_frame.pack(fill=X, pady=2)
        tb.Label(url_frame, text="Link:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT)
        
        if full_public_url != "N/A":
            url_label = tb.Label(
                url_frame, 
                text=full_public_url, 
                bootstyle="primary",
                cursor="hand2",
                wraplength=400,
                justify="left"
            )
            url_label.pack(side=LEFT, fill=X, expand=True)
            url_label.bind("<Button-1>", lambda e: self.handle_url_click(full_public_url))
        else:
            tb.Label(url_frame, text=full_public_url, bootstyle="default").pack(side=LEFT)
        
        # Gruppi abilitati
        groups_frame = tb.Frame(details_frame)
        groups_frame.pack(fill=X, pady=(10, 2))
        tb.Label(groups_frame, text="Gruppi:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT, anchor="n")
        
        groups_list_frame = tb.Frame(groups_frame)
        groups_list_frame.pack(side=LEFT, fill=X, expand=True)
        
        gid_list = record.get("protect_gids", [])
        for gid in gid_list:
            gid_str = str(gid)
            group_name = self.find_group_name_by_gid(gid_str)
            if group_name:
                tb.Label(groups_list_frame, text=f"• {group_name} (ID: {gid_str})", bootstyle="default").pack(anchor="w")
            else:
                tb.Label(groups_list_frame, text=f"• {gid_str} (Sconosciuto)", bootstyle="default").pack(anchor="w")
        
        if not gid_list:
            tb.Label(groups_list_frame, text="Nessun gruppo", bootstyle="secondary").pack(anchor="w")
        
        # Utenti abilitati
        users_frame = tb.Frame(details_frame)
        users_frame.pack(fill=X, pady=(10, 2))
        tb.Label(users_frame, text="Utenti:", bootstyle="dark", width=12, anchor="w").pack(side=LEFT, anchor="n")
        
        users_list_frame = tb.Frame(users_frame)
        users_list_frame.pack(side=LEFT, fill=X, expand=True)
        
        uid_list = record.get("protect_uids", [])
        for uid in uid_list:
            uid_str = str(uid)
            user_name = self.find_user_name_by_uid(uid_str)
            if user_name:
                tb.Label(users_list_frame, text=f"• {user_name} (ID: {uid_str})", bootstyle="default").pack(anchor="w")
            else:
                tb.Label(users_list_frame, text=f"• {uid_str} (Sconosciuto)", bootstyle="default").pack(anchor="w")
        
        if not uid_list:
            tb.Label(users_list_frame, text="Nessun utente", bootstyle="secondary").pack(anchor="w")
    
    def setup_status_bar(self, parent):
        """Configura la status bar"""
        status_frame = tb.Frame(parent)
        status_frame.pack(fill=X, pady=(10, 0))
        
        # Status variabile
        self.status_var = tk.StringVar(value="Pronto")
        status_label = tb.Label(
            status_frame, 
            textvariable=self.status_var,
            bootstyle="secondary"
        )
        status_label.pack(side=LEFT, fill=X, expand=True)
        
        # Powered by
        powered_by_label = tb.Label(
            status_frame,
            text="v1.1 powered by Guido Ballarini",
            bootstyle="secondary",
            font=('Segoe UI', 7)
        )
        powered_by_label.pack(side=RIGHT)
    
    def handle_url_click(self, url):
        """Gestisce il click su un URL"""
        if url != "N/A":
            # Copia negli appunti
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log_message(f"URL copiato negli appunti: {url}")
            
            # Apri nel browser
            try:
                webbrowser.open(url)
                self.log_message(f"Apertura nel browser: {url}")
            except Exception as e:
                self.log_message(f"Errore nell'apertura del browser: {e}")

    def run_ssh_command(self, command):
        """Esegue un comando SSH con sudo e restituisce stdout."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.hostname, self.port, self.username, self.password)

        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
        stdin.write(self.password + "\n")
        stdin.flush()

        # Leggi i dati in byte invece di decodificarli immediatamente
        result_bytes = stdout.read()
        error_bytes = stderr.read()

        ssh.close()
        
        # Prova a decodificare con UTF-8, ma usa 'replace' per caratteri non validi
        try:
            result = result_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            result = result_bytes.decode('utf-8', errors='replace').strip()
        
        try:
            error = error_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            error = error_bytes.decode('utf-8', errors='replace').strip()

        if error and not result:
            raise Exception(f"Errore SSH: {error}")
        return result

    def find_group_name_by_gid(self, gid):
        """Cerca il nome di un gruppo dato il GID nel percorso corretto."""
        # Prima controlla se è già nella mappa
        if gid in group_map:
            return group_map[gid]
        
        try:
            # Cerca direttamente il file del gruppo
            group_file = f"/usr/syno/etc/private/@accountcache/gid/{gid}"
            cmd = f"sudo -S cat '{group_file}'"
            file_content = self.run_ssh_command(cmd)
            
            # Estrai il nome del gruppo dal file
            for line in file_content.splitlines():
                if line.startswith("nss_name="):
                    nss_value = line.split("=", 1)[1].strip()
                    if "\\" in nss_value:
                        group_name = nss_value.split("\\", 1)[1]
                    else:
                        group_name = nss_value
                    # Aggiungi alla mappa per uso futuro
                    group_map[gid] = group_name
                    return group_name
        except Exception as e:
            self.log_message(f"Errore nella ricerca gruppo per GID {gid}: {e}")
        
        return None

    def find_user_name_by_uid(self, uid):
        """Cerca il nome di un utente dato l'UID nel percorso corretto."""
        # Prima controlla se è già nella mappa
        if uid in user_map:
            return user_map[uid]
        
        try:
            # Cerca direttamente il file dell'utente
            user_file = f"/usr/syno/etc/private/@accountcache/uid/{uid}"
            cmd = f"sudo -S cat '{user_file}'"
            file_content = self.run_ssh_command(cmd)
            
            # Estrai il nome dell'utente dal file
            for line in file_content.splitlines():
                if line.startswith("nss_name="):
                    nss_value = line.split("=", 1)[1].strip()
                    if "\\" in nss_value:
                        user_name = nss_value.split("\\", 1)[1]
                    else:
                        user_name = nss_value
                    # Aggiungi alla mappa per uso futuro
                    user_map[uid] = user_name
                    return user_name
        except Exception as e:
            self.log_message(f"Errore nella ricerca utente per UID {uid}: {e}")
        
        return None

    def get_owner_uid_by_rowid(self, rowid):
        """Recupera l'owner_uid dato il rowid della condivisione."""
        try:
            cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT owner_uid FROM entry WHERE rowid={rowid};"'
            result = self.run_ssh_command(f"sudo -S {cmd}")
            # La risposta dovrebbe essere solo un numero, puliamo eventuali newline e spazi
            if result and result.strip():
                # Prendi l'ultima linea non vuota (per evitare eventuali messaggi di password)
                lines = result.strip().splitlines()
                for line in reversed(lines):
                    if line.strip() and not line.strip().startswith("Password"):
                        return line.strip()
            return None
        except Exception as e:
            self.log_message(f"Errore nel recupero owner_uid per rowid {rowid}: {e}")
        return None

    def get_public_url_by_rowid(self, rowid):
        """Recupera l'URL pubblico dato il rowid della condivisione."""
        try:
            cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT * FROM entry WHERE rowid={rowid};"'
            result = self.run_ssh_command(f"sudo -S {cmd}")
            if result:
                # Prendi l'ultima linea non vuota
                lines = result.strip().splitlines()
                for line in reversed(lines):
                    if line.strip() and not line.strip().startswith("Password"):
                        # La struttura è: rowid|public_url|... resto dei campi
                        parts = line.split('|')
                        if len(parts) >= 2:
                            public_url = parts[1].strip()
                            return public_url if public_url else None
            return None
        except Exception as e:
            self.log_message(f"Errore nel recupero URL pubblico per rowid {rowid}: {e}")
        return None

    def get_sharing_entries(self):
        """Restituisce la lista di record dal DB sharing.db."""
        result = self.run_ssh_command(command_sqlite)
        records = []
        for line in result.splitlines():
            try:
                rowid, data = line.split("|", 1)
                rec = json.loads(data)
                rec["_rowid"] = int(rowid)
                records.append(rec)
            except Exception:
                pass
        return records

    def search_files(self):
        """Cerca file/cartella nei path del JSON."""
        file_name = self.entry_file.get().strip()
        if not file_name:
            messagebox.showwarning("Attenzione", "Inserisci un nome file/cartella.")
            return

        self.status_var.set("Ricerca in corso...")
        self.root.update()

        all_records = self.get_sharing_entries()
        filtered = [rec for rec in all_records if file_name.lower() in rec.get("private_data", {}).get("path", "").lower()]

        # Cancella risultati precedenti
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Popola la tabella
        for rec in filtered:
            name = rec.get("private_data", {}).get("name", "")
            path = rec.get("private_data", {}).get("path", "")
            
            # Converti GIDs in nomi
            gid_list = rec.get("protect_gids", [])
            gid_names = []
            for gid in gid_list:
                gid_str = str(gid)
                group_name = self.find_group_name_by_gid(gid_str)
                if group_name:
                    gid_names.append(f"{group_name}")
                else:
                    gid_names.append(f"{gid_str} (Sconosciuto)")
            gids = " || ".join(gid_names)
            
            # Converti UIDs in nomi
            uid_list = rec.get("protect_uids", [])
            uid_names = []
            for uid in uid_list:
                uid_str = str(uid)
                user_name = self.find_user_name_by_uid(uid_str)
                if user_name:
                    uid_names.append(f"{user_name}")
                else:
                    uid_names.append(f"{uid_str} (Sconosciuto)")
            uids = " || ".join(uid_names)
            
            self.tree.insert("", "end", values=(rec["_rowid"], name, path, gids, uids))

        self.current_records = filtered
        self.status_var.set(f"Trovati {len(filtered)} record")
        self.log_message(f"Trovati {len(filtered)} record che contengono '{file_name}'.")

        # Resetta il pannello informazioni
        self.setup_default_info()

    def show_details(self, event):
        """Mostra i dettagli del record selezionato nel pannello destro."""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # Prendi il primo elemento selezionato
        item_id = selected_items[0]
        index = self.tree.index(item_id)
        
        if index < len(self.current_records):
            record = self.current_records[index]
            self.setup_selected_info(record)

    def update_with_group(self, gr_gid, gr_name):
        """Aggiorna i record selezionati aggiungendo il gr_gid scelto."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un record dalla tabella principale.")
            return

        # Salva i rowid degli elementi selezionati prima dell'aggiornamento
        selected_rowids = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            selected_rowids.append(rec["_rowid"])

        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]

            gids = rec.get("protect_gids", [])
            if str(gr_gid) not in map(str, gids):
                # Aggiungi il nuovo gid alla lista esistente
                new_gids = gids + [int(gr_gid)]
                
                rowid = rec['_rowid']
                
                # Converti le liste in stringhe JSON
                old_gids_str = json.dumps(gids, separators=(',', ':'))
                new_gids_str = json.dumps(new_gids, separators=(',', ':'))
                
                # Costruisci il comando SQL per sostituire solo la parte dei gids
                update_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "UPDATE entry SET data = replace(data, \'\\"protect_gids\\":{old_gids_str}\', \'\\"protect_gids\\":{new_gids_str}\') WHERE rowid={rowid};"'
                cmd = f"sudo -S {update_cmd}"
                
                try:
                    self.log_message(f"[DEBUG] Eseguo: {cmd}")
                    result = self.run_ssh_command(cmd)
                    
                    # Verifica immediata
                    verify_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT data FROM entry WHERE rowid={rowid};"'
                    verify_result = self.run_ssh_command(f"sudo -S {verify_cmd}")
                    
                    if new_gids_str in verify_result:
                        self.log_message(f"[SUCCESSO] Aggiornato rowid={rowid}, aggiunto gruppo: {gr_name} (ID: {gr_gid})")
                    else:
                        self.log_message(f"[ATTENZIONE] Aggiornamento potrebbe non essere avvenuto per rowid={rowid}")
                        
                except Exception as e:
                    self.log_message(f"[ERRORE] rowid={rowid}: {e}")

            else:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} già contiene il gruppo: {gr_name} (ID: {gr_gid})")

        # Refresh tabella
        self.search_files()
        
        # Ripristina la selezione basata sui rowid
        self.restore_selection_by_rowids(selected_rowids)
        
        # Aggiorna il pannello informazioni
        self.refresh_selected_info()

    def update_with_user(self, pw_uid, nss_name):
        """Aggiorna i record selezionati aggiungendo l'pw_uid scelto."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un record dalla tabella principale.")
            return

        # Salva i rowid degli elementi selezionati prima dell'aggiornamento
        selected_rowids = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            selected_rowids.append(rec["_rowid"])

        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]

            uids = rec.get("protect_uids", [])
            if str(pw_uid) not in map(str, uids):
                # Aggiungi il nuovo uid alla lista esistente
                new_uids = uids + [int(pw_uid)]
                
                rowid = rec['_rowid']
                
                # Converti le liste in stringhe JSON
                old_uids_str = json.dumps(uids, separators=(',', ':'))
                new_uids_str = json.dumps(new_uids, separators=(',', ':'))
                
                # Costruisci il comando SQL per sostituire solo la parte degli uids
                update_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "UPDATE entry SET data = replace(data, \'\\"protect_uids\\":{old_uids_str}\', \'\\"protect_uids\\":{new_uids_str}\') WHERE rowid={rowid};"'
                cmd = f"sudo -S {update_cmd}"
                
                try:
                    self.log_message(f"[DEBUG] Eseguo: {cmd}")
                    result = self.run_ssh_command(cmd)
                    
                    # Verifica immediata
                    verify_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT data FROM entry WHERE rowid={rowid};"'
                    verify_result = self.run_ssh_command(f"sudo -S {verify_cmd}")
                    
                    if new_uids_str in verify_result:
                        self.log_message(f"[SUCCESSO] Aggiornato rowid={rowid}, aggiunto utente: {nss_name} (ID: {pw_uid})")
                    else:
                        self.log_message(f"[ATTENZIONE] Aggiornamento potrebbe non essere avvenuto per rowid={rowid}")
                        
                except Exception as e:
                    self.log_message(f"[ERRORE] rowid={rowid}: {e}")

            else:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} già contiene l'utente: {nss_name} (ID: {pw_uid})")

        # Refresh tabella
        self.search_files()
        
        # Ripristina la selezione basata sui rowid
        self.restore_selection_by_rowids(selected_rowids)
        
        # Aggiorna il pannello informazioni
        self.refresh_selected_info()

    def restore_selection_by_rowids(self, rowids):
        """Ripristina la selezione nella tabella basandosi sui rowid"""
        if not rowids:
            return
        
        # Cerca gli item nella tabella che corrispondono ai rowid
        for item in self.tree.get_children():
            item_rowid = self.tree.item(item)['values'][0]  # Il rowid è nella prima colonna
            if item_rowid in rowids:
                self.tree.selection_add(item)
        
        # Se c'è almeno un elemento selezionato, mostra i dettagli del primo
        selected_items = self.tree.selection()
        if selected_items:
            self.show_details(None)

    def refresh_selected_info(self):
        """Aggiorna il pannello informazioni selezionate"""
        selected_items = self.tree.selection()
        if selected_items:
            # Prendi il primo elemento selezionato
            item_id = selected_items[0]
            index = self.tree.index(item_id)
            
            if index < len(self.current_records):
                record = self.current_records[index]
                self.setup_selected_info(record)

    def remove_selected_groups(self):
        """Rimuove i gruppi selezionati dai record selezionati."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un record dalla tabella principale.")
            return

        # Ottieni tutti i gruppi presenti nei record selezionati
        all_groups = {}
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            gids = rec.get("protect_gids", [])
            
            for gid in gids:
                gid_str = str(gid)
                group_name = self.find_group_name_by_gid(gid_str)
                if not group_name:
                    group_name = f"{gid_str} (Sconosciuto)"
                
                if gid_str not in all_groups:
                    all_groups[gid_str] = group_name

        if not all_groups:
            messagebox.showinfo("Info", "Nessun gruppo presente nei record selezionati.")
            return

        # Mostra dialogo per selezionare i gruppi da rimuovere
        popup = tb.Toplevel(self.root)
        popup.title("Rimuovi Gruppi")
        popup.geometry("500x500")
        popup.resizable(True, True)
        
        # Imposta l'icona
        self.set_window_icon(popup)

        # Titolo
        title_frame = tb.Frame(popup, padding=15)
        title_frame.pack(fill=X)
        
        tb.Label(title_frame, text="Seleziona Gruppi da Rimuovere", font=('Segoe UI', 14, 'bold'), 
                 bootstyle="primary").pack()

        tb.Label(popup, text="Seleziona i gruppi da rimuovere:", bootstyle="dark").pack(pady=5)
        
        listbox_frame = tb.Frame(popup)
        listbox_frame.pack(fill=BOTH, expand=True, padx=15, pady=5)
        
        listbox = Listbox(listbox_frame, selectmode=MULTIPLE, font=('Segoe UI', 10))
        for gid, name in all_groups.items():
            listbox.insert(tk.END, f"{name} (ID: {gid})")
        listbox.pack(fill=BOTH, expand=True)

        selected_groups = []

        def confirm_removal():
            nonlocal selected_groups
            selections = listbox.curselection()
            selected_groups = [list(all_groups.keys())[i] for i in selections]
            popup.destroy()
            self.perform_group_removal(selected_groups)

        btn_frame = tb.Frame(popup, padding=15)
        btn_frame.pack(fill=X)
        
        tb.Button(btn_frame, text="Conferma", command=confirm_removal,
                  bootstyle="success", width=10).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Annulla", command=popup.destroy,
                  bootstyle="secondary", width=10).pack(side=LEFT, padx=5)

    def perform_group_removal(self, groups_to_remove):
        """Esegue la rimozione dei gruppi selezionati."""
        selected_items = self.tree.selection()
        
        # Salva i rowid degli elementi selezionati prima dell'aggiornamento
        selected_rowids = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            selected_rowids.append(rec["_rowid"])
        
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]

            gids = rec.get("protect_gids", [])
            if not gids:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} non ha gruppi da rimuovere")
                continue

            # Filtra i gruppi da rimuovere
            new_gids = [gid for gid in gids if str(gid) not in groups_to_remove]
            
            # Se la lista non è cambiata, salta
            if new_gids == gids:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} non contiene i gruppi specificati")
                continue

            rowid = rec['_rowid']
            
            # Converti le liste in stringhe JSON
            old_gids_str = json.dumps(gids, separators=(',', ':'))
            new_gids_str = json.dumps(new_gids, separators=(',', ':'))
            
            # Costruisci il comando SQL per sostituire solo la parte dei gids
            update_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "UPDATE entry SET data = replace(data, \'\\"protect_gids\\":{old_gids_str}\', \'\\"protect_gids\\":{new_gids_str}\') WHERE rowid={rowid};"'
            cmd = f"sudo -S {update_cmd}"
            
            try:
                self.log_message(f"[DEBUG] Eseguo: {cmd}")
                result = self.run_ssh_command(cmd)
                
                # Verifica immediata
                verify_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT data FROM entry WHERE rowid={rowid};"'
                verify_result = self.run_ssh_command(f"sudo -S {verify_cmd}")
                
                if new_gids_str in verify_result:
                    removed_groups = [group_map.get(str(gid), str(gid)) for gid in gids if str(gid) in groups_to_remove]
                    self.log_message(f"[SUCCESSO] Rimossi gruppi {removed_groups} da rowid={rowid}")
                else:
                    self.log_message(f"[ATTENZIONE] Rimozione gruppi potrebbe non essere avvenuta per rowid={rowid}")
                    
            except Exception as e:
                self.log_message(f"[ERRORE] rowid={rowid}: {e}")

        # Refresh tabella
        self.search_files()
        
        # Ripristina la selezione basata sui rowid
        self.restore_selection_by_rowids(selected_rowids)
        
        # Aggiorna il pannello informazioni
        self.refresh_selected_info()

    def remove_selected_users(self):
        """Rimuove gli utenti selezionati dai record selezionati."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un record dalla tabella principale.")
            return

        # Ottieni tutti gli utenti presenti nei record selezionati
        all_users = {}
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            uids = rec.get("protect_uids", [])
            
            for uid in uids:
                uid_str = str(uid)
                user_name = self.find_user_name_by_uid(uid_str)
                if not user_name:
                    user_name = f"{uid_str} (Sconosciuto)"
                
                if uid_str not in all_users:
                    all_users[uid_str] = user_name

        if not all_users:
            messagebox.showinfo("Info", "Nessun utente presente nei record selezionati.")
            return

        # Mostra dialogo per selezionare gli utenti da rimuovere
        popup = tb.Toplevel(self.root)
        popup.title("Rimuovi Utenti")
        popup.geometry("500x500")
        popup.resizable(True, True)
        
        # Imposta l'icona
        self.set_window_icon(popup)

        # Titolo
        title_frame = tb.Frame(popup, padding=15)
        title_frame.pack(fill=X)
        
        tb.Label(title_frame, text="Seleziona Utenti da Rimuovere", font=('Segoe UI', 14, 'bold'), 
                 bootstyle="primary").pack()

        tb.Label(popup, text="Seleziona gli utenti da rimuovere:", bootstyle="dark").pack(pady=5)
        
        listbox_frame = tb.Frame(popup)
        listbox_frame.pack(fill=BOTH, expand=True, padx=15, pady=5)
        
        listbox = Listbox(listbox_frame, selectmode=MULTIPLE, font=('Segoe UI', 10))
        for uid, name in all_users.items():
            listbox.insert(tk.END, f"{name} (ID: {uid})")
        listbox.pack(fill=BOTH, expand=True)

        selected_users = []

        def confirm_removal():
            nonlocal selected_users
            selections = listbox.curselection()
            selected_users = [list(all_users.keys())[i] for i in selections]
            popup.destroy()
            self.perform_user_removal(selected_users)

        btn_frame = tb.Frame(popup, padding=15)
        btn_frame.pack(fill=X)
        
        tb.Button(btn_frame, text="Conferma", command=confirm_removal,
                  bootstyle="success", width=10).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Annulla", command=popup.destroy,
                  bootstyle="secondary", width=10).pack(side=LEFT, padx=5)

    def perform_user_removal(self, users_to_remove):
        """Esegue la rimozione degli utenti selezionati."""
        selected_items = self.tree.selection()
        
        # Salva i rowid degli elementi selezionati prima dell'aggiornamento
        selected_rowids = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            selected_rowids.append(rec["_rowid"])
        
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]

            uids = rec.get("protect_uids", [])
            if not uids:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} non ha utenti da rimuovere")
                continue

            # Filtra gli utenti da rimuovere
            new_uids = [uid for uid in uids if str(uid) not in users_to_remove]
            
            # Se la lista non è cambiata, salta
            if new_uids == uids:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} non contiene gli utenti specificati")
                continue

            rowid = rec['_rowid']
            
            # Converti le liste in stringhe JSON
            old_uids_str = json.dumps(uids, separators=(',', ':'))
            new_uids_str = json.dumps(new_uids, separators=(',', ':'))
            
            # Costruisci il comando SQL per sostituire solo la parte degli uids
            update_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "UPDATE entry SET data = replace(data, \'\\"protect_uids\\":{old_uids_str}\', \'\\"protect_uids\\":{new_uids_str}\') WHERE rowid={rowid};"'
            cmd = f"sudo -S {update_cmd}"
            
            try:
                self.log_message(f"[DEBUG] Eseguo: {cmd}")
                result = self.run_ssh_command(cmd)
                
                # Verifica immediata
                verify_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT data FROM entry WHERE rowid={rowid};"'
                verify_result = self.run_ssh_command(f"sudo -S {verify_cmd}")
                
                if new_uids_str in verify_result:
                    removed_users = [user_map.get(str(uid), str(uid)) for uid in uids if str(uid) in users_to_remove]
                    self.log_message(f"[SUCCESSO] Rimossi utenti {removed_users} da rowid={rowid}")
                else:
                    self.log_message(f"[ATTENZIONE] Rimozione utenti potrebbe non essere avvenuta per rowid={rowid}")
                    
            except Exception as e:
                self.log_message(f"[ERRORE] rowid={rowid}: {e}")

        # Refresh tabella
        self.search_files()
        
        # Ripristina la selezione basata sui rowid
        self.restore_selection_by_rowids(selected_rowids)
        
        # Aggiorna il pannello informazioni
        self.refresh_selected_info()

    def remove_all_groups(self):
        """Rimuove tutti i gruppi dai record selezionati."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un record dalla tabella principale.")
            return

        # Controlla se c'è almeno un record che ha gruppi
        has_groups = False
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            gids = rec.get("protect_gids", [])
            if gids:
                has_groups = True
                break

        if not has_groups:
            messagebox.showinfo("Info", "Nessun gruppo presente nei record selezionati da rimuovere.")
            return

        # Salva i rowid degli elementi selezionati prima dell'aggiornamento
        selected_rowids = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            selected_rowids.append(rec["_rowid"])

        # Aggiunta finestra di conferma
        num_selected = len(selected_items)
        confirm = messagebox.askyesno(
            "Conferma Rimozione", 
            f"Sei sicuro di voler rimuovere TUTTI i gruppi dai {num_selected} record selezionati?\n\n"
            "Questa operazione non può essere annullata!",
            icon='warning'
        )
        
        if not confirm:
            self.log_message("Operazione di rimozione di tutti i gruppi annullata dall'utente")
            return

        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]

            gids = rec.get("protect_gids", [])
            if not gids:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} non ha gruppi da rimuovere")
                continue

            rowid = rec['_rowid']
            
            # Converti la lista corrente in stringa JSON
            old_gids_str = json.dumps(gids, separators=(',', ':'))
            
            # Nuova lista vuota
            new_gids_str = "[]"
            
            # Comando SQL per sostituire
            update_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "UPDATE entry SET data = replace(data, \'\\"protect_gids\\":{old_gids_str}\', \'\\"protect_gids\\":{new_gids_str}\') WHERE rowid={rowid};"'
            cmd = f"sudo -S {update_cmd}"
            
            try:
                self.log_message(f"[DEBUG] Eseguo: {cmd}")
                result = self.run_ssh_command(cmd)
                
                # Verifica
                verify_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT data FROM entry WHERE rowid={rowid};"'
                verify_result = self.run_ssh_command(f"sudo -S {verify_cmd}")
                
                if new_gids_str in verify_result:
                    self.log_message(f"[SUCCESSO] Rimossi tutti i gruppi da rowid={rowid}")
                else:
                    self.log_message(f"[ATTENZIONE] Rimozione gruppi potrebbe non essere avvenuta per rowid={rowid}")
                    
            except Exception as e:
                self.log_message(f"[ERRORE] rowid={rowid}: {e}")

        # Refresh tabella
        self.search_files()
        
        # Ripristina la selezione basata sui rowid
        self.restore_selection_by_rowids(selected_rowids)
        
        # Aggiorna il pannello informazioni
        self.refresh_selected_info()

    def remove_all_users(self):
        """Rimuove tutti gli utenti dai record selezionati."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un record dalla tabella principale.")
            return

        # Controlla se c'è almeno un record che ha utenti
        has_users = False
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            uids = rec.get("protect_uids", [])
            if uids:
                has_users = True
                break

        if not has_users:
            messagebox.showinfo("Info", "Nessun utente presente nei record selezionati da rimuovere.")
            return

        # Salva i rowid degli elementi selezionati prima dell'aggiornamento
        selected_rowids = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]
            selected_rowids.append(rec["_rowid"])

        # Aggiunta finestra di conferma
        num_selected = len(selected_items)
        confirm = messagebox.askyesno(
            "Conferma Rimozione", 
            f"Sei sicuro di voler rimuovere TUTTI gli utenti dai {num_selected} record selezionati?\n\n"
            "Questa operazione non può essere annullata!",
            icon='warning'
        )
        
        if not confirm:
            self.log_message("Operazione di rimozione di tutti gli utenti annullata dall'utente")
            return

        for item_id in selected_items:
            index = self.tree.index(item_id)
            rec = self.current_records[index]

            uids = rec.get("protect_uids", [])
            if not uids:
                self.log_message(f"[SKIP] rowid={rec['_rowid']} non ha utenti da rimuovere")
                continue

            rowid = rec['_rowid']
            
            # Converti la lista corrente in stringa JSON
            old_uids_str = json.dumps(uids, separators=(',', ':'))
            
            # Nuova lista vuota
            new_uids_str = "[]"
            
            # Comando SQL per sostituire
            update_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "UPDATE entry SET data = replace(data, \'\\"protect_uids\\":{old_uids_str}\', \'\\"protect_uids\\":{new_uids_str}\') WHERE rowid={rowid};"'
            cmd = f"sudo -S {update_cmd}"
            
            try:
                self.log_message(f"[DEBUG] Eseguo: {cmd}")
                result = self.run_ssh_command(cmd)
                
                # Verifica
                verify_cmd = f'sqlite3 /usr/syno/etc/private/session/sharing/sharing.db "SELECT data FROM entry WHERE rowid={rowid};"'
                verify_result = self.run_ssh_command(f"sudo -S {verify_cmd}")
                
                if new_uids_str in verify_result:
                    self.log_message(f"[SUCCESSO] Rimossi tutti gli utenti da rowid={rowid}")
                else:
                    self.log_message(f"[ATTENZIONE] Rimozione utenti potrebbe non essere avvenuta per rowid={rowid}")
                    
            except Exception as e:
                self.log_message(f"[ERRORE] rowid={rowid}: {e}")

        # Refresh tabella
        self.search_files()
        
        # Ripristina la selezione basata sui rowid
        self.restore_selection_by_rowids(selected_rowids)
        
        # Aggiorna il pannello informazioni
        self.refresh_selected_info()

    def log_message(self, msg):
        """Aggiunge una riga al log box."""
        self.text_log.insert(tk.END, msg + "\n")
        self.text_log.see(tk.END)

    def refresh_maps(self):
        """Svuota le mappature per forzare un ricaricamento."""
        global group_map, user_map
        group_map.clear()
        user_map.clear()
        self.log_message("Mappature svuotate. Verranno ricaricate alla prossima ricerca.")
        self.status_var.set("Mappature svuotate")

def main():
    app = ModernSSLM()
    app.root.mainloop()

if __name__ == "__main__":
    main()
