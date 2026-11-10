import getpass
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from credential_store import CredentialStore, CredentialStoreError

BG = "#F3F5F9"
SIDEBAR = "#17263C"
TEXT = "#202B3C"
MUTED = "#718096"
BLUE = "#356AE6"
WHITE = "#FFFFFF"


class TrustGateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TrustGate")
        self.root.geometry("900x580")
        self.root.minsize(760, 500)
        self.root.configure(bg=BG)
        self.status_text = "Disabled"
        self.store = None
        self.store_error = None
        try:
            self.store = CredentialStore()
        except CredentialStoreError as error:
            self.store_error = str(error)

        self.sidebar = tk.Frame(root, bg=SIDEBAR, width=205)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar, text="TRUSTGATE", bg=SIDEBAR, fg=WHITE,
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", padx=22, pady=(28, 4))
        tk.Label(
            self.sidebar, text="SECURE ACCESS", bg=SIDEBAR, fg="#9EABC0",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=23, pady=(0, 34))

        self.content = tk.Frame(root, bg=BG, padx=32, pady=28)
        self.content.pack(side="left", fill="both", expand=True)

        self.nav_buttons = {}
        for page in ("Overview", "Access", "Activity", "Settings"):
            button = tk.Button(
                self.sidebar, text=page, anchor="w", padx=22, pady=12,
                bg=SIDEBAR, fg="#D7DFEB", activebackground="#263A56",
                activeforeground=WHITE, relief="flat", bd=0,
                font=("Segoe UI", 11), cursor="hand2",
                command=lambda name=page: self.show_page(name)
            )
            button.pack(fill="x")
            self.nav_buttons[page] = button

        tk.Label(
            self.sidebar, text="LOCAL MODE", bg=SIDEBAR, fg="#9EABC0",
            font=("Segoe UI", 9, "bold")
        ).pack(side="bottom", anchor="w", padx=22, pady=22)

        self.show_page("Overview")

    def show_page(self, page):
        for widget in self.content.winfo_children():
            widget.destroy()

        for name, button in self.nav_buttons.items():
            button.configure(bg="#263A56" if name == page else SIDEBAR)

        tk.Label(
            self.content, text=page, bg=BG, fg=TEXT,
            font=("Segoe UI", 24, "bold")
        ).pack(anchor="w")

        if page == "Overview":
            self.overview()
        elif page == "Access":
            self.access_page()
        elif page == "Activity":
            self.activity_page()
        else:
            self.settings_page()

    def card(self, parent, title, value, column):
        box = tk.Frame(parent, bg=WHITE, padx=18, pady=17)
        box.grid(row=0, column=column, sticky="nsew", padx=(0, 12))
        tk.Label(
            box, text=title, bg=WHITE, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        tk.Label(
            box, text=value, bg=WHITE, fg=TEXT,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(9, 0))

    def overview(self):
        username = getpass.getuser()
        domain = os.environ.get("USERDOMAIN", "Local device")

        tk.Label(
            self.content, text="Your access and sign-in overview",
            bg=BG, fg=MUTED, font=("Segoe UI", 11)
        ).pack(anchor="w", pady=(4, 22))

        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")
        for column in range(3):
            cards.columnconfigure(column, weight=1)

        self.card(cards, "Windows account", username, 0)
        self.card(cards, "Domain", domain, 1)
        self.status_card = tk.Frame(cards, bg=WHITE, padx=18, pady=17)
        self.status_card.grid(row=0, column=2, sticky="nsew")

        tk.Label(
            self.status_card, text="Launch preference", bg=WHITE, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        self.status_label = tk.Label(
            self.status_card, text=self.status_text, bg=WHITE, fg=TEXT,
            font=("Segoe UI", 14, "bold")
        )
        self.status_label.pack(anchor="w", pady=(9, 0))

        panel = tk.Frame(self.content, bg=WHITE, padx=22, pady=20)
        panel.pack(fill="x", pady=22)

        tk.Label(
            panel, text="Quick actions", bg=WHITE, fg=TEXT,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            panel,
            text="Preview controls only. They do not configure Windows sign-in.",
            bg=WHITE, fg=MUTED, font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(0, 17))

        actions = tk.Frame(panel, bg=WHITE)
        actions.pack(anchor="w")

        tk.Button(
            actions, text="Enable (Preview)", command=self.enable_preview,
            bg=BLUE, fg=WHITE, activebackground="#2859C8",
            activeforeground=WHITE, relief="flat", padx=16, pady=9,
            font=("Segoe UI", 10, "bold"), cursor="hand2"
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            actions, text="Disable", command=self.disable_preview,
            bg="#E8ECF3", fg=TEXT, activebackground="#D9DFE9",
            relief="flat", padx=16, pady=9, font=("Segoe UI", 10),
            cursor="hand2"
        ).pack(side="left")

        tk.Label(
            self.content,
            text="Credentials stay on this device. Platform-specific connections are not configured.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", side="bottom")

    def enable_preview(self):
        self.status_text = "Enabled (preview)"
        self.status_label.config(text=self.status_text)

    def disable_preview(self):
        self.status_text = "Disabled"
        self.status_label.config(text=self.status_text)

    def access_page(self):
        self.info_page(
            "Access management",
            "Organization sign-in and permission management are not connected in this preview."
        )

    def activity_page(self):
        self.info_page(
            "Recent activity",
            "No activity recorded. Audit logging has not been configured."
        )

    def settings_page(self):
        if self.store is None:
            self.info_page("Settings", self.store_error or "Secure credential storage is unavailable.")
            return

        tabs = ttk.Notebook(self.content)
        tabs.pack(fill="both", expand=True, pady=(16, 0))

        identity_tab = ttk.Frame(tabs, padding=18)
        connections_tab = ttk.Frame(tabs, padding=14)
        tabs.add(identity_tab, text="Device identity")
        tabs.add(connections_tab, text="Connections")
        self.identity_page(identity_tab)
        self.connections_page(connections_tab)

    def identity_page(self, parent):
        try:
            identity = self.store.get_identity()
        except CredentialStoreError as error:
            ttk.Label(parent, text=str(error), wraplength=560).pack(anchor="w")
            return

        ttk.Label(parent, text="TrustGate device ID").pack(anchor="w")
        ttk.Label(parent, text=identity["device_id"]).pack(anchor="w", pady=(2, 14))
        ttk.Label(parent, text="Public identity key").pack(anchor="w")

        key_row = ttk.Frame(parent)
        key_row.pack(fill="x", pady=(4, 14))
        public_key = ttk.Entry(key_row)
        public_key.insert(0, identity["public_key"])
        public_key.configure(state="readonly")
        public_key.pack(side="left", fill="x", expand=True)
        ttk.Button(
            key_row,
            text="Copy",
            command=lambda: self.copy_to_clipboard(identity["public_key"]),
        ).pack(side="left", padx=(8, 0))

        ttk.Label(parent, text=identity["fingerprint"]).pack(anchor="w", pady=(0, 14))
        ttk.Label(
            parent,
            text=(
                "The matching private key stays in the Windows credential vault. "
                "Register this public key with a platform that supports SSH/Ed25519 identity."
            ),
            wraplength=560,
        ).pack(anchor="w")

    def connections_page(self, parent):
        ttk.Label(
            parent,
            text="Save credentials locally. Platform-specific connection adapters are not configured.",
            wraplength=590,
        ).pack(anchor="w", pady=(0, 10))

        form = ttk.Frame(parent)
        form.pack(fill="x")
        self.profile_name = tk.StringVar()
        self.profile_platform = tk.StringVar()
        self.profile_endpoint = tk.StringVar()
        self.profile_username = tk.StringVar()
        self.profile_kind = tk.StringVar(value="API")
        self.ssh_key_path = tk.StringVar()

        self.add_form_field(form, "Profile name", self.profile_name, 0)
        self.add_form_field(form, "Platform", self.profile_platform, 1)
        self.add_form_field(form, "API URL / SSH host", self.profile_endpoint, 2)
        self.add_form_field(form, "SSH username", self.profile_username, 3)

        ttk.Label(form, text="Credential type").grid(row=4, column=0, sticky="w", pady=3)
        kind_picker = ttk.Combobox(
            form, textvariable=self.profile_kind, values=("API", "SSH"), state="readonly", width=18
        )
        kind_picker.grid(row=4, column=1, sticky="w", pady=3)
        kind_picker.bind("<<ComboboxSelected>>", self.toggle_credential_fields)

        self.api_fields = ttk.Frame(form)
        self.api_fields.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.api_key = tk.StringVar()
        self.api_secret = tk.StringVar()
        self.add_form_field(self.api_fields, "API key", self.api_key, 0, secret=True)
        self.add_form_field(self.api_fields, "API secret", self.api_secret, 1, secret=True)

        self.ssh_fields = ttk.Frame(form)
        self.ssh_fields.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Label(self.ssh_fields, text="Private key file").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(self.ssh_fields, textvariable=self.ssh_key_path, width=46).grid(
            row=0, column=1, sticky="ew", pady=3
        )
        ttk.Button(self.ssh_fields, text="Browse", command=self.choose_ssh_key).grid(
            row=0, column=2, padx=(6, 0), pady=3
        )
        self.ssh_passphrase = tk.StringVar()
        self.add_form_field(self.ssh_fields, "Key passphrase", self.ssh_passphrase, 1, secret=True)
        self.toggle_credential_fields()

        ttk.Button(form, text="Save profile", command=self.save_connection).grid(
            row=6, column=1, sticky="e", pady=(8, 12)
        )

        ttk.Separator(parent).pack(fill="x", pady=(0, 8))
        self.profile_tree = ttk.Treeview(
            parent,
            columns=("name", "kind", "platform", "endpoint"),
            show="headings",
            height=5,
        )
        for column, title, width in (
            ("name", "Name", 110),
            ("kind", "Type", 60),
            ("platform", "Platform", 130),
            ("endpoint", "API URL / Host", 260),
        ):
            self.profile_tree.heading(column, text=title)
            self.profile_tree.column(column, width=width, stretch=column == "endpoint")
        self.profile_tree.pack(fill="both", expand=True)
        ttk.Button(parent, text="Remove selected", command=self.remove_connection).pack(
            anchor="e", pady=(8, 0)
        )
        self.refresh_profiles()

    def add_form_field(self, parent, label, variable, row, secret=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        field = ttk.Entry(parent, textvariable=variable, width=46, show="*" if secret else "")
        field.grid(row=row, column=1, sticky="ew", pady=3)
        parent.columnconfigure(1, weight=1)
        return field

    def toggle_credential_fields(self, _event=None):
        if self.profile_kind.get() == "SSH":
            self.api_fields.grid_remove()
            self.ssh_fields.grid()
        else:
            self.ssh_fields.grid_remove()
            self.api_fields.grid()

    def choose_ssh_key(self):
        path = filedialog.askopenfilename(
            title="Select an SSH private key",
            filetypes=(("Private key files", "*.pem *.key *.openssh"), ("All files", "*.*")),
        )
        if path:
            self.ssh_key_path.set(path)

    def save_connection(self):
        credentials = {}
        kind = self.profile_kind.get()
        try:
            if kind == "API":
                credentials = {
                    "api_key": self.api_key.get(),
                    "api_secret": self.api_secret.get(),
                }
            else:
                key_path = self.ssh_key_path.get().strip()
                if key_path:
                    with open(key_path, "r", encoding="utf-8") as key_file:
                        private_key = key_file.read()
                    if "PRIVATE KEY" not in private_key:
                        raise CredentialStoreError("Select an OpenSSH or PEM private key file.")
                else:
                    private_key = ""
                credentials = {
                    "ssh_private_key": private_key,
                    "ssh_passphrase": self.ssh_passphrase.get(),
                }

            self.store.save_profile(
                name=self.profile_name.get(),
                platform=self.profile_platform.get(),
                kind=kind,
                endpoint=self.profile_endpoint.get(),
                username=self.profile_username.get(),
                credentials=credentials,
            )
            self.api_key.set("")
            self.api_secret.set("")
            self.ssh_passphrase.set("")
            self.ssh_key_path.set("")
            self.refresh_profiles()
            messagebox.showinfo("TrustGate", "Profile saved to this Windows account.", parent=self.root)
        except (OSError, UnicodeError, CredentialStoreError) as error:
            messagebox.showerror("Could not save profile", str(error), parent=self.root)

    def refresh_profiles(self):
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        try:
            profiles = self.store.get_profiles()
        except CredentialStoreError as error:
            messagebox.showerror("Could not load profiles", str(error), parent=self.root)
            return
        for profile in profiles:
            self.profile_tree.insert(
                "", "end", iid=profile["id"],
                values=(profile["name"], profile["kind"], profile["platform"], profile["endpoint"]),
                text=profile["name"],
            )

    def remove_connection(self):
        selection = self.profile_tree.selection()
        if not selection:
            return
        try:
            self.store.delete_profile(selection[0])
            self.refresh_profiles()
        except CredentialStoreError as error:
            messagebox.showerror("Could not remove profile", str(error), parent=self.root)

    def copy_to_clipboard(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)

    def info_page(self, heading, description):
        panel = tk.Frame(self.content, bg=WHITE, padx=22, pady=22)
        panel.pack(fill="x", pady=22)
        tk.Label(
            panel, text=heading, bg=WHITE, fg=TEXT,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")
        tk.Label(
            panel, text=description, bg=WHITE, fg=MUTED,
            wraplength=580, justify="left", font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(10, 0))


if __name__ == "__main__":
    window = tk.Tk()
    TrustGateApp(window)
    window.mainloop()