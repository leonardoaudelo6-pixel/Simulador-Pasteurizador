import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
import pandas as pd

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Monitor Tecnico de Pasteurizacion", layout="wide")

# --- FUNCIONES DE PROPIEDADES ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL: INPUTS ---
st.sidebar.title("Panel de Control")

with st.sidebar.expander("MANTENIMIENTO", expanded=True):
    t_dias = st.number_input("Dias sin limpiar", value=0, min_value=0)

with st.sidebar.expander("CALDERA", expanded=True):
    m_vapor_gen = st.number_input("Flujo Vapor [kg/s]", value=1.472, format="%.3f")
    n_b = st.number_input("Eficiencia Caldera", value=0.96)
    LHV = st.number_input("LHV [kJ/kg]", value=34300.0)
    T_b_in = st.number_input("T Entrada Agua [C]", value=94.0)
    T_b_out = st.number_input("T Salida Vapor [C]", value=162.0)
    P_b_out = st.number_input("Presion Vapor [kPa]", value=550.0)

with st.sidebar.expander("INTERCAMBIADOR (HX)", expanded=True):
    U_ideal_ees = st.number_input("U Ideal de Diseño [kW/m2K]", value=1.472, format="%.3f")
    T_I_steam_IN = st.number_input("T Vapor Entrada HX [C]", value=151.0)
    T_I_water_IN = st.number_input("T Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("T Agua Salida HX [C]", value=86.0)
    P_I_water = st.number_input("Presion Agua Proceso [kPa]", value=80.0)

with st.sidebar.expander("PASTEURIZADOR", expanded=True):
    eficiencia_past = st.number_input("Eficiencia Proceso (0-1)", value=0.95)
    T_botella_IN = st.number_input("T Entrada Botella (E1) [C]", value=4.0)
    T_botella_16_OUT = st.number_input("T Salida E1 / Entrada E2 [C]", value=40.0)
    T_botella_714_OUT = st.number_input("T Salida E2 / Entrada E3 [C]", value=64.0)
    T_botella_1520_OUT = st.number_input("T Salida Final (E3) [C]", value=22.0)
    T_PS_714_OUT = st.number_input("T Salida Agua Zona 7-14 [C]", value=58.2)
    m_vidrio = st.number_input("Masa Vidrio [kg]", value=0.35)
    m_cerveza = st.number_input("Masa Cerveza [kg]", value=1.2)

# --- CALCULOS ---
try:
    # 1. Balances de Caldera
    H_b_in = h_liq(T_b_in, P_b_out)
    H_b_out = h_vap(T_b_out, 1)
    Q_caldera = m_vapor_gen * (H_b_out - H_b_in)
    m_comb = Q_caldera / (n_b * LHV)

    # 2. Intercambiador y Fouling
    m_I_steam_IN = m_vapor_gen * 0.95
    Q_HX_nominal = m_I_steam_IN * (h_vap(T_I_steam_IN, 1) - h_liq(82.0, 500.0))
    m_I_water_total = Q_HX_nominal / (h_liq(T_I_water_OUT, P_I_water) - h_liq(T_I_water_IN, P_I_water))
    
    C_min = m_I_water_total * cp_f(69.0, P_I_water)
    E_ideal = Q_HX_nominal / (C_min * (T_I_steam_IN - T_I_water_IN))
    Area_fisica = (-np.log(1 - E_ideal) * C_min) / U_ideal_ees
    
    R_f_actual = 0.00005 * (1 - np.exp(-0.02 * t_dias))
    U_real_kW = 1 / ((1 / U_ideal_ees) + (R_f_actual * 1000))
    E_real = 1 - np.exp(-(U_real_kW * Area_fisica) / C_min)
    Q_HX_real = E_real * (C_min * (T_I_steam_IN - T_I_water_IN))

    # 3. Balances por Etapa en Pasteurizador
    m_una_botella = m_vidrio + m_cerveza
    cp_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella
    m_I_w_real = Q_HX_real / (h_liq(T_I_water_OUT, P_I_water) - h_liq(T_I_water_IN, P_I_water))

    # Etapa 2 (Zona 7-14) - Base para m_botellas
    m_PS_714 = (m_I_w_real / 14) * 8
    Q_agua_cedido_E2 = m_PS_714 * (h_liq(T_I_water_OUT, P_I_water) - h_liq(T_PS_714_OUT, P_I_water))
    m_botellas_kgs = (Q_agua_cedido_E2 * eficiencia_past) / (cp_prod * (T_botella_714_OUT - T_botella_16_OUT))
    Q_botella_ganado_E2 = m_botellas_kgs * cp_prod * (T_botella_714_OUT - T_botella_16_OUT)

    # Etapa 1 (Pre-calentamiento)
    Q_botella_ganado_E1 = m_botellas_kgs * cp_prod * (T_botella_16_OUT - T_botella_IN)
    Q_agua_cedido_E1 = Q_botella_ganado_E1 / eficiencia_past

    # Etapa 3 (Enfriamiento)
    Q_botella_cedido_E3 = m_botellas_kgs * cp_prod * (T_botella_714_OUT - T_botella_1520_OUT)
    Q_agua_ganado_E3 = Q_botella_cedido_E3 * eficiencia_past

    produccion_dia = (m_botellas_kgs * 3600 * 24) / m_una_botella

    # --- INTERFAZ ---
    st.title("Monitor Tecnico de Planta")
    st.divider()

    c_left, c_right = st.columns([1.8, 1.2])

    with c_left:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama tecnico no detectado.")

        st.subheader("Balances Energeticos por Etapa")
        df_etapas = pd.DataFrame({
            "Etapa del Proceso": ["Etapa 1 (Pre-calentamiento)", "Etapa 2 (Pasteurización)", "Etapa 3 (Enfriamiento)"],
            "Q Agua [kW]": [f"{Q_agua_cedido_E1:.2f} (Cedido)", f"{Q_agua_cedido_E2:.2f} (Cedido)", f"{Q_agua_ganado_E3:.2f} (Ganado)"],
            "Q Botellas [kW]": [f"{Q_botella_ganado_E1:.2f} (Ganado)", f"{Q_botella_ganado_E2:.2f} (Ganado)", f"{Q_botella_cedido_E3:.2f} (Cedido)"]
        })
        st.table(df_etapas)

    with c_right:
        st.subheader("Indicadores de Operacion")
        st.success(f"Produccion Real: {int(produccion_dia):,} Botellas/Dia")
        st.metric("Flujo Masico Combustible", f"{m_comb:.4f} kg/s")
        
        st.divider()
        st.write("Estado del Intercambiador")
        cu1, cu2 = st.columns(2)
        cu1.metric("U Ideal [kW/m2K]", f"{U_ideal_ees:.3f}")
        cu2.metric("U Real [kW/m2K]", f"{U_real_kW:.3f}", delta=f"{U_real_kW - U_ideal_ees:.4f}" if t_dias > 0 else None)

        st.divider()
        st.write(f"Tiempo de operacion: {t_dias} dias")

except Exception as e:
    st.error(f"Error en calculos tecnicos: {e}")
