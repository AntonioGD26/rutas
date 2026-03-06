import streamlit as st
from db import db

def show_agregar_equipo():
    st.markdown('<h1 class="main-header">➕ Agregar Nuevo Equipo al Catálogo</h1>', unsafe_allow_html=True)

    with st.form("agregar_equipo_form"):
        col1, col2 = st.columns(2)
        with col1:
            id_equipo = st.text_input("ID del Equipo*", placeholder="Ej: EQ001")
            nombre_cliente = st.text_input("Nombre del Cliente*", placeholder="Ej: Cliente Corporativo S.A.")
            tipo_producto = st.text_input("Tipo de Producto*", placeholder="Ej: Impresora Láser")
        with col2:
            sucursal_atencion = st.text_input("Sucursal de Atención*", placeholder="Ej: Sucursal Centro")
            zona = st.selectbox("Zona*", ["SUR", "CENTRO", "VALLE", "BAJIO", "NORTE", "NOROESTE"])

        submit = st.form_submit_button("➕ Agregar Equipo", width='stretch', type="primary")

        if submit:
            if not all([id_equipo, nombre_cliente, tipo_producto, sucursal_atencion, zona]):
                st.error("❌ Por favor complete todos los campos obligatorios (*)")
            else:
                try:
                    db.execute_query(
                        """
                        INSERT INTO catalogo_equipos 
                        (id_equipo, nombre_cliente, tipo_producto, sucursal_atencion, zona)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id_equipo) DO UPDATE SET
                            nombre_cliente = EXCLUDED.nombre_cliente,
                            tipo_producto = EXCLUDED.tipo_producto,
                            sucursal_atencion = EXCLUDED.sucursal_atencion,
                            zona = EXCLUDED.zona;
                        """,
                        (id_equipo, nombre_cliente, tipo_producto, sucursal_atencion, zona),
                        fetch=False
                    )
                    st.success("✅ Equipo agregado/actualizado exitosamente!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")