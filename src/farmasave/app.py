import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import json
from datetime import datetime
import sys

# Robust Java Access (Rubicon vs Chaquopy Native)
AndroidJavaClass = None
java_import_error = None

def get_android_class(class_name):
    """Helper to get Java classes using Chaquopy (primary) or Rubicon"""
    # Prefer Chaquopy's jclass as it's the native bridge for modern BeeWare/Android
    try:
        from java import jclass
        return jclass(class_name)
    except ImportError:
        try:
            from rubicon.java import JavaClass
            return JavaClass(class_name)
        except ImportError:
            print(f"DEBUG: No Java bridge available for {class_name}")
            return None
    except Exception as e:
        print(f"DEBUG: Error loading class {class_name}: {e}")
        return None

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
        """Ask for storage permissions using Native Java via Rubicon/Chaquopy"""
        Python = get_android_class("com.chaquo.python.Python")
        if not Python:
            print("DEBUG: Java bridge not available, skipping permission request")
            return
            
        try:
            print("DEBUG: Attempting Native Java Permission Request...")
            
            # Get context
            context = Python.getPlatform().getApplication()
            
            # Check Android version first
            Build = get_android_class("android.os.Build")
            sdk_int = Build.VERSION.SDK_INT
            print(f"DEBUG: Android SDK version: {sdk_int}")
            
            if sdk_int >= 30:  # Android 11+ (R)
                # For Android 11+, we need MANAGE_EXTERNAL_STORAGE
                Environment = get_android_class("android.os.Environment")
                is_manager = Environment.isExternalStorageManager()
                
                if not is_manager:
                    print("DEBUG: Need MANAGE_EXTERNAL_STORAGE, launching settings...")
                    Settings = get_android_class("android.provider.Settings")
                    Uri = get_android_class("android.net.Uri")
                    Intent = get_android_class("android.content.Intent")
                    
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    uri = Uri.parse("package:" + context.getPackageName())
                    intent.setData(uri)
                    
                    # FLAG_ACTIVITY_NEW_TASK required for Application Context
                    FLAG_ACTIVITY_NEW_TASK = 0x10000000
                    intent.addFlags(FLAG_ACTIVITY_NEW_TASK)
                    
                    context.startActivity(intent)
                else:
                    print("DEBUG: MANAGE_EXTERNAL_STORAGE already granted.")
            else:
                # For Android 10 and below, use ActivityCompat
                # Try to get Activity for permission request
                try:
                    activity = Python.getPlatform().getActivity()
                    
                    Manifest = get_android_class("android.Manifest")
                    ActivityCompat = get_android_class("androidx.core.app.ActivityCompat")
                    PackageManager = get_android_class("android.content.pm.PackageManager")
                    ContextCompat = get_android_class("androidx.core.content.ContextCompat")
                    
                    if all([Manifest, ActivityCompat, PackageManager, ContextCompat]):
                        perms = [
                            Manifest.permission.READ_EXTERNAL_STORAGE,
                            Manifest.permission.WRITE_EXTERNAL_STORAGE,
                        ]
                        
                        missing_perms = []
                        for p in perms:
                            if ContextCompat.checkSelfPermission(activity, p) != PackageManager.PERMISSION_GRANTED:
                                missing_perms.append(p)
                        
                        if missing_perms:
                            print(f"DEBUG: Missing permissions: {missing_perms}. Requesting now...")
                            ActivityCompat.requestPermissions(activity, missing_perms, 1001)
                        else:
                            print("DEBUG: All permissions already granted.")
                    else:
                        print("DEBUG: Could not load all required classes for permission check")
                        # Fallback to Toga permissions
                        if toga_request_permissions:
                            toga_request_permissions(["android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"])
                except Exception as e:
                    print(f"DEBUG: ActivityCompat failed: {e}, trying Toga fallback")
                    if toga_request_permissions:
                        toga_request_permissions(["android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"])
                    
        except Exception as e:
            print(f"DEBUG: Native Permission Request failed: {e}")


    def request_android_permissions_manual(self, widget):
        """Manual trigger for permissions using robust loading"""
        self.main_window.info_dialog("DEBUG", "Starting Permission Check...")
        
        # Test loading a basic class
        Python = get_android_class("com.chaquo.python.Python")
        
        if not Python:
            self.main_window.info_dialog("Error", "Could not load Java Bridge.\nWe are likely not on Android.")
            return

        try:
            # Get Context (Application Context is safer via Chaquopy Platform)
            # Python.getPlatform().getActivity() does not exist in some versions.
            context = Python.getPlatform().getApplication()
            
            # Version Check
            Build = get_android_class("android.os.Build")
            sdk_int = Build.VERSION.SDK_INT
            
            self.main_window.info_dialog("DEBUG", f"Bridge OK.\nSDK: {sdk_int}")
            
            if sdk_int >= 30: # Android 11+ (R)
                Environment = get_android_class("android.os.Environment")
                is_manager = Environment.isExternalStorageManager()
                
                if not is_manager:
                    self.main_window.info_dialog("Action", "Launching 'All Files Access'.")
                    
                    Settings = get_android_class("android.provider.Settings")
                    Uri = get_android_class("android.net.Uri")
                    Intent = get_android_class("android.content.Intent")
                    
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    uri = Uri.parse("package:" + context.getPackageName())
                    intent.setData(uri)
                    
                    # REQUIRED for starting activity from Application Context
                    FLAG_ACTIVITY_NEW_TASK = 0x10000000
                    intent.addFlags(FLAG_ACTIVITY_NEW_TASK)
                    
                    context.startActivity(intent)
                else:
                     self.main_window.info_dialog("Success", "Already granted (Manager)!")
            
            else: # Android 10 and below
                # Fallback to Toga logic or raw intent
                if toga_request_permissions:
                     toga_request_permissions(["android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"])
                self.main_window.info_dialog("Info", "Standard request sent.")

        except Exception as e:
            self.main_window.error_dialog("Error", f"Crash during request:\n{e}")

    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Database initialization
        database.set_db_path(self.paths.data)
        database.create_tables()

        # Custom Greek menu groups
        ARXEIO_GROUP = toga.Group("Αρχείο", order=0)
        PROBOLI_GROUP = toga.Group("Προβολή", order=1)
        VOITHEIA_GROUP = toga.Group("Βοήθεια", order=99)

        # Wrapper functions for async handlers
        # Standard Toga handlers are automatically async-aware
        # Wrapper functions for async handlers
        async def do_import(widget):
            print("DEBUG: Import command triggered from menu")
            await self.trigger_import_logic()
        
        async def do_export(widget):
            print("DEBUG: Export command triggered from menu")
            await self.trigger_export_logic()

        # Commands for the menu
        self.import_cmd = toga.Command(
            do_import,
            text="Εισαγωγή JSON",
            tooltip="Εισαγωγή δεδομένων από αρχείο JSON",
            group=ARXEIO_GROUP,
            order=1
        )
        self.export_cmd = toga.Command(
            do_export,
            text="Εξαγωγή JSON",
            tooltip="Εξαγωγή δεδομένων σε αρχείο JSON",
            group=ARXEIO_GROUP,
            order=2
        )
        # ... rest of commands ...
        self.schedule_view_cmd = toga.Command(
            self.handle_schedule_view,
            text="Ανάλωση (Πρόγραμμα)",
            tooltip="Μετάβαση στο πρόγραμμα αναλώσεων",
            group=PROBOLI_GROUP,
            order=1
        )
        self.stock_view_cmd = toga.Command(
            self.handle_stock_view,
            text="Απόθεμα (Έλεγχος)",
            tooltip="Μετάβαση στον έλεγχο αποθεμάτων",
            group=PROBOLI_GROUP,
            order=2
        )
        
        # Only add custom commands, NOT about (Toga handles About automatically)
        self.commands.add(self.import_cmd, self.export_cmd, self.schedule_view_cmd, self.stock_view_cmd)

        # Create an OptionContainer (Tabs)
        
        # Tabs - Applying color style (Turquoise for active/contrast)
        self.tabs = toga.OptionContainer(
            on_select=self.handle_tab_change, 
            style=Pack(flex=1, color="turquoise")
        )
        
        # Tab 1: Φάρμακα (Medications)
        self.med_box = self.create_medications_tab()
        self.tabs.content.append("Φάρμακα", self.med_box)

        # Version label footer
        self.med_box.add(toga.Label("v2.5.1 (Stability Fix)", style=Pack(font_size=8, text_align='right', padding=5)))
        
        # Tab 2: Ανάλωση (Schedule/Consumption)
        self.schedule_box = self.create_schedule_tab()
        self.tabs.content.append("Ανάλωση", self.schedule_box)
        
        # Tab 3: Απόθεμα (Stock)
        self.stock_box = self.create_stock_tab()
        self.tabs.content.append("Απόθεμα", self.stock_box)
        
        # Tab 4: I/O (Export/Import)
        self.io_box = self.create_io_tab()
        self.tabs.content.append("I/O", self.io_box)
        
        self.main_window.content = self.tabs
        self.main_window.show()

        # POST-SHOW SETUP (CRITICAL: Show window BEFORE calling dialogs/tasks)
        async def initial_setup(app):
            print("DEBUG: initial_setup background task started")
            if self.is_android():
                # Give a small buffer for the window to settle
                import asyncio
                await asyncio.sleep(0.5)
                # Visual confirmation for the user
                await self.main_window.dialog(toga.InfoDialog("Farmasave v2.5.1", "Η εφαρμογή ξεκίνησε επιτυχώς!"))
                self.request_android_permissions()

        self.add_background_task(initial_setup)

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

    def onActivityResult(self, requestCode, resultCode, data):
        """Native Android callback for activity results (called by MainActivity)"""
        print(f"DEBUG: onActivityResult sync start: {requestCode}")
        # Delegate to async handler
        self.add_background_task(lambda app: self._async_onActivityResult(requestCode, resultCode, data))

    async def _async_onActivityResult(self, requestCode, resultCode, data):
        """Async handler for activity results"""
        print(f"DEBUG: _async_onActivityResult start: {requestCode}")
        
        # PROVIDE VISUAL FEEDBACK
        await self.main_window.dialog(toga.InfoDialog("DEBUG", f"Data received! code={requestCode}"))
        
        # RESULT_OK is -1
        if resultCode != -1:
            print("DEBUG: Result not OK, ignoring.")
            return

        if data is None:
            print("DEBUG: Data is None, ignoring.")
            return

        uri = data.getData()
        if uri is None:
            print("DEBUG: URI is None, ignoring.")
            return

        if requestCode == 1001:  # IMPORT
            print(f"DEBUG: Import URI received: {uri}")
            await self._handle_import_uri(uri)
        elif requestCode == 1002:  # EXPORT
            print(f"DEBUG: Export URI received: {uri}")
            await self._handle_export_uri(uri)

    def _get_activity(self):
        """Helper to get the singleton MainActivity"""
        try:
            return get_android_class("org.beeware.android.MainActivity").singletonThis
        except Exception as e:
            print(f"DEBUG: Failed to get activity: {e}")
            return None

    async def _handle_import_uri(self, uri):
        """Read data from the selected URI for import"""
        try:
            activity = self._get_activity()
            if not activity:
                raise Exception("MainActivity not available")
            content_resolver = activity.getContentResolver()
            input_stream = content_resolver.openInputStream(uri)
            
            # Read bytes from stream
            bytes_data = []
            while True:
                b = input_stream.read()
                if b == -1: break
                bytes_data.append(b)
            input_stream.close()
            
            content_str = bytes(bytes_data).decode('utf-8')
            data = json.loads(content_str)
            
            # Now show date dialog or proceed directly
            selected_date = datetime.now().strftime("%Y-%m-%d")
            confirm = await self.main_window.dialog(toga.QuestionDialog(
                "Επιβεβαίωση",
                "Η εισαγωγή θα διαγράψει ΟΛΑ τα τρέχοντα δεδομένα. Συνέχεια;"
            ))
            
            if confirm:
                database.import_data(data, selected_date)
                self.refresh_medications()
                self.refresh_stock()
                self.refresh_schedule()
                await self.main_window.dialog(toga.InfoDialog("Επιτυχία", "Η εισαγωγή ολοκληρώθηκε!"))
        except Exception as e:
            print(f"DEBUG: Import Error: {e}")
            await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εισαγωγής:\n{e}"))

    async def _handle_export_uri(self, uri):
        """Write data to the selected URI for export on Android"""
        try:
            print(f"DEBUG: _handle_export_uri started for {uri}")
            data = database.export_data()
            print(f"DEBUG: Export data collected: {len(data)} items")
            
            content_str = json.dumps(data, ensure_ascii=False, indent=4)
            data_bytes = content_str.encode('utf-8')
            print(f"DEBUG: JSON byte length: {len(data_bytes)}")
            
            activity = self._get_activity()
            if not activity:
                raise Exception("MainActivity not available")
            content_resolver = activity.getContentResolver()
            
            # Use "wt" to truncate existing file
            output_stream = content_resolver.openOutputStream(uri, "wt")
            if output_stream is None:
                raise Exception("Could not open output stream")
                
            output_stream.write(data_bytes)
            output_stream.flush()
            output_stream.close()
            
            print("DEBUG: Export successful")
            await self.main_window.dialog(toga.InfoDialog("Επιτυχία", f"Η εξαγωγή ολοκληρώθηκε!\n({len(data)} φάρμακα)"))
        except Exception as e:
            print(f"DEBUG: Export Error: {e}")
            await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εξαγωγής:\n{e}"))

    def is_android(self):
        """Check if running on Android using sys.platform"""
        return sys.platform == "android"

    async def trigger_export_logic(self):
        """Unified export logic for all platforms"""
        print("DEBUG: trigger_export_logic called")
        suggested_name = f"meds_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        if self.is_android():
            try:
                print("DEBUG: Triggering Android Export Intent")
                Intent = get_android_class("android.content.Intent")
                intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("application/json")
                intent.putExtra(Intent.EXTRA_TITLE, suggested_name)
                
                activity = self._get_activity()
                if not activity:
                    print("DEBUG: MainActivity not available")
                    await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", "Το Android Activity δεν βρέθηκε."))
                    return
                print("DEBUG: Launching Intent...")
                activity.startActivityForResult(intent, 1002)
                print("DEBUG: Intent launched successfully")
            except Exception as ex:
                print(f"DEBUG: Android Export triggering error: {ex}")
                await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εκκίνησης Intent: {ex}"))
        else:
            # Desktop
            print("DEBUG: Triggering Toga Desktop Export Dialog")
            dialog = toga.SaveFileDialog(
                title="Εξαγωγή Δεδομένων",
                suggested_filename=suggested_name,
                file_types=['json'],
            )
            path = await self.main_window.dialog(dialog)
            print(f"DEBUG: Desktop Export Path: {path}")
            if path:
                try:
                    data = database.export_data()
                    with open(str(path), 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    await self.main_window.dialog(toga.InfoDialog("Επιτυχία", "Η εξαγωγή JSON ολοκληρώθηκε!"))
                except Exception as ex:
                    print(f"DEBUG: Desktop Export Error: {ex}")
                    await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία: {ex}"))

    async def trigger_import_logic(self):
        """Unified import logic for all platforms"""
        print("DEBUG: trigger_import_logic called")
        if self.is_android():
            try:
                print("DEBUG: Triggering Android Import Intent")
                Intent = get_android_class("android.content.Intent")
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("application/json")
                
                activity = self._get_activity()
                if not activity:
                    print("DEBUG: MainActivity not available")
                    await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", "Το Android Activity δεν βρέθηκε."))
                    return
                print("DEBUG: Launching Intent...")
                activity.startActivityForResult(intent, 1001)
                print("DEBUG: Intent launched successfully")
            except Exception as ex:
                print(f"DEBUG: Android Import triggering error: {ex}")
                await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εκκίνησης Intent: {ex}"))
        else:
            # Desktop
            print("DEBUG: Triggering Toga Desktop Import Dialog")
            dialog = toga.OpenFileDialog(
                title="Εισαγωγή Δεδομένων",
                multiple_select=False,
                file_types=['json'],
            )
            path = await self.main_window.dialog(dialog)
            print(f"DEBUG: Desktop Import Path: {path}")
            if path:
                await self.open_date_selection_dialog(path)

    def create_io_tab(self):
        """Build the data management tab"""
        async def handle_export_btn(widget):
            print("DEBUG: Export button clicked in I/O tab")
            await self.trigger_export_logic()

        async def handle_import_btn(widget):
            print("DEBUG: Import button clicked in I/O tab")
            await self.trigger_import_logic()

        async def check_java_bridge(widget):
            res = []
            try:
                from java import jclass
                res.append("Chaquopy: OK")
                try:
                    Intent = jclass("android.content.Intent")
                    res.append("Intent Class: OK")
                except: res.append("Intent Class: FAIL")
            except:
                res.append("Chaquopy: FAIL")
            
            try:
                from rubicon.java import JavaClass
                res.append("Rubicon: OK")
            except:
                res.append("Rubicon: FAIL")
                
            await self.main_window.dialog(toga.InfoDialog("Java Bridge Status", "\n".join(res)))

        export_btn = toga.Button("Εξαγωγή σε JSON", on_press=handle_export_btn, style=Pack(margin=5))
        import_btn = toga.Button("Εισαγωγή από JSON", on_press=handle_import_btn, style=Pack(margin=5))
        
        debug_btn = toga.Button(
            "Έλεγχος Java Bridge (Debug)",
            on_press=check_java_bridge,
            style=Pack(margin=5, background_color="gray", color="white")
        )
        
        perm_btn = toga.Button(
            "Έλεγχος Δικαιωμάτων (Permissions)",
            on_press=self.request_android_permissions_manual,
            style=Pack(margin=5, background_color="orange", color="white")
        )
        
        container = toga.Box(
            children=[
                toga.Label("Διαχείριση Δεδομένων", style=Pack(font_weight='bold', font_size=15, margin_bottom=20)),
                debug_btn,
                perm_btn,
                toga.Box(style=Pack(height=10)),
                export_btn,
                import_btn,
                toga.Box(style=Pack(height=20)),
                toga.Label("Cross-platform Import/Export (v2.5.0)", 
                          style=Pack(font_size=10, text_align='center'))
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

    async def _run_export(self):
        """Async wrapper for export - called via add_background_task"""
        try:
            print("DEBUG: _run_export started")
            suggested_name = f"meds_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            dialog = toga.SaveFileDialog(
                title="Εξαγωγή Δεδομένων",
                suggested_filename=suggested_name,
                file_types=['json'],
            )
            path = await self.main_window.dialog(dialog)
            print(f"DEBUG: Export path selected: {path}")
            if path:
                data = database.export_data()
                export_path = str(path)
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                await self.main_window.dialog(toga.InfoDialog("Επιτυχία", f"Τα δεδομένα εξήχθησαν επιτυχώς.\nΑρχείο: {os.path.basename(export_path)}"))
        except Exception as ex:
            print(f"DEBUG: Export Error: {ex}")
            await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εξαγωγής: {ex}"))

    async def _run_import(self):
        """Async wrapper for import - called via add_background_task"""
        try:
            print("DEBUG: _run_import started")
            dialog = toga.OpenFileDialog(
                title="Εισαγωγή Δεδομένων",
                multiple_select=False,
                file_types=['json'],
            )
            path = await self.main_window.dialog(dialog)
            print(f"DEBUG: Import path selected: {path}")
            if path:
                await self._open_date_dialog_for_import(path)
        except Exception as ex:
            print(f"DEBUG: Import Error: {ex}")
            await self.main_window.dialog(toga.ErrorDialog("Σφάλμα", f"Αποτυχία εισαγωγής: {ex}"))

    async def _open_date_dialog_for_import(self, file_path):
        """Date selection for import"""
        content = toga.Box(style=Pack(direction=COLUMN, margin=10))
        content.add(toga.Label("Επιλέξτε Ημερομηνία Ελέγχου:", style=Pack(margin_bottom=10)))
        
        date_input = toga.DateInput(value=datetime.now().date())
        content.add(date_input)
        
        # Store file_path in self for access in nested function
        self._pending_import_path = file_path
        self._pending_date_input = date_input
        
        def do_proceed_import(widget):
            self.add_background_task(lambda app: self._finish_import())
        
        save_btn = toga.Button("Εισαγωγή", on_press=do_proceed_import, style=Pack(margin=5))
        cancel_btn = toga.Button("Ακύρωση", on_press=self.restore_tabs, style=Pack(margin=5))
        content.add(toga.Box(children=[save_btn, cancel_btn], style=Pack(direction=ROW)))
        self.show_view(content)

    async def _finish_import(self):
        """Complete the import after date selection"""
        try:
            selected_date = self._pending_date_input.value.strftime("%Y-%m-%d")
            import_path = str(self._pending_import_path)
            
            self.restore_tabs()
            
            confirm = await self.main_window.dialog(toga.QuestionDialog(
                "Προσοχή", 
                f"Η εισαγωγή για την ημερομηνία {selected_date} θα διαγράψει ΟΛΑ τα τρέχοντα δεδομένα. Συνέχεια;"
            ))
            
            if confirm:
                print(f"DEBUG: Importing from {import_path}")
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
    return Farmasave("Farmasave", "com.spyalekos.farmasave", version="2.4.1")
