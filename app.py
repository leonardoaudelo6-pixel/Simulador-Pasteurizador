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

# --- BARRA LATERAL: INPUTS TOTALES ---
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
    # CORRECCION: U Ideal ahora es 1.472 conforme a tu EES
    U_ideal_ees = st.number_input("U Ideal de Diseño [kW/m2K]", value=1.472, format="%.3f")
    T_I_steam_IN = st.number_input("T Vapor Entrada HX [C]", value=151.0)
    T_I_water_IN = st.number_input("T Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("T Agua Salida HX [C]", value=86.0)
    P_I_water = st.number_input("Presion Agua Proceso [kPa]", value=80.0)

with st.sidebar.expander("PASTEURIZADOR", expanded=True):
    eficiencia_past = st.number_input("Eficiencia Proceso (0-1)", value=0.95)
    T_PS_714_OUT = st.number_input("T Salida Agua Zona 7-14 [C]", value=58.2)
    T_botella_16_OUT = st.number_input("T Salida Etapa 1 [C]", value=40.0)
    T_botella_714_OUT = st.number_input("T Salida Etapa 2 [C]", value=64.0)
    m_vidrio = st.number_input("Masa Vidrio [kg]", value=0.35)
    m_cerveza = st.number_input("Masa Cerveza [kg]", value=1.2)

# --- CALCULOS ---
try:
    # 1. Balances de Caldera
    H_b_in = h_liq(T_b_in, P_b_out)
    H_b_out = h_vap(T_b_out, 1)
    Q_caldera_ganado = m_vapor_gen * (H_b_out - H_b_in)
    m_comb = Q_caldera_ganado / (n_b * LHV)

    # 2. Balances Intercambiador
    m_I_steam_IN = m_vapor_gen * 0.95
    h_s_in = h_vap(T_I_steam_IN, 1)
    h_cond = h_liq(82.0, 500.0)
    Q_HX_nominal = m_I_steam_IN * (h_s_in - h_cond)
    
    h_I_w_in = h_liq(T_I_water_IN, P_I_water)
    h_I_w_out = h_liq(T_I_water_OUT, P_I_water)
    m_I_water_total = Q_HX_nominal / (h_I_w_out - h_I_w_in)
    
    # NTU y Area fisica usando tu U_ideal de 1.472
    C_min = m_I_water_total * cp_f(69.0, P_I_water)
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    E_ideal = Q_HX_nominal / Q_max
    Area_fisica = (-np.log(1 - E_ideal) * C_min) / U_ideal_ees
    
    # Fouling realista
    R_f_max = 0.00005 
    beta_f = 0.02
    R_f_actual = R_f_max * (1 - np.exp(-beta_f * t_dias))
    
    # U real corregida
    U_real_kW = 1 / ((1 / U_ideal_ees) + (R_f_actual * 1000))
    NTU_real = (U_real_kW * Area_fisica) / C_min
    E_real = 1 - np.exp(-NTU_real)
    Q_HX_real = E_real * Q_max

    # 3. Produccion (Ideal vs Real)
    m_una_botella = m_vidrio + m_cerveza
    cp_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella
    h_PS_salida_agua = h_liq(T_PS_714_OUT, P_I_water)
    
    # Produccion Ideal
    m_PS_714_ideal = (m_I_water_total / 14) * 8
    Q_PS_cedido_ideal = m_PS_714_ideal * (h_I_w_out - h_PS_salida_agua)
    m_bot_kgs_ideal = (Q_PS_cedido_ideal * eficiencia_past) / (cp_prod * (T_botella_714_OUT - T_botella_16_OUT))
    prod_dia_ideal = (m_bot_kgs_ideal * 3600 * 24) / m_una_botella

    # Produccion Real
    m_I_water_real = Q_HX_real / (h_I_w_out - h_I_w_in)
    m_PS_714_real = (m_I_water_real / 14) * 8
    Q_PS_cedido_real = m_PS_714_real * (h_I_w_out - h_PS_salida_agua)
    m_bot_kgs_real = (Q_PS_cedido_real * eficiencia_past) / (cp_prod * (T_botella_714_OUT - T_botella_16_OUT))
    prod_dia_real = (m_bot_kgs_real * 3600 * 24) / m_una_botella

    # --- INTERFAZ ---
    st.title("Monitor Tecnico de Planta")
    st.divider()

    c_left, c_right = st.columns([1.8, 1.2])

    with c_left:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama tecnico no detectado.")

        st.subheader("Balances de Energia")
        df_balances = pd.DataFrame({
            "Sistema": ["Caldera", "Intercambiador", "Pasteurizador"],
            "Calor Cedido [kW]": [f"{m_comb*LHV:.2f}", f"{Q_HX_real:.2f}", f"{Q_PS_cedido_real:.2f}"],
            "Calor Aprovechado [kW]": [f"{Q_caldera_ganado:.2f}", f"{Q_HX_real:.2f}", f"{Q_PS_cedido_real*eficiencia_past:.2f}"]
        })
        st.table(df_balances)

    with c_right:
        st.subheader("Metricas de Operacion")
        st.success(f"Produccion Real: {int(prod_dia_real):,} Botellas/Dia")
        st.info(f"Produccion Ideal: {int(prod_dia_ideal):,} Botellas/Dia")
        st.metric("Flujo Masico Combustible", f"{m_comb:.4f} kg/s")
        
        st.divider()
        st.write("Eficiencia del Intercambiador")
        cu1, cu2 = st.columns(2)
        cu1.metric("U Ideal [kW/m2K]", f"{U_ideal_ees:.3f}")
        cu2.metric("U Real [kW/m2K]", f"{U_real_kW:.3f}", delta=f"{U_real_kW - U_ideal_ees:.4f}" if t_dias > 0 else None)

        ce1, ce2 = st.columns(2)
        ce1.metric("Efectividad Ideal", f"{E_ideal*100:.1f}%")
        ce2.metric("Efectividad Real", f"{E_real*100:.1f}%", delta=f"{(E_real - E_ideal)*100:.1f}%" if t_dias > 0 else None)

        st.divider()
        st.write(f"Tiempo de operacion: {t_dias} dias")

except Exception as e:
    st.error(f"Error en calculos tecnicos: {e}")
