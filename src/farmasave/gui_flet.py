import flet as ft
import os
import platform
import tempfile


from fpdf import FPDF
from . import database
from . import calculations
import json
from datetime import datetime


class PDF(FPDF):
    """Custom PDF class with page numbers in footer"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_path = "C:/Windows/Fonts/arial.ttf"
    
    def footer(self):
        # Position at 15mm from bottom
        self.set_y(-15)
        # Use Arial font if available
        if os.path.exists(self.font_path):
            self.set_font("Arial", size=8)
        else:
            self.set_font("Helvetica", size=8)
        # Page number: Σελίδα X/Y
        page_text = f"Σελίδα {self.page_no()}/{{nb}}"
        self.cell(0, 10, page_text, align='R')


class MedicationApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Διαχειριστής Φαρμάκων v2.05"
        self.page.window.width = 1200
        self.page.window.height = 700
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        
        database.create_tables()
        
        # No longer need permanent entry fields - using modal dialog
        
        # Data tables
        self.med_table = None
        self.stock_table = None
        
        # Text control for schedule
        self.schedule_text = None
        
        # Track selected medication ID
        self.selected_med_id = None
        
        self.build()
    
    
    def build(self):
        # Create navigation rail
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            on_change=self.nav_changed,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.MEDICATION,
                    selected_icon=ft.Icons.MEDICATION_OUTLINED,
                    label="Φάρμακα"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CALENDAR_MONTH,
                    label="Πρόγραμμα"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INVENTORY,
                    label="Απόθεμα"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.IMPORT_EXPORT,
                    label="I/O"
                ),
            ],
        )
        
        # Create content container
        self.content = ft.Container(
            content=self.create_medications_tab(),
            expand=True,
        )
        
        # Layout
        self.page.add(
            ft.Row(
                [
                    self.nav_rail,
                    ft.VerticalDivider(width=1),
                    self.content,
                ],
                expand=True,
            )
        )
    
    def nav_changed(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.content.content = self.create_medications_tab()
        elif idx == 1:
            self.content.content = self.create_schedule_tab()
        elif idx == 2:
            self.content.content = self.create_stock_tab()
        elif idx == 3:
            self.content.content = self.create_io_tab()
        self.page.update()
    
    
    def create_medications_tab(self):
        # Buttons - simplified without permanent input fields
        btn_row = ft.Row(
            controls=[
                ft.Button("Προσθήκη", on_click=self.add_medication, icon=ft.Icons.ADD),
                ft.Button("Επεξεργασία/Διαγραφή", on_click=self.edit_or_delete_medication, icon=ft.Icons.EDIT),
                ft.Button("Ανανέωση", on_click=self.load_medications, icon=ft.Icons.REFRESH),
            ],
            spacing=10,
        )
        
        # Data table - click row to edit
        self.med_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Όνομα", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Τύπος", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Τεμ/Κουτί", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Κουτιά", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Τεμάχια", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Αρχικό", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Υπόλοιπο", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Δόση", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
                ft.DataColumn(ft.Text("Έλεγχος", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)),
            ],
            rows=[],
        )
        
        # Hint text
        hint = ft.Text("Πατήστε σε γραμμή για επεξεργασία", size=10, italic=True, color=ft.Colors.GREY_600)
        
        table_container = ft.Column(
            controls=[self.med_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        self.load_medications()
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=btn_row, padding=10),
                    hint,
                    ft.Divider(),
                    table_container,
                ],
                expand=True,
            ),
            padding=10,
        )
    
    def create_schedule_tab(self):
        self.schedule_text = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        btn_row = ft.Row(
            controls=[
                ft.Button("Ανανέωση", on_click=self.load_schedule, icon=ft.Icons.REFRESH),
                ft.Button("Εκτύπωση", on_click=self.print_schedule, icon=ft.Icons.PRINT, visible=self.is_desktop()),
            ],
            spacing=10,
        )
        
        self.load_schedule()
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=btn_row, padding=10),
                    ft.Divider(),
                    ft.Container(content=self.schedule_text, padding=10, expand=True),
                ],
                expand=True,
            ),
            padding=10,
        )
    
    def create_stock_tab(self):
        self.stock_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Όνομα", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Κουτιά", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Τεμάχια", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Αρχικό", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Υπόλοιπο", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Έλεγχος", size=12, weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
        )
        
        table_container = ft.Column(
            controls=[self.stock_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        btn_row = ft.Row(
            controls=[
                ft.Button("Ενημέρωση Αποθέματος", on_click=self.update_stock_dialog, icon=ft.Icons.INVENTORY),
                ft.Button("Ανανέωση", on_click=self.load_stock, icon=ft.Icons.REFRESH),
                ft.Button("Εκτύπωση", on_click=self.print_stock, icon=ft.Icons.PRINT, visible=self.is_desktop()),
            ],
            spacing=10,
        )
        
        self.load_stock()
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=btn_row, padding=10),
                    ft.Divider(),
                    table_container,
                ],
                expand=True,
            ),
            padding=10,
        )
    
    def create_io_tab(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Διαχείριση Δεδομένων", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Χρησιμοποιήστε τα παρακάτω κουμπιά για να δημιουργήσετε αντίγραφα ασφαλείας ή να επαναφέρετε τα δεδομένα σας."),
                    ft.Container(height=20),
                    ft.Row(
                        controls=[
                            ft.Button(
                                "Εξαγωγή σε Αρχείο (JSON)",
                                on_click=self.export_data_click,
                                icon=ft.Icons.UPLOAD_FILE,
                            ),
                            ft.Button(
                                "Εισαγωγή από Αρχείο (JSON)",
                                on_click=self.import_data_click,
                                icon=ft.Icons.DOWNLOAD,
                            ),
                        ],
                        spacing=20,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
        )
    
    # Event handlers
    def on_med_row_click(self, e):
        """Open modal dialog to edit the clicked medication"""
        if e.control.data:
            values = e.control.data
            # values: (ID, Name, Type, ppb, boxes, pieces, total, live_balance, dosage, inv_date)
            self.selected_med_id = values[0]
            self.open_medication_dialog(med_data={
                'id': values[0],
                'name': str(values[1]),
                'type': str(values[2]),
                'ppb': str(values[3]),
                'boxes': str(values[4]),
                'pieces': str(values[5]),
                'dosage': str(values[8]),
            })
    
    def open_medication_dialog(self, med_data=None):
        """Open modal dialog for adding or editing medication"""
        is_edit = med_data is not None
        title = "Επεξεργασία Φαρμάκου" if is_edit else "Προσθήκη Φαρμάκου"
        
        # Create text fields
        name_field = ft.TextField(label="Όνομα", value=med_data['name'] if is_edit else "", autofocus=True)
        type_field = ft.TextField(label="Τύπος", value=med_data['type'] if is_edit else "")
        ppb_field = ft.TextField(label="Τεμ/Κουτί", value=med_data['ppb'] if is_edit else "", keyboard_type=ft.KeyboardType.NUMBER)
        boxes_field = ft.TextField(label="Κουτιά", value=med_data['boxes'] if is_edit else "", keyboard_type=ft.KeyboardType.NUMBER)
        pieces_field = ft.TextField(label="Τεμάχια", value=med_data['pieces'] if is_edit else "", keyboard_type=ft.KeyboardType.NUMBER)
        dosage_field = ft.TextField(label="Δόση/Ημ.", value=med_data['dosage'] if is_edit else "", keyboard_type=ft.KeyboardType.NUMBER)
        
        def save_medication(e):
            name = name_field.value
            typ = type_field.value
            
            try:
                ppb = int(ppb_field.value or 0)
                boxes = int(boxes_field.value or 0)
                pieces = int(pieces_field.value or 0)
                dosage = int(dosage_field.value or 0)
            except ValueError:
                self.show_error("Παρακαλώ εισάγετε έγκυρους αριθμούς.")
                return
            
            if not name or not typ:
                self.show_warning("Το όνομα και ο τύπος είναι υποχρεωτικά.")
                return
            
            if is_edit:
                database.update_medication(med_data['id'], name, typ, ppb, boxes, pieces, dosage)
            else:
                database.add_medication(name, typ, ppb, boxes, pieces, dosage)
            
            dialog.open = False
            self.page.update()
            self.load_medications()
        
        def cancel(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column(
                controls=[
                    name_field,
                    type_field,
                    ppb_field,
                    boxes_field,
                    pieces_field,
                    dosage_field,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Αποθήκευση", on_click=save_medication),
                ft.TextButton("Ακύρωση", on_click=cancel),
            ] if not is_edit else [
                ft.TextButton("Αποθήκευση", on_click=save_medication),
                ft.TextButton("Διαγραφή", on_click=lambda e: self.delete_medication_from_dialog(med_data['id'], dialog), style=ft.ButtonStyle(color=ft.Colors.RED_400)),
                ft.TextButton("Ακύρωση", on_click=cancel),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def load_medications(self, e=None):
        self.med_table.rows.clear()
        meds = database.get_all_medications()
        now = calculations.datetime.now().date()
        
        for med in meds:
            id, name, type, ppb, boxes, pieces, dosage, inv_date_str = med
            initial_total = (boxes * ppb) + pieces
            dosage = dosage if dosage is not None else 0
            
            if inv_date_str:
                inv_date = calculations.datetime.strptime(inv_date_str, "%Y-%m-%d").date()
                days_passed = (now - inv_date).days
                consumed = days_passed * dosage
                live_balance = max(0, initial_total - consumed)
            else:
                live_balance = initial_total
                inv_date_str = "-"
            
            row_data = (id, name, type, ppb, boxes, pieces, initial_total, live_balance, dosage, inv_date_str)
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(id), size=11)),
                    ft.DataCell(ft.Text(str(name), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(type), size=11)),
                    ft.DataCell(ft.Text(str(ppb), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(boxes), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(pieces), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(initial_total), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(int(live_balance)), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(dosage), size=11, style=ft.TextStyle(weight=ft.FontWeight.BOLD))),
                    ft.DataCell(ft.Text(str(inv_date_str), size=11)),
                ],
                on_select_change=self.on_med_row_click,
                data=row_data,
            )
            self.med_table.rows.append(row)
        
        self.page.update()
    
    def add_medication(self, e):
        """Open empty modal dialog for adding new medication"""
        self.open_medication_dialog(med_data=None)
    
    def edit_or_delete_medication(self, e):
        """Prompt user to select a medication from the table"""
        if not self.selected_med_id:
            self.show_warning("Πατήστε σε μια γραμμή του πίνακα για επεξεργασία/διαγραφή.")
            return
        # Find selected medication data and open dialog
        meds = database.get_all_medications()
        for med in meds:
            if med[0] == self.selected_med_id:
                self.open_medication_dialog(med_data={
                    'id': med[0],
                    'name': str(med[1]),
                    'type': str(med[2]),
                    'ppb': str(med[3]),
                    'boxes': str(med[4]),
                    'pieces': str(med[5]),
                    'dosage': str(med[6]) if med[6] else "0",
                })
                return
        self.show_warning("Δεν βρέθηκε το επιλεγμένο φάρμακο.")
    
    def delete_medication_from_dialog(self, med_id, dialog):
        """Delete medication from within the edit dialog"""
        if not med_id:
            return
        
        def confirm_delete(e):
            database.delete_medication(med_id)
            dialog.open = False
            confirm_dialog.open = False
            self.selected_med_id = None
            self.page.update()
            self.load_medications()
        
        def cancel_delete(e):
            confirm_dialog.open = False
            self.page.update()
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Διαγραφή"),
            content=ft.Text("Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το φάρμακο;"),
            actions=[
                ft.TextButton("Ναι", on_click=confirm_delete),
                ft.TextButton("Όχι", on_click=cancel_delete),
            ],
        )
        self.page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        self.page.update()
    
    def delete_medication(self, e):
        if not self.selected_med_id:
            self.show_warning("Επιλέξτε ένα φάρμακο για διαγραφή.")
            return
        
        def confirm_delete(e):
            med_id = self.selected_med_id
            database.delete_medication(med_id)
            self.load_medications()
            self.clear_med_entries()
            dialog.open = False
            self.page.update()
        
        def cancel_delete(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Διαγραφή"),
            content=ft.Text("Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το φάρμακο;"),
            actions=[
                ft.TextButton("Ναι", on_click=confirm_delete),
                ft.TextButton("Όχι", on_click=cancel_delete),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def load_schedule(self, e=None):
        self.schedule_text.controls.clear()
        earliest, depletion_list = calculations.get_depletion_info()
        
        # Header
        self.schedule_text.controls.append(
            ft.Text("--- Ημερομηνίες Εξάντλησης ---", size=14, weight=ft.FontWeight.BOLD)
        )
        
        if depletion_list:
            for name, date, days, stock in depletion_list:
                line = f"{date}: {name} (Υπόλοιπο: {stock:.0f}, σε {days:.1f} ημέρες)"
                self.schedule_text.controls.append(ft.Text(line, size=12))
        else:
            self.schedule_text.controls.append(ft.Text("Δεν υπάρχουν επαρκείς πληροφορίες.", size=12))
        
        self.schedule_text.controls.append(ft.Container(height=20))
        
        # Daily schedule
        self.schedule_text.controls.append(
            ft.Text("--- Ημερήσιο Πρόγραμμα (30 ημέρες) ---", size=14, weight=ft.FontWeight.BOLD)
        )
        
        schedule = calculations.generate_schedule()
        for date, meds in schedule:
            line = f"{date}: {', '.join(meds)}"
            self.schedule_text.controls.append(ft.Text(line, size=11))
        
        self.page.update()
    
    def load_stock(self, e=None):
        self.stock_table.rows.clear()
        meds = database.get_all_medications()
        now = calculations.datetime.now().date()
        
        for med in meds:
            id, name, typ, ppb, boxes, pieces, dosage, inv_date_str = med
            initial_total = (boxes * ppb) + pieces
            dosage = dosage if dosage is not None else 0
            
            if inv_date_str:
                inv_date = calculations.datetime.strptime(inv_date_str, "%Y-%m-%d").date()
                days_passed = (now - inv_date).days
                consumed = days_passed * dosage
                live_balance = max(0, initial_total - consumed)
            else:
                live_balance = initial_total
                inv_date_str = "-"
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(id), size=11)),
                    ft.DataCell(ft.Text(str(name), size=11)),
                    ft.DataCell(ft.Text(str(boxes), size=11)),
                    ft.DataCell(ft.Text(str(pieces), size=11)),
                    ft.DataCell(ft.Text(str(initial_total), size=11)),
                    ft.DataCell(ft.Text(str(int(live_balance)), size=11)),
                    ft.DataCell(ft.Text(str(inv_date_str), size=11)),
                ],
                data=(id, name, boxes, pieces),
            )
            self.stock_table.rows.append(row)
        
        self.page.update()
    
    def update_stock_dialog(self, e):
        # Find selected row
        selected_row = None
        for row in self.stock_table.rows:
            if row.selected:
                selected_row = row
                break
        
        if not selected_row:
            return
        
        med_id, name, current_boxes, current_pieces = selected_row.data
        
        boxes_field = ft.TextField(label="Κουτιά", value=str(current_boxes), keyboard_type=ft.KeyboardType.NUMBER)
        pieces_field = ft.TextField(label="Τεμάχια", value=str(current_pieces), keyboard_type=ft.KeyboardType.NUMBER)
        
        def save_stock(e):
            try:
                boxes = int(boxes_field.value or 0)
                pieces = int(pieces_field.value or 0)
                database.update_stock(med_id, boxes, pieces)
                self.load_stock()
                dialog.open = False
                self.page.update()
            except ValueError:
                self.show_error("Παρακαλώ εισάγετε έγκυρους αριθμούς.")
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Ενημέρωση Αποθέματος - {name}"),
            content=ft.Column(
                controls=[boxes_field, pieces_field],
                tight=True,
            ),
            actions=[
                ft.TextButton("Αποθήκευση", on_click=save_stock),
                ft.TextButton("Ακύρωση", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def export_data_click(self, e):
        # Ask for export file path
        path_field = ft.TextField(
            label="Πλήρης διαδρομή αρχείου (π.χ. C:\\backup.json)",
            value="medications_backup.json",
            width=400
        )
        
        def save_export(e):
            filename = path_field.value
            if filename:
                self.export_data_file(filename)
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Εξαγωγή Δεδομένων"),
            content=path_field,
            actions=[
                ft.TextButton("Αποθήκευση", on_click=save_export),
                ft.TextButton("Ακύρωση", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def import_data_click(self, e):
        # Ask for import file path
        path_field = ft.TextField(
            label="Πλήρης διαδρομή αρχείου (π.χ. C:\\backup.json)",
            width=400
        )
        
        def load_import(e):
            filename = path_field.value
            if filename:
                self.import_data_file(filename)
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Εισαγωγή Δεδομένων"),
            content=path_field,
            actions=[
                ft.TextButton("Άνοιγμα", on_click=load_import),
                ft.TextButton("Ακύρωση", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def export_data_file(self, filename):
        if not filename:
            return
        
        try:
            data = database.export_data()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.show_success("Τα δεδομένα εξήχθησαν με επιτυχία.")
        except Exception as ex:
            self.show_error(f"Αποτυχία εξαγωγής: {ex}")
    
    def import_data_file(self, filename):
        if not filename:
            return
        
        # Ask for inventory date
        default_date = datetime.now().strftime("%Y-%m-%d")
        inv_date_field = ft.TextField(label="Ημερομηνία Ελέγχου (YYYY-MM-DD)", value=default_date)
        
        def proceed_import(e):
            inv_date = inv_date_field.value
            
            # Validate date
            try:
                datetime.strptime(inv_date, "%Y-%m-%d")
            except ValueError:
                self.show_error("Μη έγκυρη μορφή ημερομηνίας. Παρακαλώ χρησιμοποιήστε YYYY-MM-DD.")
                return
            
            date_dialog.open = False
            self.page.update()
            
            # Confirm data loss
            self.confirm_import(filename, inv_date)
        
        date_dialog = ft.AlertDialog(
            title=ft.Text("Ημερομηνία Ελέγχου"),
            content=inv_date_field,
            actions=[
                ft.TextButton("OK", on_click=proceed_import),
                ft.TextButton("Ακύρωση", on_click=lambda e: self.close_dialog(date_dialog)),
            ],
        )
        self.page.overlay.append(date_dialog)
        date_dialog.open = True
        self.page.update()
    
    def confirm_import(self, filename, inv_date):
        def do_import(e):
            if e.control.text == "Ναι":
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    database.import_data(data, inv_date)
                    
                    # Reload everything
                    self.load_medications()
                    self.load_stock()
                    self.load_schedule()
                    
                    self.show_success("Τα δεδομένα εισήχθησαν με επιτυχία.")
                except Exception as ex:
                    self.show_error(f"Αποτυχία εισαγωγής: {ex}")
            
            confirm_dialog.open = False
            self.page.update()
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Προσοχή"),
            content=ft.Text("Η εισαγωγή θα διαγράψει ΟΛΑ τα τρέχοντα δεδομένα. Συνέχεια;"),
            actions=[
                ft.TextButton("Ναι", on_click=do_import),
                ft.TextButton("Όχι", on_click=do_import),
            ],
        )
        self.page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        self.page.update()
    
    def is_desktop(self):
        return platform.system() in ["Windows", "Darwin", "Linux"]

    def print_schedule(self, e):
        self.print_content("Πρόγραμμα Ανάλωσης Φαρμάκων", self.schedule_text.controls)

    def print_stock(self, e):
        """Print stock as a formatted table"""
        try:
            # Create PDF - landscape A4 with page numbers
            pdf = PDF(orientation='L', format='A4')
            pdf.alias_nb_pages()
            
            # Set margins
            left_margin = 15
            pdf.set_margins(left_margin, 15, 15)
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            # Add Unicode font
            font_path = "C:/Windows/Fonts/arial.ttf"
            if os.path.exists(font_path):
                pdf.add_font("Arial", "", font_path)
                pdf.add_font("Arial", "B", "C:/Windows/Fonts/arialbd.ttf")
                pdf.set_font("Arial", size=10)
            else:
                pdf.set_font("Helvetica", size=10)
            
            # Title
            pdf.set_font_size(14)
            pdf.cell(0, 10, "Κατάσταση Αποθήκης Φαρμάκων", align='C')
            pdf.ln()
            pdf.set_font_size(8)
            pdf.cell(0, 6, datetime.now().strftime('%d/%m/%Y %H:%M'), align='C')
            pdf.ln(10)
            
            # Table settings
            col_widths = [100, 30, 30, 30, 40, 40]  # Όνομα, Κουτιά, Τεμάχια, Αρχικό, Υπόλοιπο, Έλεγχος
            headers = ["Όνομα", "Κουτιά", "Τεμάχια", "Αρχικό", "Υπόλοιπο", "Έλεγχος"]
            
            # Draw header row
            pdf.set_font_size(10)
            if os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(200, 200, 200)  # Light gray background
            
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, border=1, align='C', fill=True)
            pdf.ln()
            
            # Draw data rows
            pdf.set_font("Arial", "", 9) if os.path.exists(font_path) else pdf.set_font("Helvetica", "", 9)
            
            for row in self.stock_table.rows:
                # Extract cell values: ID, Name, Boxes, Pieces, Initial, Balance, InvDate
                name = str(row.cells[1].content.value) if hasattr(row.cells[1].content, 'value') else ""
                boxes = str(row.cells[2].content.value) if hasattr(row.cells[2].content, 'value') else ""
                pieces = str(row.cells[3].content.value) if hasattr(row.cells[3].content, 'value') else ""
                initial = str(row.cells[4].content.value) if hasattr(row.cells[4].content, 'value') else ""
                balance = str(row.cells[5].content.value) if hasattr(row.cells[5].content, 'value') else ""
                inv_date = str(row.cells[6].content.value) if hasattr(row.cells[6].content, 'value') else ""
                
                # Truncate name if too long
                name = name[:35] if len(name) > 35 else name
                
                pdf.cell(col_widths[0], 7, name, border=1, align='L')
                pdf.cell(col_widths[1], 7, boxes, border=1, align='C')
                pdf.cell(col_widths[2], 7, pieces, border=1, align='C')
                pdf.cell(col_widths[3], 7, initial, border=1, align='C')
                pdf.cell(col_widths[4], 7, balance, border=1, align='C')
                pdf.cell(col_widths[5], 7, inv_date, border=1, align='C')
                pdf.ln()
            
            # Save and open
            temp_dir = tempfile.gettempdir()
            filename = f"kilofarm_stock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(temp_dir, filename)
            pdf.output(pdf_path)
            
            os.startfile(pdf_path)
            self.show_success("Το PDF άνοιξε για εκτύπωση")
            
        except Exception as ex:
            self.show_error(f"Σφάλμα PDF: {str(ex)[:80]}")

    def print_content(self, title, content_controls):
        """Generate PDF and open it for printing"""
        try:
            # Create PDF - landscape A4 with page numbers
            pdf = PDF(orientation='L', format='A4')
            pdf.alias_nb_pages()  # Enable total page count
            
            # Set margins FIRST before add_page
            left_margin = 15
            right_margin = 15
            pdf.set_margins(left_margin, 15, right_margin)
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            # Calculate effective width: A4 landscape = 297mm, minus margins
            effective_width = 297 - left_margin - right_margin
            
            # Add Unicode font for Greek support
            font_path = "C:/Windows/Fonts/arial.ttf"
            if os.path.exists(font_path):
                pdf.add_font("Arial", "", font_path)
                pdf.set_font("Arial", size=10)
            else:
                pdf.set_font("Helvetica", size=10)
            
            # Add title (centered)
            pdf.set_font_size(14)
            pdf.cell(effective_width, 10, title, align='C')
            pdf.ln()
            pdf.set_font_size(8)
            date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
            pdf.cell(effective_width, 6, date_str, align='C')
            pdf.ln(10)
            
            # Reset to left margin
            pdf.set_x(left_margin)
            
            # Extract and print content
            pdf.set_font_size(9)
            lines = self._extract_text_lines(content_controls)
            for line in lines:
                if line and line.strip():
                    # Reset X to left margin before each line
                    pdf.set_x(left_margin)
                    # Truncate to be safe
                    safe_line = line[:180] if len(line) > 180 else line
                    pdf.multi_cell(effective_width, 5, safe_line)
            
            # Save to temp file
            temp_dir = tempfile.gettempdir()
            filename = f"kilofarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(temp_dir, filename)
            pdf.output(pdf_path)
            
            # Open PDF with default viewer
            os.startfile(pdf_path)
            self.show_success(f"Το PDF άνοιξε για εκτύπωση")
            
        except Exception as ex:
            self.show_error(f"Σφάλμα PDF: {str(ex)[:80]}")
    
    def _extract_text_lines(self, controls):
        """Extract text lines from Flet controls"""
        lines = []
        for control in controls:
            if isinstance(control, ft.Text):
                if control.value:
                    lines.append(str(control.value))
            elif isinstance(control, ft.DataTable):
                for row in control.rows:
                    cells = []
                    for cell in row.cells:
                        try:
                            if hasattr(cell.content, 'value') and cell.content.value:
                                cells.append(str(cell.content.value))
                        except:
                            pass
                    if cells:
                        lines.append(" | ".join(cells))
            elif isinstance(control, ft.Column):
                lines.extend(self._extract_text_lines(control.controls))
        return lines

    # Helper methods
    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()
    
    def show_error(self, message):
        self.show_snackbar(message, ft.Colors.RED_400)
    
    def show_warning(self, message):
        self.show_snackbar(message, ft.Colors.ORANGE_400)
    
    def show_success(self, message):
        self.show_snackbar(message, ft.Colors.GREEN_400)
    
    def show_snackbar(self, message, color):
        snackbar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=color,
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()


def main(page: ft.Page):
    MedicationApp(page)


if __name__ == "__main__":
    ft.run(main)
