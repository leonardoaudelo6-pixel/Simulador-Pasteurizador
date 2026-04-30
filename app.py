import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
from PIL import Image

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Simulador Tecnico v4.1", layout="wide")

# --- FUNCIONES DE PROPIEDADES ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL: INPUTS ---
st.sidebar.title("Parametros de Ingenieria")

# 1. UNICO INPUT DE MANTENIMIENTO
with st.sidebar.expander("1. MANTENIMIENTO", expanded=True):
    t_dias = st.number_input("Dias sin limpiar", value=0, min_value=0)

# RESTO DE INPUTS (CALDERA, HX, PRODUCTO)
with st.sidebar.expander("2. CALDERA", expanded=False):
    m_b_in = st.number_input("Flujo Alimentacion [kg/s]", value=1.472, format="%.3f")
    n_b = st.number_input("Eficiencia Caldera", value=0.96)
    LHV = st.number_input("LHV [kJ/kg]", value=34300.0)
    T_b_in = st.number_input("T Entrada Caldera [C]", value=94.0)
    T_b_out = st.number_input("T Salida Vapor [C]", value=162.0)
    P_b_out = st.number_input("P Vapor [kPa]", value=550.0)

with st.sidebar.expander("3. INTERCAMBIADOR (HX)", expanded=True):
    N_placas = st.number_input("Numero de Placas", value=200.0)
    T_I_steam_IN = st.number_input("T Vapor Entrada HX [C]", value=151.0)
    T_I_water_IN = st.number_input("T Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("T Agua Salida HX [C]", value=86.0)

with st.sidebar.expander("4. PRODUCTO Y PROCESO", expanded=False):
    eficiencia_past = st.number_input("Eficiencia Pasteurizador", value=0.95)
    m_vidrio = st.number_input("Masa Vidrio [kg]", value=0.35)
    m_cerveza = st.number_input("Masa Cerveza [kg]", value=1.2)
    T_botella_714_OUT = st.number_input("T Salida Etapa 2 [C]", value=64.0)
    T_botella_16_OUT = st.number_input("T Salida Etapa 1 [C]", value=40.0)

# --- CALCULOS (LOGICA ASINTOTICA) ---
try:
    # Parametros fijos de ensuciamiento (internos)
    R_f_max = 0.0005
    beta_f = 0.06
    U_ideal = 2850.0 # W/m2-K

    # Balances Ideales
    H_b_in, H_b_out = h_liq(T_b_in, P_b_out), h_vap(T_b_out, 1)
    Q_b_water = m_b_in * (H_b_out - H_b_in)
    m_comb = Q_b_water / (n_b * LHV)

    m_I_steam_IN = m_b_in * 0.95
    h_s_in, h_cond = h_vap(T_I_steam_IN, 1), h_liq(82.0, 500.0)
    Q_HX_ideal = m_I_steam_IN * (h_s_in - h_cond)
    
    m_I_water_ideal = Q_HX_ideal / (h_liq(T_I_water_OUT, 80.0) - h_liq(T_I_water_IN, 80.0))
    cp_w = cp_f(69.0, 80.0)
    C_min = m_I_water_ideal * cp_w
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    E_ideal = Q_HX_ideal / Q_max
    NTU_ideal = -np.log(1 - E_ideal)
    Area_fisica = (NTU_ideal * C_min) / (U_ideal / 1000)

    # Calculo Real (Ensuciamiento)
    R_f = R_f_max * (1 - np.exp(-beta_f * t_dias))
    U_real = 1 / ((1 / U_ideal) + R_f)
    NTU_real = (U_real / 1000 * Area_fisica) / C_min
    E_real = 1 - np.exp(-NTU_real)
    Q_HX_real = E_real * Q_max

    # Produccion Real
    m_una_botella = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella
    m_I_water_real = Q_HX_real / (h_liq(T_I_water_OUT, 80.0) - h_liq(T_I_water_IN, 80.0))
    m_PS_714 = (m_I_water_real / 14) * 8
    Q_PS_cedido_714_real = m_PS_714 * (h_liq(T_I_water_OUT, 80.0) - h_liq(58.2, 80.0))
    m_botellas_real = (Q_PS_cedido_714_real * eficiencia_past) / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))
    produccion_dia = (m_botellas_real * 3600 * 24) / m_una_botella

    # --- PANTALLA PRINCIPAL ---
    st.title("Resultados de Operacion y Mantenimiento")
    st.divider()

    col_info, col_res = st.columns([1.5, 1])

    with col_info:
        st.subheader("Balances de Energia [kW]")
        st.table({
            "Componente": ["Caldera (Combustible)", "Intercambiador (Vapor)", "Intercambiador (Agua)", "Pasteurizador (Cedido)"],
            "Valor Real": [f"{m_comb*LHV:.2f}", f"{Q_HX_real:.2f}", f"{Q_HX_real:.2f}", f"{Q_PS_cedido_714_real:.2f}"]
        })
        
        st.subheader("Analisis de Eficiencia y Ensuciamiento")
        st.table({
            "Parametro": ["U (Coef. Global) [W/m2-K]", "E (Efectividad) [%]"],
            "Ideal (Dia 0)": [f"{U_ideal:.1f}", f"{E_ideal*100:.2f}%"],
            "Real (Actual)": [f"{U_real:.1f}", f"{E_real*100:.2f}%"]
        })

    with col_res:
        st.subheader("Produccion Real")
        st.metric("Botellas por Dia", f"{int(produccion_dia):,}")
        st.metric("Masa Pasteurizada", f"{m_botellas_real:.3f} kg/s")
        
        st.divider()
        st.subheader("Indicadores de Diseno")
        st.write(f"**U Ideal:** {U_ideal} W/m2-K")
        st.write(f"**U Real:** {U_real:.2f} W/m2-K")
        st.write(f"**Efectividad Ideal:** {E_ideal*100:.2f}%")
        st.write(f"**Efectividad Real:** {E_real*100:.2f}%")

except Exception as e:
    st.error(f"Error en calculos: {e}")
