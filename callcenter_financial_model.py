import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import date

# ===============================
#  MODEL: ZDALNE CALL CENTER
# ===============================

def simulate_callcenter(
    dni_pracy_miesiac=22,
    liczba_konsultantow=3,
    umawiane_spotkania_dziennie_na_osobe=6,
    odbywalnosc=1/3,
    konwersja=1/8,
    przychod_na_polisie=1875,
    koszty_miesieczne=24200,
    koszty_startowe=3900,
    miesiace=3,
    tolerancja=0.20,
    zaokraglenie_polis=True
):
    miesieczne = []
    for m in range(1, miesiace+1):
        umowione = liczba_konsultantow * dni_pracy_miesiac * umawiane_spotkania_dziennie_na_osobe
        odbyte = umowione * odbywalnosc
        polisy_float = odbyte * konwersja
        polisy = int(round(polisy_float)) if zaokraglenie_polis else polisy_float

        przychod = polisy * przychod_na_polisie
        koszt = koszty_miesieczne
        zysk = przychod - koszt

        miesieczne.append({
            "Miesiąc": m,
            "Umówione": int(umowione),
            "Odbyte": int(round(odbyte)),
            "Polisy": polisy,
            "Przychód (zł)": przychod,
            "Koszt (zł)": koszt,
            "Zysk (zł)": zysk,
        })

    df_m = pd.DataFrame(miesieczne)

    laczny_przychod = df_m["Przychód (zł)"].sum()
    laczny_koszt = df_m["Koszt (zł)"].sum() + koszty_startowe
    laczny_zysk = laczny_przychod - laczny_koszt

    marza = (laczny_zysk / laczny_przychod) * 100 if laczny_przychod else np.nan
    roi_start = (laczny_zysk / koszty_startowe) * 100 if koszty_startowe else np.nan
    roi_calk = (laczny_zysk / laczny_koszt) * 100 if laczny_koszt else np.nan

    zysk_min = laczny_zysk * (1 - tolerancja)
    zysk_max = laczny_zysk * (1 + tolerancja)

    skumulowany = (df_m["Zysk (zł)"].cumsum() - koszty_startowe).values
    miesiac_bep = int(np.argmax(skumulowany >= 0) + 1) if np.any(skumulowany >= 0) else None

    podsumowanie = pd.DataFrame([{
        "Łączny przychód (zł)": laczny_przychod,
        "Łączne koszty (zł) z startowymi": laczny_koszt,
        "Łączny zysk (zł)": laczny_zysk,
        "Zakres zysku (±20%)": f"{zysk_min:.2f} – {zysk_max:.2f}",
        "Marża zysku (%)": marza,
        "ROI vs koszty startowe (%)": roi_start,
        "ROI vs łączne koszty (%)": roi_calk,
        "Miesiąc break-even": miesiac_bep if miesiac_bep else "nieosiągnięty"
    }])

    return df_m, podsumowanie


# ===============================
#  APLIKACJA STREAMLIT
# ===============================

def main():
    st.title("📊 Model finansowy: Zdalne Call Center")

    st.sidebar.header("Parametry symulacji")
    liczba_konsultantow = st.sidebar.number_input("Liczba konsultantów", 1, 20, 3)
    dni_pracy_miesiac = st.sidebar.number_input("Dni pracy w miesiącu", 10, 31, 22)
    umawiane_spotkania = st.sidebar.number_input("Spotkania dziennie na konsultanta", 1, 20, 6)
    odbywalnosc = st.sidebar.slider("Odbywalność spotkań (1/x)", 0.05, 1.0, 1/3.0)
    konwersja = st.sidebar.slider("Konwersja na polisę (1/x)", 0.05, 1.0, 1/8.0)
    przychod_na_polisie = st.sidebar.number_input("Przychód na polisę (zł)", 500, 10000, 1875)
    koszty_startowe = st.sidebar.number_input("Koszty startowe (zł)", 0, 100000, 3900)
    miesiace = st.sidebar.slider("Liczba miesięcy symulacji", 1, 24, 3)
    tolerancja = st.sidebar.slider("Tolerancja błędu (%)", 0.0, 0.5, 0.2)

    # ===============================
    #  Kalkulator kosztów pracownika
    # ===============================
    st.header("💰 Kalkulator wynagrodzenia pracownika (pełne rozbicie kosztów)")

    rodzaj_umowy = st.radio(
        "Wybierz rodzaj umowy:",
        ["Umowa o pracę", "Umowa zlecenie", "Umowa o dzieło"],
        horizontal=True
    )

    wynagrodzenie_brutto = st.number_input(
        "Podaj miesięczne wynagrodzenie brutto jednego pracownika (zł)",
        min_value=0,
        value=5000,
        step=500
    )

    # Domyślne składki wg typu umowy
    if rodzaj_umowy == "Umowa o pracę":
        skladki = {"emerytalna": 9.76, "rentowa": 6.50, "wypadkowa": 1.67, "FP": 2.45, "FGŚP": 0.10, "PPK": 1.50}
    elif rodzaj_umowy == "Umowa zlecenie":
        skladki = {"emerytalna": 9.76, "rentowa": 6.50, "wypadkowa": 1.67, "FP": 0.00, "FGŚP": 0.00, "PPK": 0.00}
    else:
        skladki = {"emerytalna": 0.00, "rentowa": 0.00, "wypadkowa": 0.00, "FP": 0.00, "FGŚP": 0.00, "PPK": 0.00}

    st.subheader("🔧 Składki pracodawcy")
    with st.expander("Dostosuj składki ręcznie"):
        for key in skladki:
            skladki[key] = st.slider(f"{key.capitalize()} (%)", 0.0, 20.0, skladki[key])

    suma_skladek_proc = sum(skladki.values())
    koszt_pracodawcy = wynagrodzenie_brutto * (1 + suma_skladek_proc / 100)
    koszt_calosciowy = koszt_pracodawcy * liczba_konsultantow
    koszty_miesieczne = koszt_calosciowy

    # Tabela podsumowania
    st.markdown(f"""
    ### 📊 Podsumowanie kosztów ({rodzaj_umowy})
    | Pozycja | Wartość |
    |:----------------------------|----------------:|
    | Wynagrodzenie brutto | {wynagrodzenie_brutto:,.2f} zł |
    | Suma składek pracodawcy | {suma_skladek_proc:.2f}% |
    | Całkowity koszt jednego pracownika | {koszt_pracodawcy:,.2f} zł |
    | Koszt wszystkich konsultantów ({liczba_konsultantow}) | **{koszt_calosciowy:,.2f} zł** |
    """)

    # ===============================
    #  SYMULACJA
    # ===============================
    if st.sidebar.button("▶️ Uruchom symulację"):
        df_m, df_s = simulate_callcenter(
            dni_pracy_miesiac=dni_pracy_miesiac,
            liczba_konsultantow=liczba_konsultantow,
            umawiane_spotkania_dziennie_na_osobe=umawiane_spotkania,
            odbywalnosc=odbywalnosc,
            konwersja=konwersja,
            przychod_na_polisie=przychod_na_polisie,
            koszty_miesieczne=koszty_miesieczne,
            koszty_startowe=koszty_startowe,
            miesiace=miesiace,
            tolerancja=tolerancja
        )

        st.subheader("📆 Wyniki miesięczne")
        st.dataframe(df_m)

        st.subheader("📈 Podsumowanie")
        st.dataframe(df_s)

        st.subheader("📊 Trend zysku")
        st.line_chart(df_m.set_index("Miesiąc")["Zysk (zł)"])

        today = date.today().isoformat()
        path_xlsx = f"callcenter_model_{today}.xlsx"
        with pd.ExcelWriter(path_xlsx, engine="xlsxwriter") as writer:
            df_m.to_excel(writer, sheet_name="Miesięczne", index=False)
            df_s.to_excel(writer, sheet_name="Podsumowanie", index=False)

        with open(path_xlsx, "rb") as file:
            st.download_button(
                label="💾 Pobierz wyniki (Excel)",
                data=file,
                file_name=path_xlsx,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
