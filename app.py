import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
import pandas as pd
from PIL import Image

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Monitor Tecnico de Pasteurizacion Pro", layout="wide")

# --- FUNCIONES DE PROPIEDADES ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL ---
st.sidebar.title("Parametros de Ingenieria")

with st.sidebar.expander("1. MANTENIMIENTO", expanded=True):
    t_dias = st.number_input("Dias sin limpiar", value=0, min_value=0)

with st.sidebar.expander("2. CALDERA", expanded=False):
    m_b_in = st.number_input("Flujo Alimentacion [kg/s]", value=1.472, format="%.3f")
    n_b = st.number_input("Eficiencia Caldera", value=0.96)
    LHV = st.number_input("LHV [kJ/kg]", value=34300.0)
    T_b_in, T_b_out, P_b_out = 94.0, 162.0, 550.0

with st.sidebar.expander("3. INTERCAMBIADOR (HX)", expanded=True):
    N_placas = st.number_input("Numero de Placas", value=200.0)
    T_I_steam_IN = st.number_input("T Vapor Entrada HX [C]", value=151.0)
    T_I_water_IN = st.number_input("T Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("T Agua Salida HX [C]", value=86.0)

# --- CALCULOS ---
try:
    R_f_max, beta_f, U_ideal = 0.0005, 0.06, 2850.0
    
    # Balances
    H_b_in, H_b_out = h_liq(T_b_in, P_b_out), h_vap(T_b_out, 1)
    Q_b_water = m_b_in * (H_b_out - H_b_in)
    m_comb = Q_b_water / (n_b * LHV)

    # HX Ideal
    m_I_steam_IN = m_b_in * 0.95
    h_s_in, h_cond = h_vap(T_I_steam_IN, 1), h_liq(82.0, 500.0)
    Q_HX_ideal = m_I_steam_IN * (h_s_in - h_cond)
    m_I_w_ideal = Q_HX_ideal / (h_liq(T_I_water_OUT, 80.0) - h_liq(T_I_water_IN, 80.0))
    C_min = m_I_w_ideal * cp_f(69.0, 80.0)
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    E_ideal = Q_HX_ideal / Q_max
    Area_fisica = (-np.log(1 - E_ideal) * C_min) / (U_ideal / 1000)

    # Calculo Real Dinamico
    R_f = R_f_max * (1 - np.exp(-beta_f * t_dias))
    U_real = 1 / ((1 / U_ideal) + R_f)
    E_real = 1 - np.exp(-(U_real / 1000 * Area_fisica) / C_min)
    Q_HX_real = E_real * Q_max

    # Produccion
    m_una_botella = 0.35 + 1.2
    cp_prom_prod = (0.35 * 0.86 + 1.2 * 3.85) / m_una_botella
    m_botellas_real = ( ( (Q_HX_real/14)*8 ) * (h_liq(T_I_water_OUT, 80.0) - h_liq(58.2, 80.0)) * 0.95 ) / (cp_prom_prod * (64.0 - 40.0))
    produccion_dia = (m_botellas_real * 3600 * 24) / m_una_botella

    # --- UI ---
    st.title("Sistema Inteligente de Monitoreo Termico")
    st.divider()

    c_img, c_res = st.columns([1.8, 1.2])

    with c_img:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado.")
        
        # TABLA DE CALORES
        st.subheader("Balances Energeticos Reales")
        st.table({
            "Componente": ["Consumo Combustible", "Transferencia Vapor-Agua", "Calor Util en Pasteurizado"],
            "Calor [kW]": [f"{m_comb*LHV:.2f}", f"{Q_HX_real:.2f}", f"{Q_HX_real*0.95:.2f}"]
        })

        # --- MEJORA TOP: GRAFICO DE DEGRADACION ---
        st.subheader("Proyeccion de Degradacion por Ensuciamiento")
        dias_plot = np.arange(0, 61, 1)
        u_plot = 1 / ((1 / U_ideal) + (R_f_max * (1 - np.exp(-beta_f * dias_plot))))
        df_plot = pd.DataFrame({"Dias": dias_plot, "U Real": u_plot})
        st.line_chart(df_plot.set_index("Dias"))

    with c_res:
        st.subheader("Estado de Produccion")
        st.metric("Produccion Real", f"{int(produccion_dia):,} Bot/Dia")
        st.metric("Flujo Combustible", f"{m_comb:.4f} kg/s")
        
        # COMPARATIVAS
        st.divider()
        col_u1, col_u2 = st.columns(2)
        col_u1.metric("U Ideal", f"{U_ideal:.0f}")
        col_u2.metric("U Real", f"{U_real:.1f}", delta=f"{U_real - U_ideal:.1f}")

        col_e1, col_e2 = st.columns(2)
        col_e1.metric("Efectividad Ideal", f"{E_ideal*100:.1f}%")
        col_e2.metric("Efectividad Real", f"{E_real*100:.1f}%", delta=f"{(E_real - E_ideal)*100:.1f}%")

        # --- MEJORA TOP: ANALISIS PREDICTIVO ---
        st.divider()
        st.subheader("Prediccion de Mantenimiento")
        limite_u = U_ideal * 0.85
        dias_restantes = ( -np.log(1 - ( (1/limite_u - 1/U_ideal) / R_f_max )) / beta_f ) if t_dias < 15 else 0
        
        if U_real > limite_u:
            st.success(f"Sistema saludable. Rendimiento por encima del 85%.")
        else:
            st.warning(f"Se recomienda limpieza inmediata. Perdida de eficiencia critica.")
        
        st.info(f"Flujo Agua Proceso: {m_I_w_ideal * (Q_HX_real/Q_HX_ideal):.4f} kg/s")

except Exception as e:
    st.error(f"Error en calculos: {e}")
