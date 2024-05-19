import re
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import folium_static


def geocode_address(geolocator, address):
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        else:
            return (None, None)
    except Exception as e:
        return (None, None)


def clean_address_data(df):
    def extract_street_number(row):
        # Überprüfen, ob Hausnummer leer ist und Straße eine Nummer enthält
        if (pd.isna(row['Hausnummer']) or row['Hausnummer'] == "") and isinstance(row['Straße'], str):
            street_number = re.search(r'\b\d+[a-zA-Z]*\b', row['Straße'])
            if street_number:
                row['Hausnummer'] = street_number.group()
                row['Straße'] = row['Straße'].replace(row['Hausnummer'], '').strip()
        return row

    df = df.apply(extract_street_number, axis=1)

    def combine_street_and_number(row):
        # Überprüfen, ob Straße leer ist und Hausnummer eine Straße enthält
        if (pd.isna(row['Straße']) or row['Straße'] == "") and isinstance(row['Hausnummer'], str):
            street_name = re.search(r'^\D+', row['Hausnummer'])
            if street_name:
                row['Straße'] = street_name.group().strip()
                row['Hausnummer'] = row['Hausnummer'].replace(row['Straße'], '').strip()
        return row

    df = df.apply(combine_street_and_number, axis=1)
    return df


def main():
    st.title("Adresspunkte auf einer Karte anzeigen")

    # Lade die CSV-Datei hoch
    uploaded_file = st.file_uploader("Lade eine CSV-Datei hoch", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file, delimiter=';')

        # Zeige die Daten an
        st.write("Adressdaten:", df)

        # Bereinige die Adressdaten
        df = clean_address_data(df)

        geolocator = Nominatim(user_agent="address-mapper")

        # Überprüfen und bereinigen der PLZ-Spalte
        df['PLZ'] = df['PLZ'].fillna(0).astype(int).astype(str).str.zfill(4)  # PLZ als String mit führenden Nullen

        # Erstelle eine Spalte mit den vollständigen Adressen
        df['Adresse'] = df.apply(
            lambda row: f"{row['Straße']} {row['Hausnummer']}, {row['PLZ']} {row['Stadt']}, {row['Land']}", axis=1)

        # Initialisiere die Listen für Latitude und Longitude
        latitudes = []
        longitudes = []

        # Initialisiere den Fortschrittsbalken
        progress_bar = st.progress(0)
        total = len(df)
        processed = 0

        # Füge Latitude und Longitude Spalten hinzu
        for address in df['Adresse']:
            latitude, longitude = geocode_address(geolocator, address)
            latitudes.append(latitude)
            longitudes.append(longitude)
            processed += 1
            progress_bar.progress(processed / total)

        df['Latitude'] = latitudes
        df['Longitude'] = longitudes

        # Filtere ungültige Adressen heraus
        df = df.dropna(subset=['Latitude', 'Longitude'])

        # Überprüfe die zurückgegebenen Koordinaten
        st.write("Geokodierte Daten:", df[['Adresse', 'Latitude', 'Longitude']])

        # Erstelle die Karte
        if not df.empty:
            m = folium.Map(location=[df['Latitude'].mean(), df['Longitude'].mean()], zoom_start=6)

            # Füge Marker zur Karte hinzu
            for _, row in df.iterrows():
                folium.Marker([row['Latitude'], row['Longitude']],
                              popup=f"{row['Vorname']} {row['Nachname']}, {row['Straße']} {row['Hausnummer']}, {row['PLZ']} {row['Stadt']}").add_to(
                    m)

            # Zeige die Karte an
            folium_static(m)
        else:
            st.warning("Keine gültigen Adressen gefunden.")


if __name__ == "__main__":
    main()
