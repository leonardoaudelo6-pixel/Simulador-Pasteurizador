import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
import pandas as pd

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Analisis Termico Pro", layout="wide")

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
    T_I_steam_IN = st.number_input("T Vapor Entrada [C]", value=151.0)
    T_I_water_IN = st.number_input("T Agua Entrada [C]", value=52.0)
    T_I_water_OUT = st.number_input("T Agua Salida [C]", value=86.0)
    P_I_water = st.number_input("Presion Agua Proceso [kPa]", value=80.0)

with st.sidebar.expander("PASTEURIZADOR", expanded=False):
    eficiencia_past = st.number_input("Eficiencia Proceso", value=0.95)
    T_botella_714_OUT = st.number_input("T Salida Etapa 2 [C]", value=64.0)
    T_botella_16_OUT = st.number_input("T Salida Etapa 1 [C]", value=40.0)

# --- CALCULOS ---
try:
    # 1. Caldera y Combustible
    H_b_in, H_b_out = h_liq(T_b_in, P_b_out), h_vap(T_b_out, 1)
    Q_caldera = m_vapor_gen * (H_b_out - H_b_in)
    m_comb = Q_caldera / (n_b * LHV)

    # 2. HX e Idealidad
    m_I_steam_IN = m_vapor_gen * 0.95
    h_s_in, h_cond = h_vap(T_I_steam_IN, 1), h_liq(82.0, 500.0)
    Q_HX_nominal = m_I_steam_IN * (h_s_in - h_cond)
    
    h_I_w_in, h_I_w_out = h_liq(T_I_water_IN, P_I_water), h_liq(T_I_water_OUT, P_I_water)
    m_I_water = Q_HX_nominal / (h_I_w_out - h_I_w_in)
    
    C_min = m_I_water * cp_f(69.0, P_I_water)
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    
    # 3. Ensuciamiento y U en kW/m2K
    U_ideal_kW = 2.85 
    Area_fisica = (-np.log(1 - (Q_HX_nominal/Q_max)) * C_min) / U_ideal_kW
    R_f_actual = (0.0005 * (1 - np.exp(-0.06 * t_dias)))
    U_real_kW = 1 / ((1 / U_ideal_kW) + (R_f_actual * 1000))
    
    # Recalculo de Eficiencia Real
    NTU_real = (U_real_kW * Area_fisica) / C_min
    E_real = 1 - np.exp(-NTU_real)
    Q_HX_real = E_real * Q_max

    # 4. Produccion
    m_una_botella = 1.55 
    cp_prod = (0.35 * 0.86 + 1.2 * 3.85) / 1.55
    Q_util = ( (Q_HX_real/14)*8 ) * (h_I_w_out - h_liq(58.2, P_I_water)) * eficiencia_past
    m_botellas = Q_util / (cp_prod * (T_botella_714_OUT - T_botella_16_OUT))
    produccion_dia = (m_botellas * 3600 * 24) / m_una_botella

    # --- INTERFAZ ---
    st.title("Monitor Tecnico de Planta: Eficiencia y Calor")
    st.divider()

    c_left, c_right = st.columns([1.5, 1])

    with c_left:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado.")

        st.subheader("Balances de Calor del Sistema")
        # Tabla de Balances clara
        df_balances = pd.DataFrame({
            "Sistema": ["Caldera", "Intercambiador", "Pasteurizador"],
            "Fuente Energia": ["Combustible", "Vapor de Agua", "Agua de Proceso"],
            "Calor Cedido [kW]": [f"{m_comb*LHV:.2f}", f"{Q_HX_real:.2f}", f"{Q_HX_real*0.95:.2f}"],
            "Calor Ganado [kW]": [f"{Q_caldera:.2f}", f"{Q_HX_real:.2f}", f"{Q_util:.2f}"]
        })
        st.table(df_balances)

    with c_right:
        st.subheader("Metricas de Operacion")
        st.metric("Produccion Real", f"{int(produccion_dia):,} Bot/Dia")
        st.metric("Flujo Combustible", f"{m_comb:.4f} kg/s")
        
        st.write("**Coeficiente Global U [kW/(m2·K)]**")
        cu1, cu2 = st.columns(2)
        cu1.metric("U Ideal", f"{U_ideal_kW:.3f}")
        cu2.metric("U Real", f"{U_real_kW:.3f}", delta=f"{U_real_kW - U_ideal_kW:.3f}")

        # GRAFICO DE SENSIBILIDAD CORREGIDO
        st.subheader("Sensibilidad: Eficiencia vs T_vapor")
        t_range = np.linspace(T_I_water_OUT + 2, T_I_steam_IN + 20, 50)
        q_max_range = C_min * (t_range - T_I_water_IN)
        e_range = Q_HX_real / q_max_range
        
        chart_data = pd.DataFrame({
            "Temperatura Vapor [C]": t_range,
            "Efectividad": e_range
        }).set_index("Temperatura Vapor [C]")
        
        st.line_chart(chart_data)
        st.info(f"Punto actual: {T_I_steam_IN} C | E: {E_real*100:.1f}%")

except Exception as e:
    st.error(f"Error en calculos: {e}")
