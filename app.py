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

with st.sidebar.expander("1. SISTEMA DE CALDERA", expanded=True):
    m_vapor_gen = st.number_input("Flujo Vapor Generado [kg/s]", value=1.472, format="%.3f")
    n_b = st.number_input("Eficiencia de Caldera (0-1)", value=0.96)
    LHV = st.number_input("Poder Calorifico (LHV) [kJ/kg]", value=34300.0)
    T_b_in = st.number_input("Temp. Entrada Agua [C]", value=94.0)
    T_b_out = st.number_input("Temp. Salida Vapor [C]", value=162.0)
    P_b_out = st.number_input("Presion de Vapor [kPa]", value=550.0)

with st.sidebar.expander("2. INTERCAMBIADOR DE CALOR (HX)", expanded=True):
    # Inputs de diseño solicitados
    U_diseno = st.number_input("Coeficiente Global U [W/m2-K]", value=1500.0)
    N_placas = st.number_input("Numero de Placas", value=200)
    
    st.markdown("---")
    T_I_steam_IN = st.number_input("Temp. Vapor Entrada HX [C]", value=151.0)
    P_I_steam_IN = st.number_input("Presion Vapor Entrada [kPa]", value=500.0)
    T_I_cond_OUT = st.number_input("Temp. Condensado Salida [C]", value=82.0)
    T_I_water_IN = st.number_input("Temp. Agua Entrada HX [C]", value=52.0)
    T_I_water_OUT = st.number_input("Temp. Agua Salida HX [C]", value=86.0)
    P_I_water_OUT = st.number_input("Presion Agua Proceso [kPa]", value=80.0)

with st.sidebar.expander("3. DATOS DEL PRODUCTO", expanded=True):
    m_vidrio = st.number_input("Masa Vidrio (Envase) [kg]", value=0.35)
    cp_vidrio = st.number_input("Cp Vidrio [kJ/kg-K]", value=0.86)
    m_cerveza = st.number_input("Masa Cerveza [kg]", value=1.2)
    cp_cerveza = st.number_input("Cp Cerveza [kJ/kg-K]", value=3.85)

with st.sidebar.expander("4. TEMPERATURAS DE PROCESO", expanded=False):
    T_botella_IN = st.number_input("Temp. Entrada Etapa 1 [C]", value=4.0)
    T_botella_16_OUT = st.number_input("Temp. Salida Etapa 1 [C]", value=40.0)
    T_botella_714_OUT = st.number_input("Temp. Salida Etapa 2 [C]", value=64.0)
    T_botella_1520_OUT = st.number_input("Temp. Salida Final [C]", value=22.0)

# --- CALCULOS ---
try:
    # Caldera
    H_b_in = h_liq(T_b_in, P_b_out)
    H_b_out = h_vap(T_b_out, 1)
    Q_caldera_ganado = m_vapor_gen * (H_b_out - H_b_in)
    m_comb = Q_caldera_ganado / (n_b * LHV)
    
    # Intercambiador
    m_I_steam_IN = m_vapor_gen * 0.95
    h_s_in = h_vap(T_I_steam_IN, 1)
    h_cond = h_liq(T_I_cond_OUT, P_I_steam_IN)
    Q_vapor_cedido = m_I_steam_IN * (h_s_in - h_cond)
    
    h_I_water_IN = h_liq(T_I_water_IN, P_I_water_OUT)
    h_I_water_OUT = h_liq(T_I_water_OUT, P_I_water_OUT)
    m_I_water_OUT = Q_vapor_cedido / (h_I_water_OUT - h_I_water_IN)
    Q_agua_ganado_HX = m_I_water_OUT * (h_I_water_OUT - h_I_water_IN)

    # Eficiencia/Efectividad HX
    cp_w_prom = cp_f((T_I_water_IN + T_I_water_OUT)/2, P_I_water_OUT)
    C_min = m_I_water_OUT * cp_w_prom
    Q_max = C_min * (T_I_steam_IN - T_I_water_IN)
    efectividad_hx = Q_agua_ganado_HX / Q_max

    # Producto
    m_total_prod = m_vidrio + m_cerveza
    cp_prom_prod = (m_vidrio * cp_vidrio + m_cerveza * cp_cerveza) / m_total_prod
    
    # Pasteurizacion
    m_PS_714 = (m_I_water_OUT / 14) * 8
    Q_agua_cedido_PS = m_PS_714 * (h_I_water_OUT - h_liq(60.0, P_I_water_OUT))
    m_botellas_kgs = Q_agua_cedido_PS / (cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT))
    Q_botellas_ganado = m_botellas_kgs * cp_prom_prod * (T_botella_714_OUT - T_botella_16_OUT)
    
    produccion_dia = (m_botellas_kgs * 3600 * 24) / m_total_prod

    # --- PANTALLA PRINCIPAL ---
    st.title("Monitor Tecnico de Planta")
    st.divider()

    c_main, c_side = st.columns([2, 1])

    with c_main:
        try:
            st.image("diagrama.png", use_container_width=True)
        except:
            st.warning("Diagrama no encontrado en el repositorio.")
        
        st.subheader("Resumen de Flujos Masicos")
        tabla_flujos = {
            "Corriente": ["Combustible", "Vapor de Agua", "Agua de Proceso", "Producto (Masa Total)"],
            "Flujo [kg/s]": [f"{m_comb:.4f}", f"{m_I_steam_IN:.4f}", f"{m_I_water_OUT:.4f}", f"{m_botellas_kgs:.4f}"]
        }
        st.table(tabla_flujos)

        st.subheader("Balances de Energia")
        tabla_calores = {
            "Componente": ["Caldera", "Intercambiador (HX)", "Pasteurizador (Zona 7-14)"],
            "Calor Cedido [kW]": [f"{m_comb*LHV:.2f}", f"{Q_vapor_cedido:.2f}", f"{Q_agua_cedido_PS:.2f}"],
            "Calor Ganado [kW]": [f"{Q_caldera_ganado:.2f}", f"{Q_agua_ganado_HX:.2f}", f"{Q_botellas_ganado:.2f}"]
        }
        st.table(tabla_calores)

    with c_side:
        st.subheader("Indicadores Clave")
        st.metric("Produccion", f"{int(produccion_dia):,} Botellas/Dia")
        st.metric("Eficiencia HX", f"{efectividad_hx*100:.2f} %")
        st.metric("U de Diseno", f"{U_diseno:.1f} W/m2-K")
        st.metric("Placas", f"{int(N_placas)}")
        
        st.divider()
        st.subheader("Detalles Adicionales")
        st.write(f"**Agua Proceso:** {m_I_water_OUT:.3f} kg/s")
        st.write(f"**Vapor en HX:** {m_I_steam_IN:.3f} kg/s")
        st.write(f"**Cp Producto:** {cp_prom_prod:.3f} kJ/kg-K")
        # Calculo de Area basado en la U introducida
        LMTD = 30 # Valor simplificado para visualizacion
        Area_req = (Q_agua_ganado_HX * 1000) / (U_diseno * LMTD)
        st.write(f"**Area Requerida (est.):** {Area_req:.2f} m2")

except Exception as e:
    st.error(f"Error en los calculos: {e}")

except Exception as e:
    st.error(f"Error en los calculos: {e}")
