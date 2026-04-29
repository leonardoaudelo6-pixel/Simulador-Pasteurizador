import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
from PIL import Image

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Simulador Tecnico de Pasteurizacion", layout="wide")

# --- FUNCIONES DE PROPIEDADES ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL: INPUTS ---
st.sidebar.title("Parametros de Ingenieria")

with st.sidebar.expander("1. CALDERA", expanded=True):
    m_vapor_gen = st.sidebar.number_input("Flujo Vapor Generado [kg/s]", value=1.472, format="%.3f")
    n_b = st.sidebar.number_input("Eficiencia Caldera (0-1)", value=0.96)
    LHV = st.sidebar.number_input("LHV Combustible [kJ/kg]", value=34300.0)
    T_b_in = st.sidebar.number_input("Temp. Entrada Agua Caldera [C]", value=94.0)
    T_b_out = st.sidebar.number_input("Temp. Salida Vapor Caldera [C]", value=162.0)
    P_b_out = st.sidebar.number_input("Presion Vapor [kPa]", value=550.0)

with st.sidebar.expander("2. INTERCAMBIADOR (HX)", expanded=True):
    U_manual = st.sidebar.number_input("Coeficiente Global U [W/m2-K]", value=1500.0)
    N_placas = st.sidebar.number_input("Numero de Placas", value=200.0)
    T_I_steam_IN = st.sidebar.number_input("Temp. Vapor Entrada HX [C]", value=151.0)
    P_I_steam_IN = st.sidebar.number_input("Presion Vapor Entrada HX [kPa]", value=500.0)
    T_I_water_IN = st.sidebar.number_input("Temp. Agua Fria Entrada [C]", value=52.0)
    T_I_water_OUT = st.sidebar.number_input("Temp. Agua Caliente Salida [C]", value=86.0)
    P_I_water_OUT = st.sidebar.number_input("Presion Agua Proceso [kPa]", value=80.0)

with st.sidebar.expander("3. PRODUCTO Y PROCESO", expanded=True):
    m_vidrio = st.sidebar.number_input("Masa Vidrio [kg]", value=0.35)
    m_cerveza = st.sidebar.number_input("Masa Cerveza [kg]", value=1.2)
    T_botella_IN = st.sidebar.number_input("Temp. Inicial Producto [C]", value=4.0)
    T_botella_16_OUT = st.sidebar.number_input("Temp. Salida Etapa 1 [C]", value=40.0)
    T_botella_714_OUT = st.sidebar.number_input("Temp. Salida Etapa 2 [C]", value=64.0)
    T_botella_1520_OUT = st.sidebar.number_input("Temp. Salida Final [C]", value=22.0)

# --- CALCULOS ---
try:
    # 1. Caldera
    H_b_in = h_liq(T_b_in, P_b_out)
    H_b_out = h_vap(T_b_out, 1)
    Q_caldera = m_vapor_gen * (H_b_out - H_b_in)
    m_comb = Q_caldera / (n_b * LHV)

    # 2. Intercambiador
    m_I_steam_IN = m_vapor_gen * 0.95
    h_s_in = h_vap(T_I_steam_IN, 1)
    h_cond = h_liq(82.0, P_I_steam_IN)
    Q_cedido_HX = m_I_steam_IN * (h_s_in - h_cond)
    
    h_I_w_in = h_liq(T_I_water_IN, P_I_water_OUT)
    h_I_w_out = h_liq(T_I_water_OUT, P_I_water_OUT)
    m_I_water_OUT = Q_cedido_HX / (h_I_w_out - h_I_w_in)
    Q_ganado_HX = m_I_water_OUT * (h_I_w_out - h_I_w_in)

    # 3. Pasteurizador
    m_una_botella = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella

    m_PS_714 = (m_I_water_OUT / 14) * 8
    h_PS_714_out = h_liq(59.0, P_I_water_OUT)
    Q_PS_cedido_714 = m_PS_714 * (h_I_w_out - h_PS_714_out)
    m_botellas_kgs = Q_PS_cedido_714 / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))

    m_PS_1520 = (m_I_water_OUT / 14) * 6
    m_PS_16_1520 = (m_PS_1520 * (h_I_w_out - h_liq(48.0, P_I_water_OUT))) / (h_liq(48.0, P_I_water_OUT) - h_liq(36.0, P_I_water_OUT))
    
    produccion_dia = (m_botellas_kgs * 3600 * 24) / m_una_botella

    # --- VISUALIZACION ---
    st.title("Monitor Tecnico de Pasteurizacion v2.1")
    st.divider()

    col_m, col_s = st.columns([2, 1])

    with col_m:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado.")

        st.subheader("Resumen de Flujos Masicos")
        tabla_f = {
            "Corriente": ["Combustible", "Vapor de Agua (Gen)", "Vapor HX", "Agua Proceso (Total)", "Masa Producto", "Agua Mezcla E3"],
            "Valor [kg/s]": [f"{m_comb:.4f}", f"{m_vapor_gen:.4f}", f"{m_I_steam_IN:.4f}", f"{m_I_water_OUT:.4f}", f"{m_botellas_kgs:.4f}", f"{m_PS_16_1520:.4f}"]
        }
        st.table(tabla_f)

        st.subheader("Monitoreo de Temperaturas")
        tabla_t = {
            "Punto de Medicion": ["Entrada Caldera", "Salida Vapor Caldera", "Agua Proceso Entrada HX", "Agua Proceso Salida HX", "Producto Entrada (E1)", "Producto Salida Final"],
            "Temperatura [C]": [f"{T_b_in:.1f}", f"{T_b_out:.1f}", f"{T_I_water_IN:.1f}", f"{T_I_water_OUT:.1f}", f"{T_botella_IN:.1f}", f"{T_botella_1520_OUT:.1f}"]
        }
        st.table(tabla_t)

    # AQUÍ ESTABA EL ERROR, YA ESTÁ CORREGIDO A 'with col_s:'
    with col_s:
        st.subheader("Resultados Principales")
        st.metric("Produccion Total", f"{int(produccion_dia):,} Botellas/Dia")
        
        cp_w_hx = cp_f((T_I_water_IN + T_I_water_OUT)/2, P_I_water_OUT)
        eff_hx = Q_ganado_HX / (m_I_water_OUT * cp_w_hx * (T_I_steam_IN - T_I_water_IN))
        st.metric("Eficiencia HX", f"{eff_hx*100:.2f} %")
        st.metric("Presion Proceso", f"{P_I_water_OUT} kPa")
        
        st.divider()
        st.write(f"**U Seleccionada:** {U_manual} W/m2-K")
        st.write(f"**Numero de Placas:** {int(N_placas)}")
        st.write(f"**Flujo Combustible:** {m_comb:.4f} kg/s")

except Exception as e:
    st.error(f"Error en calculos: {e}")
