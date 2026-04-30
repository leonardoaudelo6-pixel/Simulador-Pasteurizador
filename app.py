import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
from PIL import Image

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Simulador de Pasteurizacion v4.0", layout="wide")

# --- FUNCIONES DE PROPIEDADES ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def dens_f(T_c, P_kpa):
    return PropsSI('D', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water')

# --- BARRA LATERAL: INPUTS ---
st.sidebar.title("Parametros de Ingenieria")

with st.sidebar.expander("1. MANTENIMIENTO Y ENSUCIAMIENTO", expanded=True):
    t_dias = st.sidebar.number_input("Dias sin limpiar [dias]", value=0, min_value=0)
    R_f_max = st.sidebar.number_input("Resistencia Maxima (Rf_max)", value=0.0005, format="%.5f")
    beta_f = st.sidebar.number_input("Constante de Ensuciamiento (beta)", value=0.06, format="%.3f")

with st.sidebar.expander("2. CALDERA", expanded=True):
    m_b_in = st.sidebar.number_input("Flujo Alimentacion [kg/s]", value=1.472, format="%.3f")
    n_b = st.sidebar.number_input("Eficiencia Caldera", value=0.96)
    LHV = st.sidebar.number_input("LHV [kJ/kg]", value=34300.0)
    T_b_in = st.sidebar.number_input("T Entrada Caldera [C]", value=94.0)
    T_b_out = st.sidebar.number_input("T Salida Vapor [C]", value=162.0)
    P_b_out = st.sidebar.number_input("P Vapor [kPa]", value=550.0)

with st.sidebar.expander("3. DISEÑO HX (NTU)", expanded=False):
    N_placas = st.sidebar.number_input("Numero de Placas", value=200.0)
    b_c = st.sidebar.number_input("Espesor Canal b_c [m]", value=0.004, format="%.4f")
    w_c = st.sidebar.number_input("Ancho Placa w_c [m]", value=0.363, format="%.3f")
    T_I_steam_IN = st.sidebar.number_input("T Vapor Entrada HX [C]", value=151.0)
    T_I_water_IN = st.sidebar.number_input("T Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.sidebar.number_input("T Agua Salida HX [C]", value=86.0)

with st.sidebar.expander("4. PRODUCTO Y PASTEURIZADOR", expanded=True):
    eficiencia_past = st.sidebar.number_input("Eficiencia Pasteurizador", value=0.95)
    m_vidrio = st.sidebar.number_input("Masa Vidrio [kg]", value=0.35)
    m_cerveza = st.sidebar.number_input("Masa Cerveza [kg]", value=1.2)
    T_botella_IN = st.sidebar.number_input("T Entrada Botella [C]", value=4.0)
    T_botella_16_OUT = st.sidebar.number_input("T Salida Etapa 1 [C]", value=40.0)
    T_botella_714_OUT = st.sidebar.number_input("T Salida Etapa 2 [C]", value=64.0)
    T_botella_1520_OUT = st.sidebar.number_input("T Salida Etapa 3 [C]", value=22.0)

# --- CALCULOS ---
try:
    # 1. Balances Iniciales e Idealidad
    H_b_in, H_b_out = h_liq(T_b_in, P_b_out), h_vap(T_b_out, 1)
    Q_b_water = m_b_in * (H_b_out - H_b_in)
    
    m_I_steam_IN = m_b_in * 0.95
    h_s_in, h_cond = h_vap(T_I_steam_IN, 1), h_liq(82.0, 500.0)
    Q_HX_ideal = m_I_steam_IN * (h_s_in - h_cond)
    
    h_I_w_in, h_I_w_out = h_liq(T_I_water_IN, 80.0), h_liq(T_I_water_OUT, 80.0)
    m_I_water_ideal = Q_HX_ideal / (h_I_w_out - h_I_w_in)

    # 2. Calculo de U Ideal (NTU)
    cp_w = cp_f(69.0, 80.0)
    C_min = m_I_water_ideal * cp_w
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    E_ideal = Q_HX_ideal / Q_max
    NTU_ideal = -np.log(1 - E_ideal)
    
    # Suponiendo U_ideal base de diseño (puedes ajustar este valor segun tu calculo de alpha)
    U_ideal = 2850.0 
    Area_fisica = (NTU_ideal * C_min) / (U_ideal / 1000)

    # 3. Calculo de Ensuciamiento Real
    R_f = R_f_max * (1 - np.exp(-beta_f * t_dias))
    U_real = 1 / ((1 / U_ideal) + R_f)
    
    NTU_real = (U_real / 1000 * Area_fisica) / C_min
    E_real = 1 - np.exp(-NTU_real)
    Q_real = E_real * Q_max

    # 4. Produccion con Q Real
    m_una_botella = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella
    m_I_water_real = Q_real / (h_I_w_out - h_I_w_in)
    m_PS_714 = (m_I_water_real / 14) * 8
    Q_PS_cedido_714 = m_PS_714 * (h_I_w_out - h_liq(58.2, 80.0))
    m_botellas_kgs = (Q_PS_cedido_714 * eficiencia_past) / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))
    
    produccion_dia = (m_botellas_kgs * 3600 * 24) / m_una_botella

    # --- UI ---
    st.title("Monitor Tecnico: Analisis de Ensuciamiento Asintotico")
    st.divider()

    c_img, c_metrics = st.columns([2, 1])

    with c_img:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado.")
        
        st.subheader("Comparativa: Estado Ideal vs. Real")
        st.table({
            "Variable": ["Coeficiente Global U [W/m2-K]", "Eficiencia (Efectividad) [%]", "Calor Transferido [kW]"],
            "Ideal (Dia 0)": [f"{U_ideal:.1f}", f"{E_ideal*100:.2f}%", f"{Q_HX_ideal:.2f}"],
            "Real (Actual)": [f"{U_real:.1f}", f"{E_real*100:.2f}%", f"{Q_real:.2f}"]
        })

    with c_metrics:
        st.subheader("Impacto en Produccion")
        st.metric("Botellas por Dia", f"{int(produccion_dia):,}", 
                  delta=f"{int(produccion_dia - (Q_HX_ideal/Q_real)*produccion_dia):,}" if t_dias > 0 else None)
        
        st.metric("Dias sin limpiar", f"{t_dias} dias")
        st.metric("Resistencia R_f", f"{R_f:.6f}")
        
        st.divider()
        st.write("**Detalles Tecnicos:**")
        st.write(f"Area Instalada: {Area_fisica:.2f} m2")
        st.write(f"Flujo Agua Proceso Real: {m_I_water_real:.4f} kg/s")

except Exception as e:
    st.error(f"Error en los calculos: {e}")
