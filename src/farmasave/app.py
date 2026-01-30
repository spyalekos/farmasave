import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import json
from datetime import datetime
# Separate imports to diagnose exactly what is missing
java_import_error = None
try:
    from rubicon.java import JavaClass
except ImportError as e:
    JavaClass = None
    java_import_error = str(e)

try:
    from android.permissions import request_permissions as toga_request_permissions
except ImportError:
    toga_request_permissions = None

from . import database
from . import calculations

class Farmasave(toga.App):
    def on_exit(self, **kwargs):
        """Handle the Android back button / exit attempt"""
        # 1. If we are in a sub-view (like Add Medication), go back to tabs
        if self.main_window.content != self.tabs:
            self.restore_tabs()
            return False
        
        # 2. If we are in a tab other than the first one, go back to Tab 0
        if self.tabs.current_tab != self.tabs.content[0]:
            self.switch_to_tab(0)
            return False
            
        # 3. Otherwise, allow exit
        return True

    def show_view(self, content):
        """Replace main window content with a scrollable view (Android-friendly)"""
        # Wrapping in ScrollContainer ensures fields aren't hidden by keyboard
        scaler = toga.ScrollContainer(content=content, style=Pack(flex=1))
        self.main_window.content = scaler

    def request_android_permissions(self):
        """Ask for storage permissions using Native Java (ActivityCompat) via Chaquopy"""
        if JavaClass:
            try:
                print("DEBUG: Attempting Native Java Permission Request...")
                
                # Get the current Activity
                Python = JavaClass("com.chaquo.python.Python")
                app_context = Python.getPlatform().getApplication()
                
                # We need the Activity, not just Application context, for ActivityCompat
                # In Chaquopy/Briefcase, the main activity usually holds the Python instance
                # We can try to get it via Python.getPlatform().getActivity() if available, 
                # or fallback to Toga's internal reference if exposed.
                
                # Toga Android creates a MainActivity. Let's try traversing.
                # Actually, Chaquopy 10+ exposes Python.getPlatform().getActivity()
                activity = Python.getPlatform().getActivity()
                
                # Import Android classes
                Manifest = JavaClass("android.Manifest")
                ActivityCompat = JavaClass("androidx.core.app.ActivityCompat")
                PackageManager = JavaClass("android.content.pm.PackageManager")
                ContextCompat = JavaClass("androidx.core.content.ContextCompat")
                
                # Define permissions
                perms = [
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE,
                ]
                
                # Check if we already have them
                missing_perms = []
                for p in perms:
                    if ContextCompat.checkSelfPermission(activity, p) != PackageManager.PERMISSION_GRANTED:
                        missing_perms.append(p)
                
                if missing_perms:
                    print(f"DEBUG: Missing permissions: {missing_perms}. Requesting now...")
                    ActivityCompat.requestPermissions(activity, missing_perms, 1001)
                else:
                    print("DEBUG: All permissions already granted.")
                    
            except Exception as e:
                print(f"DEBUG: Native Permission Request failed: {e}")

    def request_android_permissions_manual(self, widget):
        """Manual trigger for permissions with visual feedback and Android 11+ support"""
        if not JavaClass:
            msg = f"Not on Android or No Java access.\nError: {java_import_error}"
            self.main_window.info_dialog("Info", msg)
            return

        try:
            # Get Context/Activity
            Python = JavaClass("com.chaquo.python.Python")
            activity = Python.getPlatform().getActivity()
            
            # Version Check
            Build = JavaClass("android.os.Build")
            sdk_int = Build.VERSION.SDK_INT
            
            self.main_window.info_dialog("DEBUG", f"Checking Permissions...\nSDK: {sdk_int}")
            
            if sdk_int >= 30: # Android 11+ (R)
                Environment = JavaClass("android.os.Environment")
                is_manager = Environment.isExternalStorageManager()
                
                if not is_manager:
                    self.main_window.info_dialog("Action", "Launching Android 11+ 'All Files Access' screen.\nPlease enable Farmasave.")
                    
                    Settings = JavaClass("android.provider.Settings")
                    Uri = JavaClass("android.net.Uri")
                    Intent = JavaClass("android.content.Intent")
                    
                    # Intent.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    uri = Uri.parse("package:com.spyalekos")
                    intent.setData(uri)
                    activity.startActivity(intent)
                else:
                     self.main_window.info_dialog("Success", "Android 11+ Storage Manager permission already granted!")
            
            else: # Android 10 and below
                self.request_android_permissions() # Re-use existing logic
                self.main_window.info_dialog("Info", "Standard permission request sent.\nCheck for popups.")

        except Exception as e:
            self.main_window.error_dialog("Error", f"Failed to launch permission request:\n{e}")

    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Trigger permission request immediately (silent attempt)
        self.add_background_task(lambda a: self.request_android_permissions())
        
        # Database initialization with platform-specific path
        database.set_db_path(self.paths.data)
        database.create_tables()

        # Commands for the menu (especially for Android)
        self.import_cmd = toga.Command(
            self.handle_import_dialog,
            text="Εισαγωγή JSON",
            tooltip="Εισαγωγή δεδομένων από αρχείο JSON",
            group=toga.Group.FILE,
            order=1
        )
        self.export_cmd = toga.Command(
            self.handle_export,
            text="Εξαγωγή JSON",
            tooltip="Εξαγωγή δεδομένων σε αρχείο JSON",
            group=toga.Group.FILE,
            order=2
        )
        self.schedule_view_cmd = toga.Command(
            self.handle_schedule_view,
            text="Ανάλωση (Πρόγραμμα)",
            tooltip="Μετάβαση στο πρόγραμμα αναλώσεων",
            group=toga.Group.VIEW,
            order=3
        )
        self.stock_view_cmd = toga.Command(
            self.handle_stock_view,
            text="Απόθεμα (Έλεγχος)",
            tooltip="Μετάβαση στον έλεγχο αποθεμάτων",
            group=toga.Group.VIEW,
            order=4
        )
        
        self.about_cmd = toga.Command(
            lambda w: self.about(),
            text="Σχετικά με το Farmasave",
            group=toga.Group.HELP
        )
        
        self.commands.add(self.import_cmd, self.export_cmd, self.schedule_view_cmd, self.stock_view_cmd, self.about_cmd)
        # Note: Removing toolbar.add to allow system menu (About) to show correctly on Android

        # Create an OptionContainer (Tabs)
        
        # Tabs - Applying color style (Turquoise for active/contrast)
        self.tabs = toga.OptionContainer(
            on_select=self.handle_tab_change, 
            style=Pack(flex=1, color="turquoise")
        )
        
        # Tab 1: Φάρμακα (Medications)
        self.med_box = self.create_medications_tab()
        self.tabs.content.append("Φάρμακα", self.med_box, icon="resources/star.png")

        # Version label footer
        self.med_box.add(toga.Label("v2.1.3", style=Pack(font_size=8, text_align='right', padding=5)))
        
        # Tab 2: Ανάλωση (Schedule/Consumption)
        self.schedule_box = self.create_schedule_tab()
        self.tabs.content.append("Ανάλωση", self.schedule_box, icon="resources/star.png")
        
        # Tab 3: Απόθεμα (Stock)
        self.stock_box = self.create_stock_tab()
        self.tabs.content.append("Απόθεμα", self.stock_box, icon="resources/star.png")
        
        # Tab 4: I/O (Export/Import)
        self.io_box = self.create_io_tab()
        self.tabs.content.append("I/O", self.io_box, icon="resources/star.png")
        
        self.main_window.content = self.tabs
        self.main_window.show()

    def restore_tabs(self, widget=None):
        """Restore the main tab view"""
        self.main_window.content = self.tabs

    def handle_schedule_view(self, widget):
        self.switch_to_tab(1)

    def handle_stock_view(self, widget):
        self.switch_to_tab(2)

    def switch_to_tab(self, index):
        """Switch to a specific tab by index safely"""
        self.restore_tabs()
        # Ensure we target the actual tab object in the OptionContainer
        target_tab = self.tabs.content[index]
        self.tabs.current_tab = target_tab

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
        
        # Manual permission button for Android 11+ or failed auto-requests
        perm_btn = toga.Button(
            "Έλεγχος Δικαιωμάτων (Permissions)",
            on_press=self.request_android_permissions_manual,
            style=Pack(margin=5, background_color="orange", color="white")
        )
        
        container = toga.Box(
            children=[
                toga.Label("Διαχείριση Δεδομένων", style=Pack(font_weight='bold', font_size=15, padding_bottom=20)),
                perm_btn, # Add permission button first
                toga.Box(style=Pack(height=10)), # Spacer
                export_btn,
                import_btn
            ],
            style=Pack(direction=COLUMN, margin=20)
        )
        return container

    async def handle_med_activate(self, widget, row):
        med_id = int(row.id)
        await self.open_medication_dialog(med_data={
            'id': med_id,
            'name': row.name,
            'type': row.type,
            'ppb': row.ppb,
            'boxes': row.boxes,
            'pieces': row.pieces,
            'dosage': row.dosage,
        })

    async def handle_add_med(self, widget):
        """Open empty dialog for adding new medication"""
        await self.open_medication_dialog(med_data=None)

    async def open_medication_dialog(self, med_data=None):
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
                await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", "Παρακαλώ εισάγετε έγκυρους αριθμούς."))
                return

            if not name or not typ:
                await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", "Το όνομα και ο τύπος είναι υποχρεωτικά."))
                return

            if is_edit:
                database.update_medication(med_data['id'], name, typ, ppb, boxes, pieces, dosage)
            else:
                database.add_medication(name, typ, ppb, boxes, pieces, dosage)
            
            self.refresh_medications()
            self.restore_tabs()

        async def delete_medication(widget):
            if await self.main_window.question_dialog("Διαγραφή", "Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το φάρμακο;"):
                database.delete_medication(med_data['id'])
                self.refresh_medications()
                self.restore_tabs()

        save_btn = toga.Button("Αποθήκευση", on_press=save_medication, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=self.restore_tabs, style=Pack(margin=5))
        
        btn_box = toga.Box(children=[save_btn, cancel_btn], style=Pack(direction=ROW))
        
        if is_edit:
            del_btn = toga.Button("Διαγραφή", on_press=delete_medication, style=Pack(margin=5))
            btn_box.add(del_btn)
            
        content.add(btn_box)
        self.show_view(content)

    async def handle_export(self, widget):
        """Open a save file dialog to export JSON data"""
        async def perform_export(window, path):
            if path:
                try:
                    data = database.export_data()
                    
                    # Convert to string path safely for open()
                    export_path = str(path)
                    print(f"DEBUG: Exporting to {export_path}")
                    
                    with open(export_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    await self.main_window.dialog(toga.InfoDialog("Επιτυχία", f"Τα δεδομένα εξήχθησαν επιτυχώς.\nΑρχείο: {os.path.basename(export_path)}"))
                except Exception as ex:
                    print(f"DEBUG: Export Error: {ex}")
                    await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εξαγωγής: {ex}\nΠροσπαθήστε να αποθηκεύσετε στο φάκελο 'Λήψεις' (Downloads)."))

        suggested_name = f"meds_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        dialog = toga.SaveFileDialog(
            title="Εξαγωγή Δεδομένων",
            suggested_filename=suggested_name,
            file_types=['json'],
        )
        path = await self.main_window.dialog(dialog)
        if path:
            await perform_export(self.main_window, path)

    async def handle_stock_activate(self, widget, row):
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

        async def save_stock(widget):
            try:
                boxes = int(boxes_input.value or 0)
                pieces = int(pieces_input.value or 0)
                database.update_stock(med_id, boxes, pieces)
                self.refresh_stock()
                self.refresh_medications()
                self.restore_tabs()
            except ValueError:
                await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", "Παρακαλώ εισάγετε έγκυρους αριθμούς."))

        save_btn = toga.Button("Αποθήκευση", on_press=save_stock, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=self.restore_tabs, style=Pack(margin=5))
        
        content.add(toga.Box(children=[save_btn, cancel_btn], style=Pack(direction=ROW)))
        self.show_view(content)

    async def handle_import_dialog(self, widget):
        """Step 1: Open file dialog to select JSON"""
        dialog = toga.OpenFileDialog(
            title="Εισαγωγή Δεδομένων",
            multiple_select=False,
            file_types=['json'],
        )
        path = await self.main_window.dialog(dialog)
        if path:
            # Step 2: Open date selection dialog
            await self.open_date_selection_dialog(path)

    async def open_date_selection_dialog(self, file_path):
        """Step 2: Ask for inventory date before importing"""
        content = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        content.add(toga.Label("Επιλέξτε Ημερομηνία Ελέγχου:", style=Pack(margin_bottom=10)))
        
        date_input = toga.DateInput(value=datetime.now().date())
        content.add(date_input)
        
        async def proceed_import(widget):
            selected_date = date_input.value.strftime("%Y-%m-%d")
            self.restore_tabs()
            
            if await self.main_window.dialog(toga.QuestionDialog(
                "Προσοχή", 
                f"Η εισαγωγή για την ημερομηνία {selected_date} θα διαγράψει ΟΛΑ τα τρέχοντα δεδομένα. Συνέχεια;"
            )):
                try:
                    # Convert to string path safely
                    import_path = str(file_path)
                    print(f"DEBUG: Importing from {import_path}")
                    
                    if not os.path.exists(import_path):
                        # On Android, OpenFileDialog might return a URI-like path or a restricted path
                        # Here we try to see if we can read it
                        print(f"DEBUG: Path {import_path} does not exist according to os.path.exists")
                    
                    with open(import_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    database.import_data(data, selected_date)
                    self.refresh_medications()
                    self.refresh_stock()
                    self.refresh_schedule()
                    await self.main_window.dialog(toga.InfoDialog("Επιτυχία", "Η εισαγωγή ολοκληρώθηκε!"))
                except json.JSONDecodeError:
                    await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", "Το αρχείο δεν είναι έγκυρο JSON."))
                except Exception as ex:
                    print(f"DEBUG: Import Error: {ex}")
                    await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εισαγωγής: {ex}"))

        save_btn = toga.Button("Εισαγωγή", on_press=proceed_import, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=self.restore_tabs, style=Pack(margin=5))
        content.add(toga.Box(children=[save_btn, cancel_btn], style=Pack(direction=ROW)))
        self.show_view(content)

def main():
    return Farmasave("Farmasave", "com.spyalekos.farmasave")
