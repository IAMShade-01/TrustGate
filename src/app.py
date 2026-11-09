import getpass
import os
import tkinter as tk

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
            self.sidebar, text="DEMO PREVIEW", bg=SIDEBAR, fg="#9EABC0",
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
            text="TrustGate prototype • Organization SSO and API authorization are not configured.",
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
        self.info_page(
            "Settings",
            "TrustGate is running in local preview mode. No settings are saved."
        )

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