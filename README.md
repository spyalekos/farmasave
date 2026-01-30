# Farmasave

Διαχειριστής Φαρμάκων για Android - Medication Manager App

## Χαρακτηριστικά

- Διαχείριση φαρμάκων (προσθήκη, επεξεργασία, διαγραφή)
- Υπολογισμός ημερομηνιών εξάντλησης
- Έλεγχος αποθεμάτων
- Εισαγωγή/Εξαγωγή δεδομένων σε JSON
- Ελληνική γλώσσα

## Εγκατάσταση

Κατεβάστε το τελευταίο APK από τα [Releases](https://github.com/spyalekos/farmasave/releases).

## Build

### Android APK (Briefcase)

```bash
briefcase build android
```

Το APK δημιουργείται στο: `build/farmasave/android/gradle/app/build/outputs/apk/debug/app-debug.apk`

### Desktop (Linux/Windows/macOS)

```bash
briefcase run
```

## Changelog

### v2.1.7 (2026-01-30)
- **Διόρθωση**: Επίλυση bug στα δικαιώματα Android (undefined JavaClass)
- **Βελτίωση**: Προσθήκη MANAGE_EXTERNAL_STORAGE για Android 11+
- **Βελτίωση**: Αυτόματο άνοιγμα ρυθμίσεων "All Files Access" σε Android 11+

### v2.1.6
- Αρχική έκδοση με Toga/Briefcase

## Άδεια

Proprietary - SpyAlekos