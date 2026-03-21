# 1KOMMA5GRAD Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1.0+-blue.svg)](https://www.home-assistant.io/)

Eine Home Assistant Custom Integration fuer 1KOMMA5GRAD Heartbeat Systeme.

## Uebersicht

Diese Integration verbindet dein 1KOMMA5GRAD Heartbeat System mit Home Assistant und ermoeglicht die Ueberwachung aller Energiekomponenten in Echtzeit.

**Unterstuetzte Laender:** Deutschland, Oesterreich, Schweiz

## Features

- **Live-Daten** (alle 30 Sekunden aktualisiert):
  - Photovoltaik (Solarproduktion)
  - Netzbezug / Netzeinspeisung
  - Batterie (Lade-/Entladeleistung und Ladestand)
  - Waermepumpe
  - Wallbox / E-Auto Ladung
  - Haushaltsverbrauch
  - Gesamtverbrauch
  - Eigenverbrauchsquote
  - Autarkiegrad

- **Historische Energiedaten** (stuendlich aktualisiert, in kWh) fuer langfristige Statistiken und das Energy Dashboard

## Installation

### HACS (empfohlen)

1. Oeffne HACS in Home Assistant
2. Klicke auf "Integrations"
3. Klicke auf die drei Punkte oben rechts und waehle "Custom repositories"
4. Fuege die Repository-URL hinzu und waehle "Integration" als Kategorie
5. Suche nach "1KOMMA5GRAD" und installiere die Integration
6. Starte Home Assistant neu

### Manuelle Installation

1. Kopiere den Ordner `custom_components/einsk5g` in dein Home Assistant `custom_components` Verzeichnis
2. Starte Home Assistant neu

## Konfiguration

1. Gehe zu Einstellungen -> Geraete & Dienste
2. Klicke auf "Integration hinzufuegen"
3. Suche nach "1KOMMA5GRAD"
4. Gib deine 1KOMMA5GRAD App Zugangsdaten ein (E-Mail und Passwort)

## Entitaeten

Nach der Einrichtung werden folgende Sensoren erstellt:

### Leistungssensoren (Watt)

| Sensor | Beschreibung |
|--------|--------------|
| `sensor.einsk5g_photovoltaic` | Aktuelle PV-Produktion |
| `sensor.einsk5g_grid_consumption` | Aktueller Netzbezug |
| `sensor.einsk5g_grid_feedin` | Aktuelle Netzeinspeisung |
| `sensor.einsk5g_battery` | Batterie Lade-/Entladeleistung |
| `sensor.einsk5g_battery_soc` | Batterie Ladestand (%) |
| `sensor.einsk5g_heat_pump` | Waermepumpen-Verbrauch |
| `sensor.einsk5g_wallbox` | Wallbox-Verbrauch |
| `sensor.einsk5g_household` | Haushaltsverbrauch |
| `sensor.einsk5g_total_consumption` | Gesamtverbrauch |

### Energiesensoren (kWh)

Diese Sensoren zeigen die Energiewerte fuer die Verwendung im Home Assistant Energy Dashboard.

## Energy Dashboard

Die Sensoren sind kompatibel mit dem Home Assistant Energy Dashboard. Verwende die `_energy` Sensoren fuer:

- Solar-Produktion: `sensor.einsk5g_photovoltaic_energy`
- Netzbezug: `sensor.einsk5g_grid_consumption_energy`
- Netzeinspeisung: `sensor.einsk5g_grid_feedin_energy`
- Batterie: Lade- und Entladesensoren

## Entwicklung

### Lokale Entwicklung

```bash
# Repository klonen
git clone <repository-url>
cd 1komma5grad

# .env Datei erstellen (wird nicht ins Git committed)
cp .env.example .env
# Dann USERNAME und PASSWORD in .env eintragen
```

### Projektstruktur

```
1komma5grad/
├── custom_components/
│   └── einsk5g/
│       ├── __init__.py      # Integration Setup
│       ├── api.py           # API Client
│       ├── config_flow.py   # UI Konfiguration
│       ├── const.py         # Konstanten
│       ├── coordinator.py   # Daten-Koordinator
│       ├── manifest.json    # HA Manifest
│       ├── sensor.py        # Sensor Entitaeten
│       └── strings.json     # Uebersetzungen
├── hacs.json                # HACS Konfiguration
├── .gitignore
└── README.md
```

## Technische Details

### API-Endpunkte

Die Integration nutzt die offizielle 1KOMMA5GRAD API:

| Endpunkt | Beschreibung |
|----------|--------------|
| `auth.1komma5grad.com` | Authentifizierung (OAuth2/Auth0) |
| `heartbeat.1komma5grad.com` | Live-Daten und Verlauf |
| `customer-identity.1komma5grad.com` | Benutzerinformationen |

### Authentifizierung

Die Integration verwendet OAuth2 mit Auth0 zur sicheren Authentifizierung. Die Zugangsdaten sind dieselben wie fuer die 1KOMMA5GRAD App.

### Update-Intervalle

| Datentyp | Intervall |
|----------|-----------|
| Live-Daten (Leistung) | 30 Sekunden |
| Historische Daten (Energie) | 1 Stunde |

### Voraussetzungen

- Home Assistant 2024.1.0 oder neuer
- Ein aktives 1KOMMA5GRAD Konto mit eingerichtetem Heartbeat System
- Zugangsdaten zur 1KOMMA5GRAD App

## Fehlerbehebung

### Haeufige Probleme

**"Ungueltige Zugangsdaten"**
- Pruefe, ob E-Mail und Passwort korrekt sind
- Teste die Zugangsdaten in der 1KOMMA5GRAD App

**"Kein System gefunden"**
- Stelle sicher, dass ein Heartbeat System in der App eingerichtet ist
- Pruefe, ob das System online ist

**Sensoren zeigen "Unbekannt"**
- Einige Sensoren sind nur verfuegbar, wenn die entsprechende Hardware installiert ist (z.B. Wallbox, Waermepumpe)

## Mitwirken

Beitraege sind willkommen! Bitte erstelle einen Pull Request oder oeffne ein Issue bei Problemen.

## Lizenz

MIT License

## Danksagung

Diese Integration ist ein Community-Projekt und steht in keiner offiziellen Verbindung zu 1KOMMA5 GmbH.
