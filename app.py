import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Simulador Pasteurizador", layout="wide")

# --- FUNCIONES DE APOYO (TRADUCCIÓN EES -> PYTHON) ---
def h_water(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_steam(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_water(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- INTERFAZ DE USUARIO (SIDEBAR) ---
st.sidebar.header("🛠️ Parámetros de Entrada")

# Caldera
T_b_in = st.sidebar.slider("Temp. Entrada Caldera [C]", 50, 100, 94)
T_b_out = st.sidebar.slider("Temp. Salida Vapor [C]", 140, 180, 162)
m_b_in = st.sidebar.number_input("Flujo Agua Entrada [kg/s]", value=1.472)
n_b = 0.96

# Producto
m_vidrio = 0.35
m_cerveza = 1.2
cp_vidrio = 0.86
cp_cerveza = 3.85
m_una_botella = m_vidrio + m_cerveza
cp_prom_prod = (m_vidrio * cp_vidrio + m_cerveza * cp_cerveza) / m_una_botella

# --- CÁLCULOS TRAS CORTINAS ---
try:
    # 1. Caldera
    h_b_in = h_water(T_b_in, 550)
    h_b_out = h_steam(T_b_out, 1)
    # Q_boiler = m_b_in * (h_b_out - h_b_in) / n_b (Si necesitaras calcular combustible)

    # 2. Intercambiador
    m_i_steam_in = m_b_in * 0.95
    h_s_in = h_steam(151, 1)
    h_cond = h_water(82, 500)
    
    h_i_w_in = h_water(52, 80)
    h_i_w_out = h_water(86, 80)
    
    # Despeje de m_I_water_OUT de tu balance: m_w * dh_w = m_s * dh_s
    m_i_water_out = (m_i_steam_in * (h_s_in - h_cond)) / (h_i_w_out - h_i_w_in)
    q_intercambiador = m_i_water_out * (h_i_w_out - h_i_w_in)

    # 3. Zonas Pasteurizador (Balance Zona 7-14 para sacar m_botellas)
    m_ps_714 = (m_i_water_out / 14) * 8
    h_ps_714_out = h_water(60, 80)
    q_ps_cedido_714 = m_ps_714 * (h_i_w_out - h_ps_714_out)
    
    # Despeje m_botellas: Q = m * cp * dT
    m_botellas_kgs = q_ps_cedido_714 / (cp_prom_prod * (64 - 40))
    
    # 4. Producción
    botellas_dia = (m_botellas_kgs * 3600 * 24) / m_una_botella

    # 5. NTU Intercambiador
    cp_w_prom = cp_water(69, 80)
    c_min = m_i_water_out * cp_w_prom
    q_max = c_min * (151 - 52)
    eff = q_intercambiador / q_max
    ntu = -np.log(1 - eff)

    # --- MOSTRAR RESULTADOS ---
    st.title("📊 Monitor de Pasteurización Digital")
    
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Esquema de Planta")
        # Aquí cargarías tu imagen. Si no está en el repo, muestra un placeholder.
        try:
            img = Image.open("diagrama.png")
            st.image(img, caption="Diagrama de Flujo de Proceso", use_container_width=True)
        except:
            st.warning("⚠️ Sube tu imagen como 'diagrama.png' para verla aquí.")

    with col2:
        st.metric("Producción Diaria", f"{int(botellas_dia):,} botellas")
        st.metric("Flujo Agua Caliente", f"{m_i_water_out:.2f} kg/s")
        st.metric("Efectividad HX", f"{eff*100:.1f} %")
        st.metric("NTU Calculado", f"{ntu:.3f}")

    # Tabla de estados por zona
    st.subheader("📋 Estado de Zonas")
    data = {
        "Zona": ["1-6 (Pre-Cal)", "7-14 (Pasteur)", "15-20 (Enfriamiento)"],
        "Temp. Botella Out [C]": [40, 64, 22],
        "Carga Térmica [kW]": [m_botellas_kgs*cp_prom_prod*(40-4), q_ps_cedido_714, m_botellas_kgs*cp_prom_prod*(22-64)]
    }
    st.table(data)

except Exception as e:
    st.error(f"Error en los cálculos: {e}. Revisa las propiedades del fluido.")