import getpass
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from activity_log import append_activity, read_activity
from company_profiles import CompanyProfileError, load_company_profiles
from credential_store import CredentialStore, CredentialStoreError
from dashboard_modules import MODULES, DashboardConfigError, DashboardStore
from printer_requests import PrinterRequestError, PrinterRequestStore, export_request_pdf
from software_integrations import (
    INTEGRATIONS, IntegrationError, check_status, executable_path, install_package,
    validate_package_id,
)

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
        self.root.geometry("1100x720")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG)
        self.status_text = "Disabled"
        self.dashboard_store = DashboardStore()
        self.dashboard_error = None
        self.dashboard_widgets = []
        self.dashboard_editing = False
        try:
            self.dashboard_widgets = self.dashboard_store.load()
        except DashboardConfigError as error:
            self.dashboard_error = str(error)
        self.deployment_busy = False
        self.deployment_result = "Select an integration and check its status."
        self.deployment_queue = queue.Queue()
        self.company_profiles = {}
        self.company_profile_error = None
        try:
            self.company_profiles = load_company_profiles()
        except CompanyProfileError as error:
            self.company_profile_error = str(error)
        self.store = None
        self.printer_request_store = PrinterRequestStore()
        self.store_error = None
        try:
            self.store = CredentialStore()
        except CredentialStoreError as error:
            self.store_error = str(error)

        self.sidebar = tk.Frame(root, bg=SIDEBAR, width=205)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        header = tk.Frame(self.sidebar, bg=SIDEBAR)
        header.pack(fill="x")
        tk.Label(
            header, text="TRUSTGATE", bg=SIDEBAR, fg=WHITE,
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", padx=22, pady=(28, 4))
        tk.Label(
            header, text="SECURE ACCESS", bg=SIDEBAR, fg="#9EABC0",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=23, pady=(0, 34))

        navigation = tk.Frame(self.sidebar, bg=SIDEBAR)
        navigation.pack(fill="both", expand=True)
        self.nav_canvas = tk.Canvas(
            navigation, bg=SIDEBAR, borderwidth=0, highlightthickness=0,
        )
        self.nav_scrollbar = ttk.Scrollbar(
            navigation, orient="vertical", command=self.nav_canvas.yview,
        )
        self.nav_canvas.configure(yscrollcommand=self.nav_scrollbar.set)
        self.nav_scrollbar.pack(side="right", fill="y")
        self.nav_canvas.pack(side="left", fill="both", expand=True)
        self.nav_frame = tk.Frame(self.nav_canvas, bg=SIDEBAR)
        self.nav_window = self.nav_canvas.create_window(
            (0, 0), window=self.nav_frame, anchor="nw",
        )
        self.nav_frame.bind("<Configure>", self._update_navigation_scrollregion)
        self.nav_canvas.bind("<Configure>", self._resize_navigation_content)
        self.nav_canvas.bind("<MouseWheel>", self._scroll_navigation)

        self.content = tk.Frame(root, bg=BG, padx=32, pady=28)
        self.content.pack(side="left", fill="both", expand=True)

        self.nav_buttons = {}
        pages = (
            "Dashboard", "Deployment Wizard", "Company Profiles", "Computer Setup",
            "Account Setup", "AutoLogon Manager", "Password Reset", "Software Deployment",
            "Asset Management", "Network Configuration", "Printer Requests", "Validation",
            "Reports", "Plugin Marketplace", "Settings",
        )
        for page in pages:
            button = tk.Button(
                self.nav_frame, text=page, anchor="w", padx=22, pady=12,
                bg=SIDEBAR, fg="#D7DFEB", activebackground="#263A56",
                activeforeground=WHITE, relief="flat", bd=0,
                font=("Segoe UI", 11), cursor="hand2",
                command=lambda name=page: self.show_page(name)
            )
            button.pack(fill="x")
            button.bind("<MouseWheel>", self._scroll_navigation)
            self.nav_buttons[page] = button

        tk.Label(
            self.sidebar, text="LOCAL MODE", bg=SIDEBAR, fg="#9EABC0",
            font=("Segoe UI", 9, "bold")
        ).pack(side="bottom", anchor="w", padx=22, pady=22)

        self.show_page("Dashboard")

    def _update_navigation_scrollregion(self, _event=None):
        self.nav_canvas.configure(scrollregion=self.nav_canvas.bbox("all"))

    def _resize_navigation_content(self, event):
        self.nav_canvas.itemconfigure(self.nav_window, width=event.width)

    def _scroll_navigation(self, event):
        if event.delta:
            self.nav_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def show_page(self, page):
        if page != "AutoLogon Manager" and hasattr(self, "autologon_password"):
            self.autologon_password.set("")
            if not self.remember_autologon_settings.get():
                self.autologon_company.set(next(iter(self.company_profiles), "Custom"))
                self.autologon_username.set("")
                self.autologon_domain.set("")

        for widget in self.content.winfo_children():
            widget.destroy()

        for name, button in self.nav_buttons.items():
            button.configure(bg="#263A56" if name == page else SIDEBAR)

        tk.Label(
            self.content, text=page, bg=BG, fg=TEXT,
            font=("Segoe UI", 24, "bold")
        ).pack(anchor="w")

        if page == "Dashboard":
            self.overview()
        elif page == "Company Profiles":
            self.company_profiles_page()
        elif page == "Computer Setup":
            self.computer_setup_page()
        elif page == "AutoLogon Manager":
            self.auto_logon_page()
        elif page == "Deployment Wizard":
            self.deployment_wizard_page()
        elif page == "Password Reset":
            self.password_reset_page()
        elif page == "Printer Requests":
            self.printer_requests_page()
        elif page in ("Reports", "Logs & Reports"):
            self.activity_page()
        elif page == "Settings":
            self.settings_page()
        elif page == "Plugin Marketplace":
            self.plugin_marketplace_page()
        elif page == "Software Deployment":
            self.software_deployment_page()
        elif page == "Account Setup":
            self.info_page("Account setup", "Use AutoLogon Manager or Password Reset. Directory changes are not executed in this preview.")
        elif page == "Asset Management":
            self.info_page("Asset management", "Asset inventory fields and assignment workflows are not connected yet.")
        elif page == "Network Configuration":
            self.info_page("Network configuration", "DNS, time sync, printer, and drive configuration adapters are not connected.")
        elif page == "Validation":
            self.info_page("Validation", "SCCM, GPO, DNS, and time-sync checks are not connected in this preview.")
        else:
            self.info_page("Health checks", "Device health checks are not connected in this preview.")

    def software_deployment_page(self):
        tk.Label(
            self.content, text="Connect to local tools and install Windows packages with winget.",
            bg=BG, fg=MUTED, font=("Segoe UI", 11), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(4, 16))
        panel = tk.Frame(self.content, bg=WHITE, padx=20, pady=18)
        panel.pack(fill="both", expand=True)
        if not hasattr(self, "deployment_integration"):
            self.deployment_integration = tk.StringVar(value=INTEGRATIONS[0])
            self.deployment_package_id = tk.StringVar()

        tk.Label(panel, text="Application", bg=WHITE, fg=TEXT).pack(anchor="w")
        picker = ttk.Combobox(
            panel, textvariable=self.deployment_integration, values=INTEGRATIONS,
            state="readonly", width=36,
        )
        picker.pack(anchor="w", pady=(4, 10))
        picker.bind("<<ComboboxSelected>>", self._update_deployment_controls)
        self.deployment_check_button = ttk.Button(
            panel, text="Check connection / status", command=self.check_deployment_status,
        )
        self.deployment_check_button.pack(anchor="w", pady=(0, 12))

        tk.Label(panel, text="Exact winget package ID", bg=WHITE, fg=TEXT).pack(anchor="w")
        package_row = tk.Frame(panel, bg=WHITE)
        package_row.pack(fill="x", pady=(4, 4))
        self.deployment_package_entry = ttk.Entry(
            package_row, textvariable=self.deployment_package_id, width=38,
        )
        self.deployment_package_entry.pack(side="left", fill="x", expand=True)
        self.deployment_install_button = ttk.Button(
            package_row, text="Install package", command=self.confirm_package_install,
        )
        self.deployment_install_button.pack(side="left", padx=(8, 0))
        tk.Label(
            panel,
            text="Example: Microsoft.PowerToys. Installation uses the configured winget source "
                 "and may require administrator approval. Docker and WSL checks are read-only.",
            bg=WHITE, fg=MUTED, wraplength=700, justify="left",
        ).pack(anchor="w", pady=(0, 12))

        tk.Label(panel, text="Result", bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        result_frame = tk.Frame(panel, bg=WHITE)
        result_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.deployment_output = tk.Text(result_frame, wrap="word", height=7, state="disabled")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.deployment_output.yview)
        self.deployment_output.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.deployment_output.pack(side="left", fill="both", expand=True)
        self._show_deployment_result()
        self._update_deployment_controls()

    def _show_deployment_result(self):
        if hasattr(self, "deployment_output") and self.deployment_output.winfo_exists():
            self.deployment_output.configure(state="normal")
            self.deployment_output.delete("1.0", "end")
            self.deployment_output.insert("1.0", self.deployment_result)
            self.deployment_output.configure(state="disabled")

    def _update_deployment_controls(self, _event=None):
        if not hasattr(self, "deployment_check_button") or not self.deployment_check_button.winfo_exists():
            return
        self.deployment_check_button.configure(state="disabled" if self.deployment_busy else "normal")
        install_enabled = not self.deployment_busy and self.deployment_integration.get() == INTEGRATIONS[2]
        state = "normal" if install_enabled else "disabled"
        self.deployment_package_entry.configure(state=state)
        self.deployment_install_button.configure(state=state)

    def check_deployment_status(self):
        integration = self.deployment_integration.get()
        self._start_deployment_operation(lambda: check_status(integration), f"Checking {integration}...")

    def confirm_package_install(self):
        try:
            package_id = validate_package_id(self.deployment_package_id.get())
            executable = executable_path("winget.exe")
        except IntegrationError as error:
            messagebox.showerror("Cannot install package", str(error), parent=self.root)
            return
        if not messagebox.askyesno(
            "Confirm software installation",
            f"Install {package_id} from the configured winget source?\n\n"
            f"Executable: {executable}\n\n"
            "This runs the package's installer and accepts its package and source agreements. "
            "It may change this computer or request administrator approval. "
            "Do not close TrustGate while the installation is running.",
            parent=self.root,
        ):
            return
        self._start_deployment_operation(
            lambda: install_package(package_id, executable), f"Installing {package_id}...",
        )

    def _start_deployment_operation(self, operation, message):
        if self.deployment_busy:
            return
        self.deployment_busy = True
        self.deployment_result = message
        self._show_deployment_result()
        self._update_deployment_controls()

        def run():
            try:
                self.deployment_queue.put(operation())
            except Exception as error:
                self.deployment_queue.put(f"Operation failed: {error}")

        threading.Thread(target=run, daemon=True).start()
        self.root.after(100, self._poll_deployment_operation)

    def _poll_deployment_operation(self):
        try:
            self.deployment_result = self.deployment_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_deployment_operation)
            return
        self.deployment_busy = False
        self._show_deployment_result()
        self._update_deployment_controls()

    def printer_requests_page(self):
        tk.Label(
            self.content,
            text="Create a request for the printer team, then track its local status.",
            bg=BG, fg=MUTED, font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 14))

        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True)
        form_panel = tk.Frame(body, bg=WHITE, padx=18, pady=16)
        form_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))
        tk.Label(form_panel, text="Printer Request", bg=WHITE, fg=TEXT, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10))

        form = tk.Frame(form_panel, bg=WHITE)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.printer_request_fields = {
            "location": tk.StringVar(),
            "department": tk.StringVar(),
            "computer_name": tk.StringVar(value=os.environ.get("COMPUTERNAME", "")),
            "user_name": tk.StringVar(value=getpass.getuser()),
            "printer_type": tk.StringVar(value="Zebra Label Printer"),
            "printer_team_contact": tk.StringVar(value="printerteam@company.com"),
            "reason": tk.StringVar(value="New workstation deployment."),
            "requested_by": tk.StringVar(value=getpass.getuser()),
            "requested_by_title": tk.StringVar(value="Infrastructure Engineer"),
        }
        fields = (
            ("Location", "location", None),
            ("Department", "department", None),
            ("Computer Name", "computer_name", None),
            ("User Name", "user_name", None),
            ("Printer Type", "printer_type", ("Zebra Label Printer", "Laser Printer", "Label Printer", "Other")),
            ("Printer Team Contact", "printer_team_contact", None),
            ("Reason", "reason", None),
            ("Requested By", "requested_by", None),
            ("Requested By Title", "requested_by_title", None),
        )
        for row, (label, key, choices) in enumerate(fields):
            tk.Label(form, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 9)).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )
            if choices:
                widget = ttk.Combobox(form, textvariable=self.printer_request_fields[key], values=choices)
            else:
                widget = ttk.Entry(form, textvariable=self.printer_request_fields[key])
            widget.grid(row=row, column=1, sticky="ew", pady=4)

        tk.Button(
            form_panel, text="Generate Request", command=self.create_printer_request,
            bg=BLUE, fg=WHITE, relief="flat", padx=14, pady=8,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        ).pack(anchor="w", pady=(12, 8))
        self.printer_request_preview = tk.Text(form_panel, height=10, wrap="word", font=("Consolas", 9))
        self.printer_request_preview.pack(fill="both", expand=True)
        self.printer_request_preview.configure(state="disabled")

        actions = tk.Frame(form_panel, bg=WHITE)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Copy for ticket system", command=self.copy_printer_request).pack(side="left")
        ttk.Button(actions, text="Export PDF", command=self.export_printer_request_pdf).pack(side="left", padx=6)
        ttk.Button(actions, text="Edit Template", command=self.edit_printer_request_template).pack(side="left")

        list_panel = tk.Frame(body, bg=WHITE, padx=14, pady=14, width=290)
        list_panel.pack(side="right", fill="y")
        list_panel.pack_propagate(False)
        tk.Label(list_panel, text="Printer Requests", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self.printer_request_list = ttk.Treeview(
            list_panel, columns=("computer", "status", "created"), show="headings", height=12,
        )
        for column, title, width in (("computer", "Computer", 88), ("status", "Status", 82), ("created", "Created", 80)):
            self.printer_request_list.heading(column, text=title)
            self.printer_request_list.column(column, width=width, stretch=column == "computer")
        self.printer_request_list.tag_configure("Complete", foreground="#16723A")
        self.printer_request_list.tag_configure("Pending", foreground="#8A6500")
        self.printer_request_list.tag_configure("Failed", foreground="#B42318")
        self.printer_request_list.pack(fill="both", expand=True)
        self.printer_request_list.bind("<<TreeviewSelect>>", self.select_printer_request)
        self.selected_printer_request = None

        status_actions = tk.Frame(list_panel, bg=WHITE)
        status_actions.pack(fill="x", pady=(10, 0))
        self.printer_status_choice = tk.StringVar(value="Complete")
        ttk.Combobox(
            status_actions, textvariable=self.printer_status_choice,
            values=("Pending", "Complete", "Failed"), state="readonly", width=10,
        ).pack(side="left")
        ttk.Button(status_actions, text="Update Status", command=self.update_printer_request_status).pack(side="left", padx=(6, 0))
        self.refresh_printer_requests()

    def create_printer_request(self):
        fields = {key: value.get() for key, value in self.printer_request_fields.items()}
        try:
            request = self.printer_request_store.create_request(fields)
        except PrinterRequestError as error:
            messagebox.showwarning("Cannot generate request", str(error))
            return
        self._show_printer_request_text(request["RequestText"])
        append_activity("SUCCESS", f"Printer request created for {request['ComputerName']}")
        self.refresh_printer_requests()
        self.selected_printer_request = request

    def _show_printer_request_text(self, text):
        self.printer_request_preview.configure(state="normal")
        self.printer_request_preview.delete("1.0", "end")
        self.printer_request_preview.insert("1.0", text)
        self.printer_request_preview.configure(state="disabled")

    def select_printer_request(self, _event=None):
        selection = self.printer_request_list.selection()
        if not selection:
            return
        request_id = selection[0]
        self.selected_printer_request = next(
            (request for request in self.printer_request_store.list_requests() if request.get("Id") == request_id),
            None,
        )
        if self.selected_printer_request:
            self.printer_status_choice.set(self.selected_printer_request["Status"])
            self._show_printer_request_text(self.selected_printer_request["RequestText"])

    def refresh_printer_requests(self):
        for item in self.printer_request_list.get_children():
            self.printer_request_list.delete(item)
        try:
            requests = self.printer_request_store.list_requests()
        except PrinterRequestError as error:
            messagebox.showerror("Printer requests unavailable", str(error))
            return
        for request in reversed(requests):
            self.printer_request_list.insert(
                "", "end", iid=request["Id"],
                values=(request["ComputerName"], request["Status"], request["DateCreated"]),
                tags=(request["Status"],),
            )

    def update_printer_request_status(self):
        if not self.selected_printer_request:
            messagebox.showwarning("Select a request", "Select a printer request to update.")
            return
        try:
            self.selected_printer_request = self.printer_request_store.update_status(
                self.selected_printer_request["Id"], self.printer_status_choice.get(),
            )
        except PrinterRequestError as error:
            messagebox.showerror("Status update failed", str(error))
            return
        append_activity(
            "SUCCESS",
            f"Printer request status changed to {self.selected_printer_request['Status']} "
            f"for {self.selected_printer_request['ComputerName']}",
        )
        self.refresh_printer_requests()

    def copy_printer_request(self):
        text = self.printer_request_preview.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("No request", "Generate or select a printer request first.")
            return
        self.copy_to_clipboard(text)
        messagebox.showinfo("Copied", "Request copied for pasting into the ticket system.")

    def export_printer_request_pdf(self):
        text = self.printer_request_preview.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("No request", "Generate or select a printer request first.")
            return
        output_path = filedialog.asksaveasfilename(
            title="Export printer request",
            defaultextension=".pdf",
            initialfile="TrustGate-printer-request.pdf",
            filetypes=(("PDF document", "*.pdf"),),
        )
        if not output_path:
            return
        try:
            export_request_pdf(text, output_path)
        except OSError as error:
            messagebox.showerror("PDF export failed", str(error))
            return
        messagebox.showinfo("PDF exported", f"Saved printer request to {output_path}")

    def edit_printer_request_template(self):
        try:
            template = self.printer_request_store.load_template()
        except PrinterRequestError as error:
            messagebox.showerror("Template unavailable", str(error))
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Printer Request Template")
        dialog.geometry("680x500")
        dialog.transient(self.root)
        editor = tk.Text(dialog, wrap="word", font=("Consolas", 10))
        editor.pack(fill="both", expand=True, padx=12, pady=12)
        editor.insert("1.0", template)
        tk.Label(
            dialog,
            text="Fields: {computer_name}, {user_name}, {location}, {department}, {printer_type}, "
                 "{printer_team_contact}, {reason}, {requested_by}, {requested_by_title}, {date}",
            wraplength=640, justify="left",
        ).pack(anchor="w", padx=12)

        def save_template():
            try:
                candidate = editor.get("1.0", "end-1c")
                # Validate placeholders against a sample before replacing the saved template.
                sample = {key: key for key in (
                    "computer_name", "user_name", "location", "department", "printer_type",
                    "printer_team_contact", "reason", "requested_by", "requested_by_title", "date",
                )}
                self.printer_request_store.save_template(candidate)
                self.printer_request_store.load_template().format_map(sample)
            except (PrinterRequestError, KeyError, ValueError) as error:
                messagebox.showerror("Template not saved", str(error), parent=dialog)
                return
            dialog.destroy()

        ttk.Button(dialog, text="Save Template", command=save_template).pack(anchor="e", padx=12, pady=12)

    def company_profiles_page(self):
        tk.Label(
            self.content,
            text="Company deployment defaults",
            bg=BG, fg=MUTED, font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 18))
        if self.company_profile_error:
            self.info_page("Company profiles", self.company_profile_error)
            return

        for name, profile in self.company_profiles.items():
            panel = tk.Frame(self.content, bg=WHITE, padx=18, pady=14)
            panel.pack(fill="x", pady=(0, 10))
            tk.Label(panel, text=name, bg=WHITE, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
            details = (
                f"Domain: {profile['domain'] or 'Not set'}    "
                f"Default OU: {profile['default_ou'] or 'Not set'}\n"
                f"Printers: {', '.join(profile['printers']) or 'None'}    "
                f"Drives: {', '.join(profile['drives']) or 'None'}"
            )
            tk.Label(panel, text=details, bg=WHITE, fg=MUTED, justify="left", anchor="w", wraplength=760).pack(
                anchor="w", pady=(6, 0)
            )

    def auto_logon_page(self):
        tk.Label(
            self.content,
            text="Configure a sign-in profile for review",
            bg=BG, fg=MUTED, font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 16))

        panel = tk.Frame(self.content, bg=WHITE, padx=22, pady=18)
        panel.pack(fill="x")
        form = tk.Frame(panel, bg=WHITE)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        if not hasattr(self, "autologon_company"):
            self.autologon_company = tk.StringVar(value=next(iter(self.company_profiles), "Custom"))
            self.autologon_username = tk.StringVar()
            self.autologon_domain = tk.StringVar()
            self.autologon_password = tk.StringVar()
            self.remember_autologon_settings = tk.BooleanVar(value=False)
            self.verify_autologon_account = tk.BooleanVar(value=True)
            self.log_autologon_changes = tk.BooleanVar(value=True)

        tk.Label(form, text="Company", bg=WHITE, fg=TEXT, font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", padx=(0, 20), pady=7
        )
        self.company_picker = ttk.Combobox(
            form, textvariable=self.autologon_company,
            values=tuple(self.company_profiles), state="readonly",
        )
        self.company_picker.grid(row=0, column=1, sticky="ew", pady=7)
        self.company_picker.bind("<<ComboboxSelected>>", self.update_autologon_company)

        for row, label, variable, secret in (
            (1, "Username", self.autologon_username, False),
            (2, "Domain", self.autologon_domain, False),
            (3, "Password", self.autologon_password, True),
        ):
            tk.Label(form, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", padx=(0, 20), pady=7
            )
            ttk.Entry(form, textvariable=variable, show="*" if secret else "").grid(
                row=row, column=1, sticky="ew", pady=7
            )

        self.autologon_resources = tk.Label(
            panel, text="", bg=WHITE, fg=MUTED, justify="left", anchor="w", wraplength=760,
        )
        self.autologon_resources.pack(fill="x", pady=(12, 8))
        for label, variable in (
            ("Remember company, username, and domain for this session", self.remember_autologon_settings),
            ("Verify account before apply", self.verify_autologon_account),
            ("Log changes", self.log_autologon_changes),
        ):
            ttk.Checkbutton(panel, text=label, variable=variable).pack(anchor="w", pady=3)

        button_row = tk.Frame(self.content, bg=BG)
        button_row.pack(anchor="w", pady=16)
        tk.Button(
            button_row, text="Enable (Preview)", command=self.enable_autologon_preview,
            bg=BLUE, fg=WHITE, activebackground="#2859C8", activeforeground=WHITE,
            relief="flat", padx=15, pady=9, font=("Segoe UI", 10, "bold"), cursor="hand2",
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            button_row, text="Disable (Preview)", command=self.disable_autologon_preview,
            bg="#E8ECF3", fg=TEXT, relief="flat", padx=15, pady=9, cursor="hand2",
        ).pack(side="left", padx=8)
        tk.Button(
            button_row, text="Test", command=self.test_autologon_preview,
            bg="#E8ECF3", fg=TEXT, relief="flat", padx=15, pady=9, cursor="hand2",
        ).pack(side="left", padx=8)
        tk.Button(
            button_row, text="Close", command=lambda: self.show_page("Dashboard"),
            bg="#E8ECF3", fg=TEXT, relief="flat", padx=15, pady=9, cursor="hand2",
        ).pack(side="left", padx=8)

        tk.Label(
            self.content,
            text="Preview only. TrustGate does not configure Windows AutoAdminLogon or verify accounts. "
                 "Passwords are never remembered or written to logs.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        self.update_autologon_company()

    def update_autologon_company(self, _event=None):
        profile = self.company_profiles.get(self.autologon_company.get(), {})
        self.autologon_domain.set(profile.get("domain", ""))
        printers = ", ".join(profile.get("printers", [])) or "None"
        drives = ", ".join(profile.get("drives", [])) or "None"
        ou = profile.get("default_ou", "") or "Not set"
        self.autologon_resources.config(text=f"Default OU: {ou}\nPrinters: {printers}\nDrives: {drives}")

    def _autologon_fields_valid(self):
        missing = [
            name for name, value in (
                ("username", self.autologon_username.get().strip()),
                ("domain", self.autologon_domain.get().strip()),
                ("password", self.autologon_password.get()),
            ) if not value
        ]
        if missing:
            messagebox.showwarning("Required fields", "Enter a " + ", ".join(missing) + ".")
            return False
        return True

    def test_autologon_preview(self):
        if not self._autologon_fields_valid():
            return
        messagebox.showinfo(
            "Local validation passed",
            "Required fields are present. No network, domain, or account verification was performed.",
        )

    def enable_autologon_preview(self):
        if not self._autologon_fields_valid():
            return
        self.status_text = "Enabled (preview)"
        self._record_autologon_event("SUCCESS", "AutoLogon enable requested (preview)")
        messagebox.showinfo("Preview only", "The AutoLogon configuration was validated but not applied to Windows.")

    def disable_autologon_preview(self):
        self.status_text = "Disabled (preview)"
        self._record_autologon_event("SUCCESS", "AutoLogon disable requested (preview)")
        messagebox.showinfo("Preview only", "No Windows sign-in settings were changed.")

    def _record_autologon_event(self, status, message):
        if self.log_autologon_changes.get():
            append_activity(status, message)

    def computer_setup_page(self):
        tk.Label(
            self.content,
            text="Computer setup actions are presented for planning only; no machine or directory changes are made.",
            bg=BG, fg=MUTED, font=("Segoe UI", 11), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(4, 18))
        panel = tk.Frame(self.content, bg=WHITE, padx=20, pady=18)
        panel.pack(fill="x")
        tk.Label(panel, text="Rename computer", bg=WHITE, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.new_computer_name = tk.StringVar()
        row = tk.Frame(panel, bg=WHITE)
        row.pack(fill="x", pady=(12, 4))
        tk.Label(row, text="New computer name", bg=WHITE, fg=TEXT).pack(side="left", padx=(0, 18))
        ttk.Entry(row, textvariable=self.new_computer_name, width=30).pack(side="left")
        tk.Button(
            panel, text="Validate rename (Preview)", command=self.preview_computer_rename,
            bg=BLUE, fg=WHITE, relief="flat", padx=14, pady=8, cursor="hand2",
        ).pack(anchor="w", pady=(12, 0))

        tk.Button(
            self.content, text="Start Deployment Wizard", command=self.start_deployment_wizard,
            bg="#E8ECF3", fg=TEXT, relief="flat", padx=14, pady=9, cursor="hand2",
        ).pack(anchor="w", pady=18)

    def preview_computer_rename(self):
        computer_name = self.new_computer_name.get().strip()
        if not computer_name or len(computer_name) > 15 or not computer_name.replace("-", "").isalnum():
            messagebox.showwarning("Invalid computer name", "Use 1-15 letters, numbers, or hyphens.")
            return
        messagebox.showinfo("Preview only", f"{computer_name} is formatted for review. No rename was performed.")
        append_activity("SUCCESS", "Computer rename validated (preview)")

    def password_reset_page(self):
        tk.Label(
            self.content,
            text="Directory password changes require approved AD administration procedures.",
            bg=BG, fg=MUTED, font=("Segoe UI", 11), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(4, 18))
        panel = tk.Frame(self.content, bg=WHITE, padx=22, pady=18)
        panel.pack(fill="x")
        self.reset_username = tk.StringVar()
        self.reset_password = tk.StringVar()
        for label, variable, secret in (
            ("Username", self.reset_username, False),
            ("New password", self.reset_password, True),
        ):
            row = tk.Frame(panel, bg=WHITE)
            row.pack(fill="x", pady=7)
            tk.Label(row, text=label, bg=WHITE, fg=TEXT, width=16, anchor="w").pack(side="left")
            ttk.Entry(row, textvariable=variable, show="*" if secret else "", width=36).pack(side="left", fill="x", expand=True)
        tk.Button(
            panel, text="Validate reset request (Preview)", command=self.preview_password_reset,
            bg=BLUE, fg=WHITE, relief="flat", padx=14, pady=8, cursor="hand2",
        ).pack(anchor="w", pady=(12, 0))
        tk.Label(
            self.content,
            text="The password is not saved or logged. No account lookup or password change is performed.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(12, 0))

    def preview_password_reset(self):
        if not self.reset_username.get().strip() or not self.reset_password.get():
            messagebox.showwarning("Required fields", "Enter a username and new password.")
            return
        messagebox.showinfo("Preview only", "The reset request is complete for review. No password was changed.")
        append_activity("SUCCESS", "Password reset request validated (preview)")

    def start_deployment_wizard(self):
        self.wizard_steps = (
            "Company", "Computer Name", "Domain Join", "Software",
            "Printers", "Validation", "Report",
        )
        self.wizard_step = 0
        self.wizard_values = {"Company": next(iter(self.company_profiles), "Custom")}
        self.show_page("Deployment Wizard")

    def deployment_wizard_page(self):
        step = self.wizard_steps[self.wizard_step]
        tk.Label(
            self.content, text=f"Step {self.wizard_step + 1} of {len(self.wizard_steps)}  /  {step}",
            bg=BG, fg=MUTED, font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 14))
        panel = tk.Frame(self.content, bg=WHITE, padx=22, pady=20)
        panel.pack(fill="x")
        descriptions = {
            "Company": "Choose a company profile to load organization defaults.",
            "Computer Name": "Set the intended computer name.",
            "Domain Join": "Review the domain and OU from the selected profile.",
            "Software": "Software deployment is not connected in this preview.",
            "Printers": "Review printers and drives loaded from the company profile.",
            "Validation": "Review the collected deployment inputs. Nothing has been applied.",
            "Report": "Generate a local preview summary of this deployment plan.",
        }
        tk.Label(panel, text=descriptions[step], bg=WHITE, fg=TEXT, wraplength=700, justify="left").pack(anchor="w")

        if step == "Company":
            self.wizard_company = tk.StringVar(value=self.wizard_values.get("Company", "Custom"))
            ttk.Combobox(panel, textvariable=self.wizard_company, values=tuple(self.company_profiles), state="readonly").pack(
                anchor="w", pady=(14, 0)
            )
        elif step == "Computer Name":
            self.wizard_computer_name = tk.StringVar(value=self.wizard_values.get("Computer Name", ""))
            ttk.Entry(panel, textvariable=self.wizard_computer_name, width=32).pack(anchor="w", pady=(14, 0))
        elif step in ("Domain Join", "Printers"):
            profile = self.company_profiles.get(self.wizard_values.get("Company", ""), {})
            content = (
                f"Domain: {profile.get('domain', 'Not set')}\nOU: {profile.get('default_ou', 'Not set')}"
                if step == "Domain Join" else
                f"Printers: {', '.join(profile.get('printers', [])) or 'None'}\n"
                f"Drives: {', '.join(profile.get('drives', [])) or 'None'}"
            )
            tk.Label(panel, text=content, bg=WHITE, fg=MUTED, justify="left").pack(anchor="w", pady=(12, 0))
        elif step in ("Validation", "Report"):
            summary = "\n".join(f"{key}: {value}" for key, value in self.wizard_values.items()) or "No deployment inputs collected."
            tk.Label(panel, text=summary, bg=WHITE, fg=MUTED, justify="left").pack(anchor="w", pady=(12, 0))

        tk.Label(
            self.content, text="Preview workflow only. Domain join, software installation, and printer mapping are not executed.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(14, 0))
        controls = tk.Frame(self.content, bg=BG)
        controls.pack(fill="x", side="bottom", pady=12)
        ttk.Button(controls, text="Back", command=self.previous_wizard_step, state="normal" if self.wizard_step else "disabled").pack(side="left")
        if step == "Report":
            ttk.Button(controls, text="Generate Preview Report", command=self.generate_preview_report).pack(side="right")
        else:
            ttk.Button(controls, text="Next", command=self.next_wizard_step).pack(side="right")

    def _save_wizard_step(self):
        step = self.wizard_steps[self.wizard_step]
        if step == "Company":
            self.wizard_values[step] = self.wizard_company.get()
        elif step == "Computer Name":
            computer_name = self.wizard_computer_name.get().strip()
            if not computer_name or len(computer_name) > 15 or not computer_name.replace("-", "").isalnum():
                messagebox.showwarning("Invalid computer name", "Use 1-15 letters, numbers, or hyphens.")
                return False
            self.wizard_values[step] = computer_name
        return True

    def next_wizard_step(self):
        if self._save_wizard_step():
            self.wizard_step += 1
            self.show_page("Deployment Wizard")

    def previous_wizard_step(self):
        self._save_wizard_step()
        self.wizard_step = max(0, self.wizard_step - 1)
        self.show_page("Deployment Wizard")

    def generate_preview_report(self):
        if not self._save_wizard_step():
            return
        report_path = filedialog.asksaveasfilename(
            title="Export deployment preview",
            defaultextension=".json",
            initialfile="TrustGate-deployment-preview.json",
            filetypes=(("JSON report", "*.json"),),
        )
        if not report_path:
            return

        company = self.wizard_values.get("Company", "")
        report = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "preview_only": True,
            "plan": self.wizard_values,
            "company_defaults": self.company_profiles.get(company, {}),
            "system_changes_applied": False,
        }
        try:
            with open(report_path, "w", encoding="utf-8") as report_file:
                json.dump(report, report_file, indent=2)
        except OSError as error:
            messagebox.showerror("Report export failed", str(error))
            return

        append_activity("SUCCESS", "Deployment preview report exported")
        messagebox.showinfo("Preview report", "The deployment preview report was exported. No system changes were made.")
        self.show_page("Dashboard")

    def card(self, parent, title, value, row, column):
        box = tk.Frame(parent, bg=WHITE, padx=18, pady=17)
        box.grid(row=row, column=column, sticky="nsew", padx=(0, 12), pady=(0, 10))
        tk.Label(
            box, text=title, bg=WHITE, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        label = tk.Label(
            box, text=value, bg=WHITE, fg=TEXT,
            font=("Segoe UI", 12, "bold"), wraplength=200, justify="left",
        )
        label.pack(anchor="w", pady=(9, 0))
        return label

    def _dashboard_value(self, widget):
        if widget == "account":
            return getpass.getuser()
        if widget == "domain":
            return os.environ.get("USERDOMAIN", "Local device")
        if widget == "launch":
            return self.status_text
        if widget == "computer":
            return os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "Not available"
        if widget == "activity":
            try:
                return str(len(read_activity()))
            except OSError as error:
                return f"Unavailable: {error}"
        if widget == "printers":
            try:
                requests = self.printer_request_store.list_requests()
                if any(not isinstance(request, dict) for request in requests):
                    raise PrinterRequestError("The local printer request database has an invalid format.")
                return str(sum(
                    request.get("Status") == "Pending" for request in requests
                ))
            except (OSError, PrinterRequestError) as error:
                return f"Unavailable: {error}"
        raise ValueError(f"Unknown dashboard widget: {widget}")

    def _save_dashboard_widgets(self, widgets, page):
        if self.dashboard_error:
            messagebox.showerror("Dashboard unavailable", self.dashboard_error, parent=self.root)
            return
        try:
            self.dashboard_store.save(widgets)
        except DashboardConfigError as error:
            messagebox.showerror("Could not save dashboard", str(error), parent=self.root)
            return
        self.dashboard_widgets = widgets
        self.show_page(page)

    def _change_dashboard_widget(self, widget, action, page):
        widgets = list(self.dashboard_widgets)
        if action == "add":
            if widget in widgets:
                messagebox.showinfo("Dashboard", "That widget is already on the dashboard.", parent=self.root)
                return
            widgets.append(widget)
        elif action == "remove":
            if widget not in widgets:
                messagebox.showinfo("Dashboard", "That widget is not on the dashboard.", parent=self.root)
                return
            widgets.remove(widget)
        elif action in ("left", "right"):
            if widget not in widgets:
                messagebox.showinfo("Dashboard", "Add the widget before moving it.", parent=self.root)
                return
            index = widgets.index(widget)
            target = index + (-1 if action == "left" else 1)
            if not 0 <= target < len(widgets):
                return
            widgets[index], widgets[target] = widgets[target], widgets[index]
        else:
            raise ValueError(f"Unknown dashboard action: {action}")
        self._save_dashboard_widgets(widgets, page)

    def _edit_dashboard_widget(self, action):
        title = self.dashboard_selection.get()
        widget = next((key for key, value in MODULES.items() if value[0] == title), None)
        if widget is None:
            messagebox.showwarning("Select a widget", "Choose a widget first.", parent=self.root)
            return
        self._change_dashboard_widget(widget, action, "Dashboard")

    def _toggle_dashboard_edit(self):
        self.dashboard_editing = not self.dashboard_editing
        self.show_page("Dashboard")

    def plugin_marketplace_page(self):
        tk.Label(
            self.content,
            text="Built-in dashboard modules. No downloads or third-party code are supported.",
            bg=BG, fg=MUTED, font=("Segoe UI", 11), wraplength=760, justify="left",
        ).pack(anchor="w", pady=(4, 12))
        if self.dashboard_error:
            tk.Label(
                self.content, text=self.dashboard_error, bg=BG, fg="#B42318",
                wraplength=760, justify="left",
            ).pack(anchor="w", pady=(0, 8))
        panel = tk.Frame(self.content, bg=WHITE, padx=16, pady=14)
        panel.pack(fill="both", expand=True)
        tree_frame = tk.Frame(panel, bg=WHITE)
        tree_frame.pack(fill="both", expand=True)
        self.marketplace_tree = ttk.Treeview(
            tree_frame, columns=("name", "description", "status"), show="headings", height=7,
        )
        for column, title, width in (
            ("name", "Module", 155), ("description", "Description", 330), ("status", "Dashboard", 95),
        ):
            self.marketplace_tree.heading(column, text=title)
            self.marketplace_tree.column(column, width=width, stretch=column == "description")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.marketplace_tree.yview)
        self.marketplace_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.marketplace_tree.pack(side="left", fill="both", expand=True)
        for widget, (title, description) in MODULES.items():
            self.marketplace_tree.insert(
                "", "end", iid=widget,
                values=(
                    title, description,
                    "Unavailable" if self.dashboard_error else
                    ("Added" if widget in self.dashboard_widgets else "Available"),
                ),
            )
        controls = tk.Frame(panel, bg=WHITE)
        controls.pack(fill="x", pady=(12, 0))
        state = "disabled" if self.dashboard_error else "normal"
        ttk.Button(
            controls, text="Add to dashboard", state=state,
            command=lambda: self._marketplace_change("add"),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            controls, text="Remove from dashboard", state=state,
            command=lambda: self._marketplace_change("remove"),
        ).pack(side="left")
        ttk.Button(
            controls, text="Open dashboard", command=lambda: self.show_page("Dashboard"),
        ).pack(side="right")

    def _marketplace_change(self, action):
        selection = self.marketplace_tree.selection()
        if not selection:
            messagebox.showwarning("Select a module", "Choose a module first.", parent=self.root)
            return
        self._change_dashboard_widget(selection[0], action, "Plugin Marketplace")

    def overview(self):
        heading = tk.Frame(self.content, bg=BG)
        heading.pack(fill="x", pady=(4, 16))
        tk.Label(
            heading, text="Your access and sign-in overview",
            bg=BG, fg=MUTED, font=("Segoe UI", 11)
        ).pack(side="left")
        ttk.Button(
            heading, text="Done editing" if self.dashboard_editing else "Edit page",
            command=self._toggle_dashboard_edit,
            state="disabled" if self.dashboard_error else "normal",
        ).pack(side="right")

        if self.dashboard_error:
            tk.Label(
                self.content, text=self.dashboard_error, bg=BG, fg="#B42318",
                wraplength=760, justify="left",
            ).pack(anchor="w", pady=(0, 8))
        if self.dashboard_editing and not self.dashboard_error:
            if not hasattr(self, "dashboard_selection"):
                self.dashboard_selection = tk.StringVar(value=next(iter(MODULES.values()))[0])
            editor = tk.Frame(self.content, bg=BG)
            editor.pack(fill="x", pady=(0, 12))
            ttk.Combobox(
                editor, textvariable=self.dashboard_selection,
                values=tuple(value[0] for value in MODULES.values()), state="readonly", width=22,
            ).pack(side="left", padx=(0, 6))
            for label, action in (("Add", "add"), ("Remove", "remove"), ("Move left", "left"), ("Move right", "right")):
                ttk.Button(
                    editor, text=label, command=lambda name=action: self._edit_dashboard_widget(name),
                ).pack(side="left", padx=(0, 4))
            ttk.Button(
                editor, text="Marketplace", command=lambda: self.show_page("Plugin Marketplace"),
            ).pack(side="left")

        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")
        for column in range(3):
            cards.columnconfigure(column, weight=1)
        self.status_label = None
        for index, widget in enumerate(self.dashboard_widgets):
            label = self.card(cards, MODULES[widget][0], self._dashboard_value(widget), index // 3, index % 3)
            if widget == "launch":
                self.status_label = label

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
        tk.Button(
            actions, text="Deployment Wizard", command=self.start_deployment_wizard,
            bg="#E8ECF3", fg=TEXT, activebackground="#D9DFE9",
            relief="flat", padx=16, pady=9, font=("Segoe UI", 10),
            cursor="hand2"
        ).pack(side="left", padx=(10, 0))

        tk.Label(
            self.content,
            text="Credentials stay on this device. Platform-specific connections are not configured.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", side="bottom")

    def enable_preview(self):
        self.status_text = "Enabled (preview)"
        if self.status_label is not None:
            self.status_label.config(text=self.status_text)
        append_activity("SUCCESS", "Launch preference enabled (preview)")

    def disable_preview(self):
        self.status_text = "Disabled"
        if self.status_label is not None:
            self.status_label.config(text=self.status_text)
        append_activity("SUCCESS", "Launch preference disabled")

    def access_page(self):
        self.info_page(
            "Access management",
            "Organization sign-in and permission management are not connected in this preview."
        )

    def activity_page(self):
        tk.Label(
            self.content,
            text="Local audit events from this device",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 18))

        summary = tk.Frame(self.content, bg=BG)
        summary.pack(fill="x", pady=(0, 18))
        for column in range(3):
            summary.columnconfigure(column, weight=1, uniform="activity")
        self.activity_total = self.activity_metric(summary, "TOTAL EVENTS", 0, 0)
        self.activity_success = self.activity_metric(summary, "SUCCESSFUL", 0, 1)
        self.activity_failures = self.activity_metric(summary, "FAILED", 0, 2)

        panel = tk.Frame(self.content, bg=WHITE, padx=16, pady=14)
        panel.pack(fill="both", expand=True)

        toolbar = tk.Frame(panel, bg=WHITE)
        toolbar.pack(fill="x", pady=(0, 12))
        tk.Label(
            toolbar, text="Event history", bg=WHITE, fg=TEXT,
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        self.activity_search = tk.StringVar()
        search_box = ttk.Entry(toolbar, textvariable=self.activity_search, width=22)
        search_box.pack(side="right", padx=(8, 0))
        search_box.bind("<KeyRelease>", lambda _event: self.refresh_activity())
        self.activity_filter = tk.StringVar(value="All events")
        filter_box = ttk.Combobox(
            toolbar,
            textvariable=self.activity_filter,
            values=("All events", "Successful", "Failed"),
            state="readonly",
            width=14,
        )
        filter_box.pack(side="right", padx=(8, 0))
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_activity())
        tk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_activity,
            bg="#E8ECF3",
            fg=TEXT,
            activebackground="#D9DFE9",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9),
            cursor="hand2",
        ).pack(side="right")

        table_frame = tk.Frame(panel, bg=WHITE)
        table_frame.pack(fill="both", expand=True)
        columns = ("time", "status", "event")
        self.activity_table = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=10
        )
        self.activity_table.heading("time", text="TIME")
        self.activity_table.heading("status", text="STATUS")
        self.activity_table.heading("event", text="EVENT")
        self.activity_table.column("time", width=145, minwidth=130, stretch=False)
        self.activity_table.column("status", width=95, minwidth=85, stretch=False)
        self.activity_table.column("event", width=260, minwidth=140, stretch=True)
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.activity_table.yview
        )
        self.activity_table.configure(yscrollcommand=scrollbar.set)
        self.activity_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.activity_table.tag_configure("SUCCESS", foreground="#18794E")
        self.activity_table.tag_configure("FAILURE", foreground="#C0392B")
        self.refresh_activity()

    def activity_metric(self, parent, title, value, column):
        box = tk.Frame(parent, bg=WHITE, padx=16, pady=13)
        box.grid(row=0, column=column, sticky="nsew", padx=(0, 10))
        tk.Label(
            box, text=title, bg=WHITE, fg=MUTED,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        value_label = tk.Label(
            box, text=str(value), bg=WHITE, fg=TEXT,
            font=("Segoe UI", 19, "bold")
        )
        value_label.pack(anchor="w", pady=(5, 0))
        return value_label

    def refresh_activity(self):
        entries = read_activity()
        successes = sum(entry["status"] == "SUCCESS" for entry in entries)
        failures = sum(entry["status"] == "FAILURE" for entry in entries)
        self.activity_total.config(text=str(len(entries)))
        self.activity_success.config(text=str(successes))
        self.activity_failures.config(text=str(failures))

        for item in self.activity_table.get_children():
            self.activity_table.delete(item)

        selected_filter = self.activity_filter.get()
        if selected_filter == "Successful":
            entries = [entry for entry in entries if entry["status"] == "SUCCESS"]
        elif selected_filter == "Failed":
            entries = [entry for entry in entries if entry["status"] == "FAILURE"]

        query = self.activity_search.get().strip().casefold()
        if query:
            entries = [
                entry for entry in entries
                if query in entry["status"].casefold()
                or query in entry["message"].casefold()
                or query in entry["timestamp"].strftime("%b %d, %H:%M:%S").casefold()
            ]

        if not entries:
            self.activity_table.insert("", "end", values=("", "", "No matching activity"))
        for entry in reversed(entries):
            self.activity_table.insert(
                "",
                "end",
                values=(
                    entry["timestamp"].strftime("%b %d, %H:%M:%S"),
                    entry["status"],
                    entry["message"],
                ),
                tags=(entry["status"],),
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