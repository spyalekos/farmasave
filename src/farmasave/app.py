import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import json
from datetime import datetime
from . import database
from . import calculations

class Farmasave(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Database initialization with platform-specific path
        database.set_db_path(self.paths.data)
        database.create_tables()

        # Create an OptionContainer (Tabs)
        
        # Tabs
        self.tabs = toga.OptionContainer(on_select=self.handle_tab_change)
        
        # Tab 1: Φάρμακα (Medications)
        self.med_box = self.create_medications_tab()
        self.tabs.content.append("Φάρμακα", self.med_box)
        
        # Tab 2: Πρόγραμμα (Schedule)
        self.schedule_box = self.create_schedule_tab()
        self.tabs.content.append("Πρόγραμμα", self.schedule_box)
        
        # Tab 3: Απόθεμα (Stock)
        self.stock_box = self.create_stock_tab()
        self.tabs.content.append("Απόθεμα", self.stock_box)
        
        # Tab 4: I/O
        self.io_box = self.create_io_tab()
        self.tabs.content.append("I/O", self.io_box)
        
        self.main_window.content = self.tabs
        self.main_window.show()

    def handle_tab_change(self, widget, **kwargs):
        index = widget.current_tab.index
        if index == 0:
            self.refresh_medications()
        elif index == 1:
            self.refresh_schedule()
        elif index == 2:
            self.refresh_stock()

    def create_medications_tab(self):
        self.med_table = toga.Table(
            headings=["ID", "Όνομα", "Τύπος", "Τεμ/Κουτί", "Κουτιά", "Τεμάχια", "Αρχικό", "Υπόλοιπο", "Δόση", "Έλεγχος"],
            accessors=["id", "name", "type", "ppb", "boxes", "pieces", "initial", "balance", "dosage", "inv_date"],
            on_activate=self.handle_med_activate,
            style=Pack(flex=1)
        )
        
        add_btn = toga.Button("Προσθήκη", on_press=self.handle_add_med, style=Pack(margin=5))
        refresh_btn = toga.Button("Ανανέωση", on_press=self.refresh_medications, style=Pack(margin=5))
        
        btn_box = toga.Box(children=[add_btn, refresh_btn], style=Pack(direction=ROW))
        
        container = toga.Box(
            children=[btn_box, self.med_table],
            style=Pack(direction=COLUMN, margin=10)
        )
        self.refresh_medications()
        return container

    def refresh_medications(self, widget=None):
        self.med_table.data.clear()
        meds = database.get_all_medications()
        now = datetime.now().date()
        
        for med in meds:
            id, name, type, ppb, boxes, pieces, dosage, inv_date_str = med
            initial_total = (boxes * ppb) + pieces
            dosage = dosage if dosage is not None else 0
            
            if inv_date_str:
                inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
                days_passed = (now - inv_date).days
                consumed = days_passed * dosage
                live_balance = max(0, initial_total - consumed)
            else:
                live_balance = initial_total
                inv_date_str = "-"
            
            self.med_table.data.append(
                (str(id), str(name), str(type), str(ppb), str(boxes), str(pieces), 
                 str(initial_total), str(int(live_balance)), str(dosage), str(inv_date_str))
            )

    def create_schedule_tab(self):
        self.schedule_content = toga.Box(style=Pack(direction=COLUMN, margin=5))
        self.schedule_scroll = toga.ScrollContainer(content=self.schedule_content, style=Pack(flex=1))
        
        refresh_btn = toga.Button("Ανανέωση", on_press=self.refresh_schedule, style=Pack(margin=5))
        
        container = toga.Box(
            children=[refresh_btn, self.schedule_scroll],
            style=Pack(direction=COLUMN, margin=10)
        )
        self.refresh_schedule()
        return container

    def refresh_schedule(self, widget=None):
        self.schedule_content.clear()
        earliest, depletion_list = calculations.get_depletion_info()
        
        self.schedule_content.add(toga.Label("--- Ημερομηνίες Εξάντλησης ---", style=Pack(font_weight='bold', padding_bottom=5)))
        
        if depletion_list:
            for name, date, days, stock in depletion_list:
                line = f"{date}: {name} (Υπόλοιπο: {stock:.0f}, σε {days:.1f} ημέρες)"
                self.schedule_content.add(toga.Label(line, style=Pack(padding_bottom=2)))
        else:
            self.schedule_content.add(toga.Label("Δεν υπάρχουν επαρκείς πληροφορίες."))
            
        self.schedule_content.add(toga.Divider(style=Pack(padding_top=10, padding_bottom=10)))
        self.schedule_content.add(toga.Label("--- Ημερήσιο Πρόγραμμα (30 ημέρες) ---", style=Pack(font_weight='bold', padding_bottom=5)))
        
        schedule = calculations.generate_schedule()
        for date, meds in schedule:
            line = f"{date}: {', '.join(meds)}"
            self.schedule_content.add(toga.Label(line, style=Pack(padding_bottom=2)))

    def create_stock_tab(self):
        self.stock_table = toga.Table(
            headings=["ID", "Όνομα", "Αρχικά Κουτιά", "Αρχικά Τεμάχια", "Υπόλοιπο (Τεμ)", "Αποθέματα", "Ημ. Ελέγχου"],
            accessors=["id", "name", "boxes", "pieces", "balance", "calc_stock", "inv_date"],
            on_activate=self.handle_stock_activate,
            style=Pack(flex=1)
        )
        
        refresh_btn = toga.Button("Ανανέωση", on_press=self.refresh_stock, style=Pack(margin=5))
        
        container = toga.Box(
            children=[refresh_btn, self.stock_table],
            style=Pack(direction=COLUMN, margin=10)
        )
        self.refresh_stock()
        return container

    def refresh_stock(self, widget=None):
        self.stock_table.data.clear()
        meds = database.get_all_medications()
        now = datetime.now().date()
        
        for med in meds:
            id, name, type, ppb, boxes, pieces, dosage, inv_date_str = med
            initial_total = (boxes * ppb) + pieces
            dosage = dosage if dosage is not None else 0
            
            if inv_date_str:
                inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
                days_passed = (now - inv_date).days
                consumed = days_passed * dosage
                live_balance = max(0, initial_total - consumed)
            else:
                live_balance = initial_total
                inv_date_str = "-"
            
            self.stock_table.data.append(
                (str(id), str(name), str(boxes), str(pieces), str(int(live_balance)), str(initial_total), str(inv_date_str))
            )

    def create_io_tab(self):
        export_btn = toga.Button("Εξαγωγή σε JSON", on_press=self.handle_export, style=Pack(margin=5))
        import_btn = toga.Button("Εισαγωγή από JSON", on_press=self.handle_import_dialog, style=Pack(margin=5))
        
        container = toga.Box(
            children=[
                toga.Label("Διαχείριση Δεδομένων", style=Pack(font_weight='bold', font_size=15, padding_bottom=20)),
                export_btn,
                import_btn
            ],
            style=Pack(direction=COLUMN, margin=20)
        )
        return container

    def handle_med_activate(self, widget, row):
        med_id = int(row.id)
        self.open_medication_dialog(med_data={
            'id': med_id,
            'name': row.name,
            'type': row.type,
            'ppb': row.ppb,
            'boxes': row.boxes,
            'pieces': row.pieces,
            'dosage': row.dosage,
        })

    def handle_add_med(self, widget):
        """Open empty dialog for adding new medication"""
        self.open_medication_dialog(med_data=None)

    def open_medication_dialog(self, med_data=None):
        is_edit = med_data is not None
        title = "Επεξεργασία Φαρμάκου" if is_edit else "Προσθήκη Φαρμάκου"
        
        name_input = toga.TextInput(value=med_data['name'] if is_edit else "", placeholder="Όνομα")
        type_input = toga.TextInput(value=med_data['type'] if is_edit else "", placeholder="Τύπος")
        ppb_input = toga.TextInput(value=str(med_data['ppb']) if is_edit and med_data['ppb'] is not None else "", placeholder="Τεμ/Κουτί")
        boxes_input = toga.TextInput(value=str(med_data['boxes']) if is_edit and med_data['boxes'] is not None else "", placeholder="Κουτιά")
        pieces_input = toga.TextInput(value=str(med_data['pieces']) if is_edit and med_data['pieces'] is not None else "", placeholder="Τεμάχια")
        dosage_input = toga.TextInput(value=str(med_data['dosage']) if is_edit and med_data['dosage'] is not None else "", placeholder="Δόση/Ημ.")

        content = toga.Box(
            children=[
                toga.Label("Όνομα:"), name_input,
                toga.Label("Τύπος:"), type_input,
                toga.Label("Τεμ/Κουτί:"), ppb_input,
                toga.Label("Κουτιά:"), boxes_input,
                toga.Label("Τεμάχια:"), pieces_input,
                toga.Label("Δόση/Ημ.:"), dosage_input,
            ],
            style=Pack(direction=COLUMN, margin=10)
        )

        async def save_medication(widget):
            try:
                name = name_input.value
                typ = type_input.value
                ppb = int(ppb_input.value or 0)
                boxes = int(boxes_input.value or 0)
                pieces = int(pieces_input.value or 0)
                dosage = int(dosage_input.value or 0)
            except ValueError:
                self.main_window.error_dialog("Σφάλμα", "Παρακαλώ εισάγετε έγκυρους αριθμούς.")
                return

            if not name or not typ:
                self.main_window.error_dialog("Σφάλμα", "Το όνομα και ο τύπος είναι υποχρεωτικά.")
                return

            if is_edit:
                database.update_medication(med_data['id'], name, typ, ppb, boxes, pieces, dosage)
            else:
                database.add_medication(name, typ, ppb, boxes, pieces, dosage)
            
            self.refresh_medications()
            dialog.close()

        async def delete_medication(widget):
            if await self.main_window.question_dialog("Διαγραφή", "Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το φάρμακο;"):
                database.delete_medication(med_data['id'])
                self.refresh_medications()
                dialog.close()

        save_btn = toga.Button("Αποθήκευση", on_press=save_medication, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=lambda w: dialog.close(), style=Pack(margin=5))
        
        buttons = [save_btn, cancel_btn]
        if is_edit:
            del_btn = toga.Button("Διαγραφή", on_press=delete_medication, style=Pack(margin=5, color='red'))
            buttons.insert(1, del_btn)

        button_box = toga.Box(children=buttons, style=Pack(direction=ROW))
        content.add(button_box)

        dialog = toga.Window(title=title, size=(300, 450))
        dialog.content = content
        dialog.show()

    async def handle_export(self, widget):
        """Open a save file dialog to export JSON data"""
        async def perform_export(window, path):
            if path:
                try:
                    data = database.export_data()
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    self.main_window.info_dialog("Επιτυχία", f"Τα δεδομένα εξήχθησαν στο {path}")
                except Exception as ex:
                    self.main_window.error_dialog("Σφάλμα", f"Αποτυχία εξαγωγής: {ex}")

        self.main_window.save_file_dialog(
            title="Εξαγωγή Δεδομένων",
            suggested_filename="medications_backup.json",
            file_types=['json'],
            on_result=perform_export
        )

    def handle_stock_activate(self, widget, row):
        med_id = int(row.id)
        name = row.name
        
        boxes_input = toga.TextInput(value=str(row.boxes), placeholder="Κουτιά")
        pieces_input = toga.TextInput(value=str(row.pieces), placeholder="Τεμάχια")

        content = toga.Box(
            children=[
                toga.Label(f"Ενημέρωση Αποθέματος: {name}"),
                toga.Label("Κουτιά:"), boxes_input,
                toga.Label("Τεμάχια:"), pieces_input,
            ],
            style=Pack(direction=COLUMN, margin=10)
        )

        def save_stock(widget):
            try:
                boxes = int(boxes_input.value or 0)
                pieces = int(pieces_input.value or 0)
                database.update_stock(med_id, boxes, pieces)
                self.refresh_stock()
                self.refresh_medications()
                dialog.close()
            except ValueError:
                self.main_window.error_dialog("Σφάλμα", "Παρακαλώ εισάγετε έγκυρους αριθμούς.")

        save_btn = toga.Button("Αποθήκευση", on_press=save_stock, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=lambda w: dialog.close(), style=Pack(margin=5))
        
        content.add(toga.Box(children=[save_btn, cancel_btn], style=Pack(direction=ROW)))

        dialog = toga.Window(title="Ενημέρωση Αποθέματος", size=(300, 250))
        dialog.content = content
        dialog.show()

    def handle_import_dialog(self, widget):
        """Step 1: Open file dialog to select JSON"""
        async def on_file_selected(window, path):
            if path:
                # Step 2: Open date selection dialog
                self.open_date_selection_dialog(path)

        self.main_window.open_file_dialog(
            title="Εισαγωγή Δεδομένων",
            multiple_select=False,
            file_types=['json'],
            on_result=on_file_selected
        )

    def open_date_selection_dialog(self, file_path):
        """Step 2: Ask for inventory date before importing"""
        content = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        content.add(toga.Label("Επιλέξτε Ημερομηνία Ελέγχου:", style=Pack(margin_bottom=10)))
        
        date_input = toga.DateInput(value=datetime.now().date())
        content.add(date_input)
        
        async def proceed_import(widget):
            selected_date = date_input.value.strftime("%Y-%m-%d")
            dialog.close()
            
            if await self.main_window.question_dialog(
                "Προσοχή", 
                f"Η εισαγωγή για την ημερομηνία {selected_date} θα διαγράψει ΟΛΑ τα τρέχοντα δεδομένα. Συνέχεια;"
            ):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    database.import_data(data, selected_date)
                    self.refresh_medications()
                    self.refresh_stock()
                    self.refresh_schedule()
                    self.main_window.info_dialog("Επιτυχία", "Τα δεδομένα εισήχθησαν με επιτυχία.")
                except Exception as ex:
                    self.main_window.error_dialog("Σφάλμα", f"Αποτυχία εισαγωγής: {ex}")

        save_btn = toga.Button("Εισαγωγή", on_press=proceed_import, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=lambda w: dialog.close(), style=Pack(margin=5))
        content.add(toga.Box(children=[save_btn, cancel_btn], style=Pack(direction=ROW)))

        dialog = toga.Window(title="Ημερομηνία Ελέγχου", size=(300, 200))
        dialog.content = content
        dialog.show()

def main():
    return Farmasave("Farmasave", "com.spyalekos.farmasave")
