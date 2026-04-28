import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
from PIL import Image

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Simulador Termico de Pasteurizacion", layout="wide")

# --- FUNCIONES DE PROPIEDADES (LOGICA EES) ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL: INPUTS DETALLADOS ---
st.sidebar.title("Parametros de Ingenieria")

# SECCION 1: CALDERA
with st.sidebar.expander("1. SISTEMA DE CALDERA", expanded=True):
    st.markdown("**Flujos y Eficiencia**")
    m_b_in = st.number_input("Flujo Agua Alimentacion [kg/s]", value=1.472, format="%.3f")
    n_b = st.number_input("Eficiencia de Caldera (0-1)", value=0.96)
    LHV = st.number_input("Poder Calorifico (LHV) [kJ/kg]", value=34300.0)
    
    st.markdown("**Estados Termicos**")
    T_b_in = st.number_input("Temp. Entrada Agua [C]", value=94.0)
    T_b_out = st.number_input("Temp. Salida Vapor [C]", value=162.0)
    P_b_out = st.number_input("Presion de Vapor [kPa]", value=550.0)

# SECCION 2: INTERCAMBIADOR DE CALOR (HX)
with st.sidebar.expander("2. INTERCAMBIADOR DE CALOR", expanded=True):
    st.markdown("**Lado Vapor (Calentamiento)**")
    T_I_steam_IN = st.number_input("Temp. Vapor Entrada HX [C]", value=151.0)
    P_I_steam_IN = st.number_input("Presion Vapor Entrada [kPa]", value=500.0)
    T_I_cond_OUT = st.number_input("Temp. Condensado Salida [C]", value=82.0)
    
    st.markdown("**Lado Agua Proceso (Duchas)**")
    T_I_water_IN = st.number_input("Temp. Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("Temp. Agua Salida HX [C]", value=86.0)
    P_I_water_OUT = st.number_input("Presion Agua Proceso [kPa]", value=80.0)

# SECCION 3: PRODUCTO (BOTELLA + CERVEZA)
with st.sidebar.expander("3. DATOS DEL PRODUCTO", expanded=True):
    m_vidrio = st.number_input("Masa Vidrio (Envase) [kg]", value=0.35)
    cp_vidrio = st.number_input("Cp Vidrio [kJ/kg-K]", value=0.86)
    m_cerveza = st.number_input("Masa Cerveza [kg]", value=1.2)
    cp_cerveza = st.number_input("Cp Cerveza [kJ/kg-K]", value=3.85)

# SECCION 4: ETAPAS DEL PASTEURIZADOR
with st.sidebar.expander("4. TEMPERATURAS DE PROCESO", expanded=False):
    T_botella_IN = st.number_input("Temp. Entrada Etapa 1 [C]", value=4.0)
    T_botella_16_OUT = st.number_input("Temp. Salida Etapa 1 [C]", value=40.0)
    T_botella_714_OUT = st.number_input("Temp. Salida Etapa 2 [C]", value=64.0)
    T_botella_1520_OUT = st.number_input("Temp. Salida Final [C]", value=22.0)

# SECCION 5: DISEÑO (METODO NTU)
with st.sidebar.expander("5. GEOMETRIA DEL HX", expanded=False):
    N_placas = st.number_input("Numero de Placas", value=200)
    b_c = st.number_input("Espesor Canal (b_c) [m]", value=0.004, format="%.4f")
    w_c = st.number_input("Ancho Placa (w_c) [m]", value=0.363, format="%.3f")

# --- CALCULOS ---
try:
    # Caldera
    H_b_in = h_liq(T_b_in, P_b_out)
    H_b_out = h_vap(T_b_out, 1)
    
    # Intercambiador
    m_I_steam_IN = m_b_in * 0.95
    h_s_in = h_vap(T_I_steam_IN, 1)
    h_cond = h_liq(T_I_cond_OUT, P_I_steam_IN)
    
    h_I_water_IN = h_liq(T_I_water_IN, P_I_water_OUT)
    h_I_water_OUT = h_liq(T_I_water_OUT, P_I_water_OUT)
    
    # Masa agua proceso
    m_I_water_OUT = (m_I_steam_IN * (h_s_in - h_cond)) / (h_I_water_OUT - h_I_water_IN)
    Q_HX = m_I_water_OUT * (h_I_water_OUT - h_I_water_IN)

    # Propiedades del producto
    m_total_prod = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * cp_vidrio + m_cerveza * cp_cerveza) / m_total_prod
    
    # Zona 7-14 (Pasteurizacion)
    m_PS_714 = (m_I_water_OUT / 14) * 8
    h_PS_714_out = h_liq(60.0, P_I_water_OUT)
    Q_cedido_714 = m_PS_714 * (h_I_water_OUT - h_PS_714_out)
    m_botellas_kgs = Q_cedido_714 / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))
    
    # Produccion
    produccion_dia = (m_botellas_kgs * 3600 * 24) / m_total_prod

    # --- PANTALLA PRINCIPAL ---
    st.title("Monitor Tecnico de Planta")
    st.markdown(f"Analisis termico basado en CoolProp / IAPWS-IF97")
    st.divider()

    c_img, c_res = st.columns([2, 1])

    with c_img:
        try:
            img = Image.open("diagrama.png")
            st.image(img, use_container_width=True)
        except:
            st.warning("Archivo 'diagrama.png' no encontrado.")
        
        st.subheader("Variables de Control")
        col1, col2, col3 = st.columns(3)
        col1.metric("Agua de Proceso", f"{m_I_water_OUT:.3f} kg/s")
        col2.metric("Calor HX", f"{Q_HX:.1f} kW")
        col3.metric("Masa de Paso", f"{m_botellas_kgs:.2f} kg/s")

    with c_res:
        st.subheader("Produccion")
        st.success(f"{int(produccion_dia):,} Botellas/Dia")
        
        st.divider()
        st.subheader("Detalles de Balance")
        st.write(f"**Cp Producto:** {cp_prom_prod:.3f} kJ/kg-K")
        
        m_comb = (m_b_in * (H_b_out - H_b_in)) / (n_b * LHV)
        st.write(f"**Consumo Combustible:** {m_comb:.4f} kg/s")
        
        # Efectividad NTU
        cp_w_prom = cp_f(69, P_I_water_OUT)
        C_min = m_I_water_OUT * cp_w_prom
        Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
        eff = Q_HX / Q_max
        st.write(f"**Efectividad HX:** {eff*100:.1f}%")

except Exception as e:
    st.error(f"Error en los calculos: {e}")
