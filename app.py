import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Simulador Térmico Pasteurizador", layout="wide")

# --- FUNCIONES TERMODINÁMICAS ---
def h_agua(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vapor(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_agua(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL (INPUTS DETALLADOS) ---
st.sidebar.title("🎮 Panel de Control Técnico")

# SECCIÓN 1: CALDERA
with st.sidebar.expander("🔥 1. SISTEMA DE CALDERA (Vapor)", expanded=True):
    T_b_in = st.number_input("Temp. Entrada Agua Alimentación [C]", value=94.0, help="Agua líquida que entra a la caldera.")
    T_b_out = st.number_input("Temp. Salida Vapor Generado [C]", value=162.0, help="Vapor que sale hacia la planta.")
    P_b_out = st.number_input("Presión de Operación [kPa]", value=550.0)
    m_b_in = st.number_input("Flujo de Alimentación [kg/s]", value=1.472)
    n_b = st.number_input("Eficiencia Térmica (0.0 - 1.0)", value=0.96)
    LHV = st.number_input("Poder Calorífico Combustible [kJ/kg]", value=34300.0)

# SECCIÓN 2: INTERCAMBIADOR DE PLACAS
with st.sidebar.expander("⚙️ 2. INTERCAMBIADOR (Transferencia)", expanded=True):
    st.markdown("**Lado Vapor (Calentamiento)**")
    T_I_steam_IN = st.number_input("Temp. Vapor Entrada HX [C]", value=151.0)
    P_I_steam_IN = st.number_input("Presión Vapor Entrada HX [kPa]", value=500.0)
    T_I_cond_OUT = st.number_input("Temp. Condensado Salida [C]", value=82.0)
    
    st.markdown("**Lado Agua de Proceso (Calentamiento)**")
    T_I_water_IN = st.number_input("Temp. Agua Fría Entrada [C]", value=52.0)
    T_I_water_OUT = st.number_input("Temp. Agua Caliente Salida [C]", value=86.0)
    P_I_water_OUT = st.number_input("Presión Agua Proceso [kPa]", value=80.0)

# SECCIÓN 3: GEOMETRÍA DEL INTERCAMBIADOR (MÉTODO NTU)
with st.sidebar.expander("📐 3. GEOMETRÍA Y DISEÑO HX", expanded=False):
    N_placas = st.number_input("Número Total de Placas", value=200)
    b_c = st.number_input("Espesor de Canal (b_c) [m]", value=0.004, format="%.4f")
    w_c = st.number_input("Ancho de Placa (w_c) [m]", value=0.363, format="%.3f")
    miu = st.number_input("Viscosidad Dinámica [Pa-s]", value=4.04e-7, format="%.2e")
    k_w = st.number_input("Conductividad Térmica [W/m-K]", value=0.663)

# SECCIÓN 4: PRODUCTO Y PASTEURIZACIÓN
with st.sidebar.expander("🍺 4. PARÁMETROS DEL PRODUCTO", expanded=True):
    m_vidrio = st.number_input("Masa Botella Vacía [kg]", value=0.35)
    m_cerveza = st.number_input("Masa Líquido (Cerveza) [kg]", value=1.2)
    T_botella_IN = st.number_input("Temp. Inicial Producto [C]", value=4.0)
    T_botella_16_OUT = st.number_input("Temp. Salida Etapa 1 [C]", value=40.0)
    T_botella_714_OUT = st.number_input("Temp. Salida Etapa 2 [C]", value=64.0)
    T_botella_1520_OUT = st.number_input("Temp. Salida Final [C]", value=22.0)

# --- CÁLCULOS ---
try:
    # Propiedades
    H_b_in = h_agua(T_b_in, P_b_out)
    H_b_out = h_vapor(T_b_out, 1.0)
    
    # Intercambiador
    m_I_steam_IN = m_b_in * 0.95
    h_s_in = h_vapor(T_I_steam_IN, 1.0)
    h_cond = h_agua(T_I_cond_OUT, P_I_steam_IN)
    
    h_I_water_IN = h_agua(T_I_water_IN, P_I_water_OUT)
    h_I_water_OUT = h_agua(T_I_water_OUT, P_I_water_OUT)
    
    # Balance de energía en HX
    # m_steam * (h_in - h_out) = m_water * (h_out - h_in)
    m_I_water_OUT = (m_I_steam_IN * (h_s_in - h_cond)) / (h_I_water_OUT - h_I_water_IN)
    Q_intercambiador = m_I_water_OUT * (h_I_water_OUT - h_I_water_IN)

    # Producto
    m_una_botella = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella
    
    # Masa de botellas basada en Etapa 2 (Zona 7-14)
    m_PS_714 = (m_I_water_OUT / 14) * 8
    h_PS_714_out = h_agua(60.0, P_I_water_OUT)
    Q_PS_cedido_714 = m_PS_714 * (h_I_water_OUT - h_PS_714_out)
    m_botellas_kgs = Q_PS_cedido_714 / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))
    
    produccion_dia = (m_botellas_kgs * 3600 * 24) / m_una_botella

    # --- DISEÑO ---
    st.title("🛡️ Sistema de Monitoreo Térmico: Pasteurización Batch")
    st.markdown(f"**Ingeniero a cargo:** Armangoat / Leo")
    st.divider()

    c_img, c_stats = st.columns([2, 1])

    with c_img:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado. Súbelo como 'diagrama.png'")
        
        st.subheader("📡 Datos en Tiempo Real")
        m1, m2, m3 = st.columns(3)
        m1.metric("Flujo Agua de Proceso", f"{m_I_water_OUT:.3f} kg/s")
        m2.metric("Q Intercambiador", f"{Q_intercambiador:.2f} kW")
        m3.metric("Flujo Vapor HX", f"{m_I_steam_IN:.3f} kg/s")

    with c_stats:
        st.subheader("📦 Producción Estimada")
        st.success(f"**{int(produccion_dia):,}** Botellas / 24h")
        
        st.divider()
        st.subheader("🔬 Análisis de Ingeniería")
        st.write(f"**Cp Promedio Producto:** {cp_prom_prod:.3f} kJ/kg-K")
        st.write(f"**Masa de Producción:** {m_botellas_kgs:.2f} kg/s")
        
        # Cálculo de combustible aproximado
        m_comb = (m_b_in * (H_b_out - H_b_in)) / (n_b * LHV)
        st.write(f"**Consumo Combustible:** {m_comb:.4f} kg/s")

    st.divider()
    st.subheader("📝 Resumen de Operación por Zona")
    st.table({
        "Zona": ["1-6 (Pre-cal)", "7-14 (Pasteur)", "15-20 (Pre-enf)"],
        "Estado": ["Calentando", "Sostenimiento", "Enfriamiento"],
        "Temp. Objetivo [C]": [T_botella_16_OUT, T_botella_714_OUT, T_botella_1520_OUT]
    })

except Exception as e:
    st.error(f"Error en el balance: {e}")
