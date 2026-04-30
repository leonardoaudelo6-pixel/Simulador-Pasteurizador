import streamlit as st
from CoolProp.CoolProp import PropsSI
import numpy as np
import pandas as pd
from PIL import Image

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Simulador de Pasteurizacion Pro", layout="wide")

# --- FUNCIONES DE PROPIEDADES ---
def h_liq(T_c, P_kpa):
    return PropsSI('H', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

def h_vap(T_c, Q):
    return PropsSI('H', 'T', T_c + 273.15, 'Q', Q, 'Water') / 1000

def cp_f(T_c, P_kpa):
    return PropsSI('C', 'T', T_c + 273.15, 'P', P_kpa * 1000, 'Water') / 1000

# --- BARRA LATERAL: CONTROL TOTAL ---
st.sidebar.title("Configuracion de Planta")

with st.sidebar.expander("🛠️ MANTENIMIENTO", expanded=True):
    t_dias = st.number_input("Dias sin limpiar", value=0, min_value=0)

with st.sidebar.expander("🔥 CALDERA", expanded=False):
    m_vapor_gen = st.number_input("Flujo Vapor Generado [kg/s]", value=1.472, format="%.3f")
    n_b = st.number_input("Eficiencia Caldera (0-1)", value=0.96)
    LHV = st.number_input("LHV [kJ/kg]", value=34300.0)
    T_b_in = st.number_input("T Entrada Agua Caldera [C]", value=94.0)
    T_b_out = st.number_input("T Salida Vapor Caldera [C]", value=162.0)
    P_b_out = st.number_input("Presion Vapor [kPa]", value=550.0)

with st.sidebar.expander("⚙️ INTERCAMBIADOR (HX)", expanded=True):
    T_I_steam_IN = st.number_input("T Vapor Entrada HX [C]", value=151.0)
    T_I_water_IN = st.number_input("T Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("T Agua Salida HX [C]", value=86.0)
    P_I_water = st.number_input("Presion Agua Proceso [kPa]", value=80.0)
    N_placas = st.number_input("Numero de Placas", value=200)

with st.sidebar.expander("🍺 PRODUCTO Y PROCESO", expanded=False):
    eficiencia_past = st.number_input("Eficiencia Pasteurizador", value=0.95)
    m_vidrio = st.number_input("Masa Vidrio [kg]", value=0.35)
    m_cerveza = st.number_input("Masa Cerveza [kg]", value=1.2)
    T_botella_714_OUT = st.number_input("T Salida Etapa 2 [C]", value=64.0)
    T_botella_16_OUT = st.number_input("T Salida Etapa 1 [C]", value=40.0)

# --- CALCULOS ---
try:
    # Parametros de ensuciamiento (Internos)
    R_f_max, beta_f = 0.0005, 0.06
    U_ideal_kW = 2.85  # kW/(m2-K) equivalente a 2850 W/(m2-K)

    # 1. Balances Caldera
    H_b_in, H_b_out = h_liq(T_b_in, P_b_out), h_vap(T_b_out, 1)
    Q_caldera = m_vapor_gen * (H_b_out - H_b_in)
    m_comb = Q_caldera / (n_b * LHV)

    # 2. Intercambiador Ideal
    m_I_steam_IN = m_vapor_gen * 0.95
    h_s_in, h_cond = h_vap(T_I_steam_IN, 1), h_liq(82.0, 500.0)
    Q_HX_ideal = m_I_steam_IN * (h_s_in - h_cond)
    
    h_I_w_in, h_I_w_out = h_liq(T_I_water_IN, P_I_water), h_liq(T_I_water_OUT, P_I_water)
    m_I_water_ideal = Q_HX_ideal / (h_I_w_out - h_I_w_in)
    
    C_min = m_I_water_ideal * cp_f(69.0, P_I_water)
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    E_ideal = Q_HX_ideal / Q_max
    Area_fisica = (-np.log(1 - E_ideal) * C_min) / U_ideal_kW

    # 3. Modelo Real (Ensuciamiento)
    R_f_kW = R_f_max / 1000 # Convertir resistencia a escala kW
    R_f_actual = (R_f_max * (1 - np.exp(-beta_f * t_dias)))
    # U real en kW/(m2-K)
    U_real_kW = 1 / ((1 / U_ideal_kW) + (R_f_actual * 1000))
    
    NTU_real = (U_real_kW * Area_fisica) / C_min
    E_real = 1 - np.exp(-NTU_real)
    Q_HX_real = E_real * Q_max

    # 4. Produccion
    m_una_botella = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * 0.86 + m_cerveza * 3.85) / m_una_botella
    m_I_water_real = Q_HX_real / (h_I_w_out - h_I_w_in)
    m_PS_714 = (m_I_water_real / 14) * 8
    Q_PS_cedido = m_PS_714 * (h_I_w_out - h_liq(58.2, P_I_water))
    m_botellas_real = (Q_PS_cedido * eficiencia_past) / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))
    produccion_dia = (m_botellas_real * 3600 * 24) / m_una_botella

    # --- INTERFAZ GRAFICA ---
    st.title("Monitor Tecnico: Planta de Pasteurizacion")
    st.divider()

    col_diag, col_res = st.columns([1.8, 1.2])

    with col_diag:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado.")
        
        # TABLA DE CALORES
        st.subheader("Balances Termicos Reales")
        st.table({
            "Componente": ["Consumo de Combustible", "Calor en Intercambiador (HX)", "Calor Efectivo Pasteurizado"],
            "Potencia [kW]": [f"{m_comb*LHV:.2f}", f"{Q_HX_real:.2f}", f"{Q_PS_cedido*eficiencia_past:.2f}"]
        })

        # GRAFICO DE PREDICCION ENTENDIBLE
        st.subheader("Analisis de Degradacion (Proxima Limpieza)")
        dias_proyeccion = np.arange(0, 61, 1)
        r_proy = R_f_max * (1 - np.exp(-beta_f * dias_proyeccion))
        u_proy = 1 / ((1 / U_ideal_kW) + (r_proy * 1000))
        
        chart_data = pd.DataFrame({"Dias": dias_proyeccion, "U Real": u_proy, "Limite Critico": U_ideal_kW * 0.85})
        st.line_chart(chart_data.set_index("Dias"), color=["#29b5e8", "#ff4b4b"])
        st.caption("La linea roja indica el limite critico (85% de eficiencia). Si la azul baja de ahi, se requiere limpieza.")

    with col_res:
        st.subheader("Indicadores de Desempeño")
        st.metric("Produccion Real", f"{int(produccion_dia):,} Bot/Dia")
        st.metric("Flujo Combustible", f"{m_comb:.4f} kg/s")
        
        st.divider()
        # COMPARATIVA U EN kW/m2K
        st.write("**Coeficiente Global U [kW/(m2·K)]**")
        c_u1, c_u2 = st.columns(2)
        c_u1.metric("Ideal", f"{U_ideal_kW:.3f}")
        c_u2.metric("Real", f"{U_real_kW:.3f}", delta=f"{U_real_kW - U_ideal_kW:.3f}")

        # EFICIENCIA
        st.write("**Efectividad del Sistema (E)**")
        c_e1, c_e2 = st.columns(2)
        c_e1.metric("Ideal", f"{E_ideal*100:.1f}%")
        c_e2.metric("Real", f"{E_real*100:.1f}%", delta=f"{(E_real - E_ideal)*100:.1f}%")

        st.divider()
        st.subheader("Estado de Operacion")
        if U_real_kW < (U_ideal_kW * 0.85):
            st.error("⚠️ ALERTA: Eficiencia Critica. Se recomienda mantenimiento.")
        else:
            st.success("✅ Operacion Normal.")
        
        st.write(f"Dias sin limpieza: **{t_dias}**")
        st.write(f"Agua de Proceso: **{m_I_water_real:.4f} kg/s**")

except Exception as e:
    st.error(f"Error en los calculos: {e}")
