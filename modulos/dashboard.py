import streamlit as st
import pandas as pd
from db import db

def show_dashboard():
    st.markdown('<h1 class="main-header">🚙 RUTAS</h1>', unsafe_allow_html=True)
    st.divider()

    # Widgets del dashboard (2x2 grid)
    col1, col2 = st.columns(2)

    with col1:
        # Widget 1: Visitas Sin Programar
        st.markdown('<div class="widget-header">⏰ Visitas Sin Programar</div>', unsafe_allow_html=True)

        query_sin_programar = """
        SELECT 
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            v.fecha_solicitud,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Sin programar'
            AND t.estatus_ticket = 'Programado'
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            v.fecha_solicitud;
        """

        data_sin_programar = db.execute_query(query_sin_programar)
        if data_sin_programar:
            df_sin_programar = pd.DataFrame(data_sin_programar)
            st.dataframe(df_sin_programar[['numero_ticket', 'nombre_cliente', 'sucursal_atencion', 'fecha_solicitud']],
                        width='stretch', hide_index=True)
            st.caption(f"Mostrando {min(len(df_sin_programar), 5)} de {len(data_sin_programar)} visitas")
        else:
            st.info("No hay visitas sin programar")
        st.markdown('</div>', unsafe_allow_html=True)

        # Widget 2: Visitas Programadas
        st.markdown('<div class="widget-header">📅 Visitas programadas</div>', unsafe_allow_html=True)

        query_programadas = """
        SELECT 
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            v.fecha_atencion,
            v.tiempo_atencion as dias_desde_solicitud
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion > CURRENT_DATE
        ORDER BY v.fecha_atencion;
        """

        data_programadas = db.execute_query(query_programadas)
        if data_programadas:
            df_programadas = pd.DataFrame(data_programadas)
            st.dataframe(df_programadas[['numero_ticket', 'nombre_cliente', 'sucursal_atencion', 'fecha_atencion']],
                        width='stretch', hide_index=True)
        else:
            st.info("No hay visitas programadas futuras")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # Widget 3: Visitas para Hoy
        st.markdown('<div class="widget-header">📅 Visitas para Hoy</div>', unsafe_allow_html=True)

        query_hoy = """
        SELECT 
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            v.fecha_solicitud,
            v.fecha_respuesta,
            v.fecha_atencion,
            v.tiempo_respuesta,
            v.tiempo_atencion
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion = CURRENT_DATE
        ORDER BY v.fecha_atencion;
        """

        data_hoy = db.execute_query(query_hoy)
        if data_hoy:
            df_hoy = pd.DataFrame(data_hoy)
            st.dataframe(df_hoy[['numero_ticket', 'nombre_cliente', 'sucursal_atencion', 'fecha_atencion']],
                        width='stretch', hide_index=True)
        else:
            st.info("No hay visitas para hoy")
        st.markdown('</div>', unsafe_allow_html=True)

        # Widget 4: Visitas Sin Cierre
        st.markdown('<div class="widget-header">⚠️ Visitas sin Cierre</div>', unsafe_allow_html=True)

        query_sin_cierre = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_ticket,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            v.fecha_solicitud,
            v.fecha_atencion,
            CURRENT_DATE - v.fecha_atencion as dias_desde_atencion
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion IS NOT NULL
            AND v.fecha_atencion < CURRENT_DATE
        ORDER BY v.fecha_atencion;
        """

        data_sin_cierre = db.execute_query(query_sin_cierre)
        if data_sin_cierre:
            df_sin_cierre = pd.DataFrame(data_sin_cierre)
            st.dataframe(df_sin_cierre[['numero_ticket', 'nombre_cliente', 'sucursal_atencion', 'fecha_atencion', 'dias_desde_atencion']],
                        width='stretch', hide_index=True)
        else:
            st.info("No hay visitas sin cierre")
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabla Pendientes
    st.markdown("---")
    st.subheader("PENDIENTES")

    query_pendientes = """
    SELECT 
        t.numero_ticket AS ticket,
        t.id_equipo AS equipo,
        c.nombre_cliente AS cliente,
        c.sucursal_atencion AS sucursal,
        v.estatus,
        v.fecha_solicitud,
        (CURRENT_DATE - v.fecha_solicitud) AS dias
    FROM visitas v
    JOIN tickets t ON v.id_ticket = t.id_ticket
    JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
    WHERE v.estatus IN ('Sin programar', 'Programado')
        AND (CURRENT_DATE - v.fecha_solicitud) >= 3
    ORDER BY 
        CASE WHEN v.estatus = 'Sin programar' THEN 1 ELSE 2 END,
        dias DESC,
        t.numero_ticket;
    """

    data_pendientes = db.execute_query(query_pendientes)

    if data_pendientes:
        df_pendientes = pd.DataFrame(data_pendientes)
        st.caption(f"Total de visitas pendientes con más de 3 días: {len(df_pendientes)}")
        st.dataframe(
            df_pendientes,
            column_config={
                "ticket": "Ticket",
                "equipo": "Equipo",
                "cliente": "Cliente",
                "sucursal": "Sucursal",
                "estatus": "Estatus",
                "fecha_solicitud": st.column_config.DateColumn("Fecha Solicitud"),
                "dias": "Días"
            },
            hide_index=True,
            width='stretch'
        )
    else:
        st.info("No hay visitas pendientes con 3 o más días de antigüedad.")