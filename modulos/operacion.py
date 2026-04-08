import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
from db import db


def _show_tickets():
    """Contenido de la pestaña de Tickets (modificado según actualización 07-04)."""

    # Sub-tabs de Tickets: se eliminó "Cerrados", se dividió "Sin Visitas" en dos
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Crear Ticket",
        "📋 Tickets abiertos sin visitas",
        "📋 Tickets con seguimiento pendiente",
        "📅 Con Visitas",
        "🔒 Cerrar Ticket"
    ])

    with tab1:
        st.subheader("📝 Crear Nuevo Ticket")
        with st.form("crear_ticket_form"):
            col1, col2 = st.columns(2)
            with col1:
                numero_ticket = st.text_input("Número de Ticket*", placeholder="Ej: TKT-2024-001")
                id_equipo = st.text_input("ID del Equipo*", placeholder="Ej: EQ001")
                fecha_alta = st.date_input("Fecha de Alta*", value=datetime.now())
            with col2:
                if id_equipo:
                    equipo = db.execute_query(
                        "SELECT * FROM catalogo_equipos WHERE id_equipo = %s",
                        (id_equipo,)
                    )
                    if equipo:
                        st.success("✅ Equipo encontrado:")
                        st.info(f"""
                        **Cliente:** {equipo[0]['nombre_cliente']}
                        **Producto:** {equipo[0]['tipo_producto']}
                        **Sucursal:** {equipo[0]['sucursal_atencion']}
                        **Zona:** {equipo[0]['zona']}
                        """)
                    else:
                        st.warning("⚠️ Equipo no encontrado en catálogo")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit = st.form_submit_button("📋 Crear Ticket", use_container_width=True, type="primary")

            if submit:
                if not all([numero_ticket, id_equipo, fecha_alta]):
                    st.error("❌ Por favor complete todos los campos obligatorios (*)")
                else:
                    try:
                        db.execute_query(
                            "CALL crear_ticket(%s, %s, %s, NULL)",
                            (numero_ticket, id_equipo, fecha_alta)
                        )
                        st.success("✅ Ticket creado exitosamente!")
                        st.balloons()
                        ticket_info = db.execute_query(
                            "SELECT * FROM tickets WHERE numero_ticket = %s",
                            (numero_ticket,)
                        )
                        if ticket_info:
                            st.info(f"""
                            **Ticket ID:** {ticket_info[0]['id_ticket']}
                            **Número:** {ticket_info[0]['numero_ticket']}
                            **Fecha de alta:** {ticket_info[0]['fecha_alta']}
                            """)
                    except Exception as e:
                        st.error(f"❌ Error al crear ticket: {str(e)}")

    # Tab 2: Tickets abiertos sin visitas (sin ningún registro en tabla de visitas)
    with tab2:
        st.subheader("📋 Tickets Abiertos Sin Visitas")
        query_sin_visitas = """
        SELECT 
            t.id_ticket,
            t.numero_ticket,
            t.id_equipo,
            t.fecha_alta,
            c.nombre_cliente,
            c.tipo_producto,
            c.sucursal_atencion,
            c.zona,
            CURRENT_DATE - t.fecha_alta as dias_transcurridos,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE t.estatus_ticket = 'Abierto'
            AND NOT EXISTS (SELECT 1 FROM visitas v WHERE v.id_ticket = t.id_ticket)
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            t.fecha_alta;
        """
        data_sin_visitas = db.execute_query(query_sin_visitas)
        if data_sin_visitas:
            df_sin_visitas = pd.DataFrame(data_sin_visitas)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tickets", len(df_sin_visitas))
            with col2:
                alta_prioridad = len(df_sin_visitas[df_sin_visitas['prioridad'] == 'Alta'])
                st.metric("Alta Prioridad", alta_prioridad, delta_color="inverse")
            with col3:
                dias_promedio = df_sin_visitas['dias_transcurridos'].mean()
                st.metric("Días Promedio", f"{dias_promedio:.1f}")
            st.dataframe(
                df_sin_visitas[['numero_ticket', 'id_equipo', 'nombre_cliente',
                               'sucursal_atencion', 'zona', 'fecha_alta', 'dias_transcurridos', 'prioridad']],
                use_container_width=True, hide_index=True,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'zona': 'Zona', 'fecha_alta': 'Fecha Alta',
                    'dias_transcurridos': 'Días Abierto', 'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay tickets abiertos sin visitas")

    # Tab 3: Tickets con seguimiento pendiente (Abiertos con al menos una visita)
    with tab3:
        st.subheader("📋 Tickets con Seguimiento Pendiente")
        query_seguimiento = """
        SELECT 
            t.id_ticket,
            t.numero_ticket,
            t.id_equipo,
            t.fecha_alta,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            CURRENT_DATE - t.fecha_alta as dias_transcurridos,
            uv.fecha_solicitud as ultima_fecha_solicitud,
            uv.fecha_atencion as ultima_fecha_atencion,
            uv.estatus as estatus_ultima_visita,
            uv.comentarios as comentarios_ultima_visita
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        JOIN LATERAL (
            SELECT v.fecha_solicitud, v.fecha_atencion, v.estatus, v.comentarios
            FROM visitas v
            WHERE v.id_ticket = t.id_ticket
            ORDER BY v.fecha_solicitud DESC
            LIMIT 1
        ) uv ON true
        WHERE t.estatus_ticket = 'Abierto'
            AND EXISTS (SELECT 1 FROM visitas v WHERE v.id_ticket = t.id_ticket)
        ORDER BY t.fecha_alta;
        """
        data_seguimiento = db.execute_query(query_seguimiento)
        if data_seguimiento:
            df_seg = pd.DataFrame(data_seguimiento)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tickets", len(df_seg))
            with col2:
                dias_promedio = df_seg['dias_transcurridos'].mean()
                st.metric("Días Promedio Abierto", f"{dias_promedio:.1f}")
            with col3:
                pendientes = len(df_seg[df_seg['estatus_ultima_visita'].isin(['Sin programar', 'Programado'])])
                st.metric("Última Visita Pendiente", pendientes)
            st.dataframe(
                df_seg[['numero_ticket', 'id_equipo', 'nombre_cliente', 'sucursal_atencion',
                        'fecha_alta', 'ultima_fecha_solicitud', 'ultima_fecha_atencion',
                        'estatus_ultima_visita', 'comentarios_ultima_visita']],
                use_container_width=True, hide_index=True,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'fecha_alta': 'Fecha Alta',
                    'ultima_fecha_solicitud': 'Últ. Fecha Solicitud',
                    'ultima_fecha_atencion': 'Últ. Fecha Atención',
                    'estatus_ultima_visita': 'Estatus Últ. Visita',
                    'comentarios_ultima_visita': 'Comentarios Últ. Visita'
                }
            )
        else:
            st.info("✅ No hay tickets con seguimiento pendiente")

    # Tab 4: Con Visitas (Programados)
    with tab4:
        st.subheader("📅 Tickets Programados (Con Visitas)")
        query_tickets_con_visitas = """
        SELECT 
            t.id_ticket,
            t.numero_ticket,
            t.id_equipo,
            t.fecha_alta,
            t.cantidad_visitas,
            t.visitas_fallidas,
            c.nombre_cliente,
            c.tipo_producto,
            c.sucursal_atencion,
            c.zona,
            CURRENT_DATE - t.fecha_alta as dias_transcurridos,
            MAX(v.fecha_atencion) as ultima_visita_fecha,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        LEFT JOIN visitas v ON t.id_ticket = v.id_ticket
        WHERE t.estatus_ticket = 'Programado'
        GROUP BY t.id_ticket, c.id_equipo
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            t.fecha_alta;
        """
        data_con_visitas = db.execute_query(query_tickets_con_visitas)
        if data_con_visitas:
            df_con_visitas = pd.DataFrame(data_con_visitas)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tickets", len(df_con_visitas))
            with col2:
                total_visitas = df_con_visitas['cantidad_visitas'].sum()
                st.metric("Total Visitas", total_visitas)
            with col3:
                fallidas = df_con_visitas['visitas_fallidas'].sum()
                st.metric("Visitas Fallidas", fallidas, delta_color="inverse")
            st.dataframe(
                df_con_visitas[['numero_ticket', 'id_equipo', 'nombre_cliente',
                               'sucursal_atencion', 'cantidad_visitas', 'visitas_fallidas',
                               'dias_transcurridos', 'prioridad']],
                use_container_width=True, hide_index=True,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'cantidad_visitas': '# Visitas', 'visitas_fallidas': '# Fallidas',
                    'dias_transcurridos': 'Días Abierto', 'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay tickets programados con visitas")

    # Tab 5: Cerrar Ticket — con botón "Cargar Información del Ticket" (como en Servicios)
    with tab5:
        st.subheader("🔒 Cerrar Ticket")
        query_tickets_abiertos = """
        SELECT 
            t.id_ticket,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            t.fecha_alta,
            t.cantidad_visitas,
            CURRENT_DATE - t.fecha_alta as dias_abierto
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE t.estatus_ticket IN ('Abierto', 'Programado')
        ORDER BY t.numero_ticket;
        """
        tickets_abiertos = db.execute_query(query_tickets_abiertos)
        if tickets_abiertos:
            opciones_tickets = [f"{t['numero_ticket']} - {t['id_equipo']} ({t['nombre_cliente']}) - {t['dias_abierto']} días"
                               for t in tickets_abiertos]
            with st.form("cerrar_ticket_form"):
                ticket_seleccionado = st.selectbox(
                    "Seleccionar Ticket para Cerrar*", opciones_tickets,
                    help="Seleccione un ticket para cerrar",
                    key="cerrar_ticket_selectbox"
                )

                # Botón "Cargar Información del Ticket" — misma mecánica que Servicios
                if st.form_submit_button("📋 Cargar Información del Ticket", use_container_width=True):
                    if ticket_seleccionado:
                        numero_ticket_seleccionado = ticket_seleccionado.split(" - ")[0]
                        ticket_info = next((t for t in tickets_abiertos if t['numero_ticket'] == numero_ticket_seleccionado), None)
                        if ticket_info:
                            st.session_state.ticket_info_cerrar_ticket = ticket_info
                            st.success("✅ Información del ticket cargada correctamente")
                        else:
                            st.error("❌ No se pudo encontrar la información del ticket")

                if 'ticket_info_cerrar_ticket' in st.session_state:
                    ticket_info = st.session_state.ticket_info_cerrar_ticket
                    st.info(f"""
                    **Información del Ticket Cargada:**
                    - **Número:** {ticket_info['numero_ticket']}
                    - **ID Equipo:** {ticket_info['id_equipo']}
                    - **Cliente:** {ticket_info['nombre_cliente']}
                    - **Sucursal:** {ticket_info['sucursal_atencion']}
                    - **Zona:** {ticket_info['zona']}
                    - **Fecha Alta:** {ticket_info['fecha_alta']}
                    - **Visitas registradas:** {ticket_info['cantidad_visitas']}
                    - **Días Abierto:** {ticket_info['dias_abierto']} días
                    """)

                    fecha_cierre = st.date_input("Fecha de Cierre del Ticket*", value=datetime.now(), key="fecha_cierre_ticket")

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        submit_cierre = st.form_submit_button("🔒 Cerrar Ticket", use_container_width=True, type="primary")

                    if submit_cierre:
                        if not fecha_cierre:
                            st.error("❌ Por favor especifique la fecha de cierre")
                        else:
                            try:
                                id_ticket = st.session_state.ticket_info_cerrar_ticket['id_ticket']
                                db.execute_query("CALL cerrar_ticket(%s, %s)", (id_ticket, fecha_cierre), fetch=False)
                                st.success(f"✅ Ticket {ticket_info['numero_ticket']} cerrado exitosamente!")
                                st.balloons()
                                st.info(f"""
                                **Resumen del cierre:**
                                - **Ticket:** {ticket_info['numero_ticket']}
                                - **Equipo:** {ticket_info['id_equipo']}
                                - **Cliente:** {ticket_info['nombre_cliente']}
                                - **Fecha de cierre:** {fecha_cierre}
                                - **Días total abierto:** {ticket_info['dias_abierto']} días
                                """)
                                del st.session_state.ticket_info_cerrar_ticket
                            except Exception as e:
                                st.error(f"❌ Error al cerrar ticket: {str(e)}")
                else:
                    st.warning("⚠️ Seleccione un ticket y haga clic en 'Cargar Información del Ticket' para continuar")
        else:
            st.info("✅ No hay tickets abiertos para cerrar")


def _show_servicios():
    """Contenido de la pestaña de Servicios (funcionalidad existente sin cambios)."""

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "➕ Crear Visita", "📅 Programar Visita", "✅ Cerrar Visita",
        "⏰ Sin Programar", "📅 Hoy", "📋 Programadas", "⚠️ Pendientes"
    ])

    with tab1:
        st.subheader("➕ Crear Nueva Visita")
        query_tickets_abiertos = """
        SELECT 
            t.id_ticket,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            t.fecha_alta,
            CURRENT_DATE - t.fecha_alta as dias_abierto
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE t.estatus_ticket = 'Abierto'
        ORDER BY t.numero_ticket;
        """
        tickets_abiertos = db.execute_query(query_tickets_abiertos)
        if tickets_abiertos:
            opciones_tickets = [f"{t['numero_ticket']} - {t['id_equipo']} ({t['nombre_cliente']}) - {t['dias_abierto']} días"
                                for t in tickets_abiertos]
            with st.form("crear_visita_form"):
                ticket_seleccionado = st.selectbox(
                    "Seleccionar Ticket para Crear Visita*", opciones_tickets,
                    help="Seleccione un ticket en estado 'Abierto' para crear una visita",
                    key="crear_visita_selectbox"
                )
                if st.form_submit_button("📋 Cargar Información del Ticket", use_container_width=True):
                    if ticket_seleccionado:
                        numero_ticket_seleccionado = ticket_seleccionado.split(" - ")[0]
                        ticket_info = next((t for t in tickets_abiertos if t['numero_ticket'] == numero_ticket_seleccionado), None)
                        if ticket_info:
                            st.session_state.ticket_info_crear_visita = ticket_info
                            st.success("✅ Información del ticket cargada correctamente")
                        else:
                            st.error("❌ No se pudo encontrar la información del ticket")

                if 'ticket_info_crear_visita' in st.session_state:
                    ticket_info = st.session_state.ticket_info_crear_visita
                    st.info(f"""
                    **Información del Ticket Cargada:**
                    - **Número:** {ticket_info['numero_ticket']}
                    - **ID Equipo:** {ticket_info['id_equipo']}
                    - **Cliente:** {ticket_info['nombre_cliente']}
                    - **Días Abierto:** {ticket_info['dias_abierto']} días
                    """)
                    fecha_solicitud = st.date_input(
                        "Fecha de Solicitud de la Visita*", value=datetime.now(),
                        key="fecha_solicitud_crear"
                    )
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        submit_visita = st.form_submit_button("➕ Crear Visita", use_container_width=True, type="primary")
                    if submit_visita:
                        if not fecha_solicitud:
                            st.error("❌ Por favor especifique la fecha de solicitud")
                        else:
                            try:
                                id_ticket = st.session_state.ticket_info_crear_visita['id_ticket']
                                db.execute_query(
                                    "CALL registrar_visita(%s, %s, NULL, NULL)",
                                    (id_ticket, fecha_solicitud)
                                )
                                st.success(f"✅ Visita creada exitosamente para el ticket {st.session_state.ticket_info_crear_visita['numero_ticket']}!")
                                st.balloons()
                                st.info(f"""
                                **Resumen de la visita creada:**
                                - **Ticket:** {st.session_state.ticket_info_crear_visita['numero_ticket']}
                                - **Equipo:** {st.session_state.ticket_info_crear_visita['id_equipo']}
                                - **Cliente:** {st.session_state.ticket_info_crear_visita['nombre_cliente']}
                                - **Fecha de solicitud:** {fecha_solicitud}
                                """)
                                del st.session_state.ticket_info_crear_visita
                            except Exception as e:
                                st.error(f"❌ Error al crear visita: {str(e)}")
                else:
                    st.warning("⚠️ Seleccione un ticket y haga clic en 'Cargar Información del Ticket' para continuar")
        else:
            st.info("✅ No hay tickets abiertos para crear visitas")

    with tab2:
        st.subheader("📅 Programar Visita")
        query_visitas_sin_programar = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            v.fecha_solicitud,
            CURRENT_DATE - v.fecha_solicitud as dias_desde_solicitud
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Sin programar'
            AND t.estatus_ticket IN ('Abierto', 'Programado')
        ORDER BY v.fecha_solicitud;
        """
        visitas_sin_programar = db.execute_query(query_visitas_sin_programar)
        if visitas_sin_programar:
            mapa_visitas = {f"ID: {v['id_visita']} - Folio: {v['folio']} - Ticket: {v['numero_ticket']} - {v['id_equipo']} (Solicitado: {v['fecha_solicitud']})": v
                            for v in visitas_sin_programar}
            opciones_visitas = list(mapa_visitas.keys())
            with st.form("programar_visita_form"):
                visita_seleccionada = st.selectbox(
                    "Seleccionar Visita para Programar*", opciones_visitas,
                    help="Seleccione una visita en estado 'Sin programar' para programar",
                    key="programar_visita_selectbox"
                )
                if st.form_submit_button("📋 Cargar Información de la Visita", use_container_width=True):
                    if visita_seleccionada:
                        visita_info = mapa_visitas.get(visita_seleccionada)
                        if visita_info:
                            st.session_state.visita_info_programar = visita_info
                            st.success("✅ Información de la visita cargada correctamente")
                        else:
                            st.error("❌ No se pudo encontrar la información de la visita")

                if 'visita_info_programar' in st.session_state:
                    visita_info = st.session_state.visita_info_programar
                    st.info(f"""
                    **Información de la Visita Cargada:**
                    - **ID Visita:** {visita_info['id_visita']}
                    - **Ticket:** {visita_info['numero_ticket']}
                    - **Folio:** {visita_info['folio']}
                    - **Equipo:** {visita_info['id_equipo']}
                    - **Cliente:** {visita_info['nombre_cliente']}
                    - **Fecha de solicitud:** {visita_info['fecha_solicitud']}
                    - **Días desde solicitud:** {visita_info['dias_desde_solicitud']} días
                    """)
                    col1, col2 = st.columns(2)
                    with col1:
                        fecha_respuesta = st.date_input("Fecha de Respuesta*", value=datetime.now(), key="fecha_respuesta_programar")
                    with col2:
                        fecha_atencion = st.date_input("Fecha de Atención*", value=datetime.now() + timedelta(days=1), key="fecha_atencion_programar")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        submit_programar = st.form_submit_button("📅 Programar Visita", use_container_width=True, type="primary")
                    if submit_programar:
                        if not fecha_respuesta or not fecha_atencion:
                            st.error("❌ Por favor complete todos los campos")
                        elif fecha_atencion < fecha_respuesta:
                            st.error("❌ La fecha de atención no puede ser anterior a la fecha de respuesta")
                        else:
                            try:
                                id_visita = st.session_state.visita_info_programar['id_visita']
                                db.execute_query(
                                    "CALL programar_visita(%s, %s, %s)",
                                    (id_visita, fecha_respuesta, fecha_atencion)
                                )
                                st.success(f"✅ Visita {st.session_state.visita_info_programar['folio']} programada exitosamente!")
                                st.balloons()
                                st.info(f"""
                                **Resumen de la programación:**
                                - **ID Visita:** {st.session_state.visita_info_programar['id_visita']}
                                - **Ticket:** {st.session_state.visita_info_programar['numero_ticket']}
                                - **Folio:** {st.session_state.visita_info_programar['folio']}
                                - **Equipo:** {st.session_state.visita_info_programar['id_equipo']}
                                - **Fecha de respuesta:** {fecha_respuesta}
                                - **Fecha de atención:** {fecha_atencion}
                                """)
                                del st.session_state.visita_info_programar
                            except Exception as e:
                                st.error(f"❌ Error al programar visita: {str(e)}")
                else:
                    st.warning("⚠️ Seleccione una visita y haga clic en 'Cargar Información de la Visita' para continuar")
        else:
            st.info("✅ No hay visitas sin programar")

    with tab3:
        st.subheader("✅ Cerrar Visita")
        query_visitas_programadas = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            v.fecha_atencion,
            CURRENT_DATE - v.fecha_atencion as dias_desde_atencion
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion IS NOT NULL
            AND t.estatus_ticket IN ('Abierto', 'Programado')
        ORDER BY v.fecha_atencion;
        """
        visitas_programadas = db.execute_query(query_visitas_programadas)
        if visitas_programadas:
            mapa_visitas = {f"ID: {v['id_visita']} - Folio: {v['folio']} - Ticket: {v['numero_ticket']} - {v['id_equipo']} (Atención: {v['fecha_atencion']})": v
                            for v in visitas_programadas}
            opciones_visitas = list(mapa_visitas.keys())
            with st.form("cerrar_visita_form"):
                visita_seleccionada = st.selectbox(
                    "Seleccionar Visita para Cerrar*", opciones_visitas,
                    help="Seleccione una visita en estado 'Programado' para cerrar",
                    key="cerrar_visita_selectbox"
                )
                if st.form_submit_button("📋 Cargar Información de la Visita", use_container_width=True):
                    if visita_seleccionada:
                        visita_info = mapa_visitas.get(visita_seleccionada)
                        if visita_info:
                            st.session_state.visita_info_cerrar = visita_info
                            st.success("✅ Información de la visita cargada correctamente")
                        else:
                            st.error("❌ No se pudo encontrar la información de la visita")

                if 'visita_info_cerrar' in st.session_state:
                    visita_info = st.session_state.visita_info_cerrar
                    st.info(f"""
                    **Información de la Visita Cargada:**
                    - **ID Visita:** {visita_info['id_visita']}
                    - **Ticket:** {visita_info['numero_ticket']}
                    - **Folio:** {visita_info['folio']}
                    - **Equipo:** {visita_info['id_equipo']}
                    - **Cliente:** {visita_info['nombre_cliente']}
                    - **Fecha de atención:** {visita_info['fecha_atencion']}
                    - **Días desde atención:** {visita_info['dias_desde_atencion']} días
                    """)
                    estatus_final = st.selectbox(
                        "Estatus Final de la Visita*",
                        ["Efectivo", "Fallido", "Cancelado", "Sin Respuesta"],
                        help="Seleccione el resultado final de la visita",
                        key="estatus_final_cerrar"
                    )
                    comentarios = st.text_area(
                        "Comentarios de Cierre (Opcional)",
                        placeholder="Ingrese observaciones, hallazgos o comentarios sobre la visita...",
                        height=100,
                        key="comentarios_cerrar"
                    )
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        submit_cierre = st.form_submit_button("✅ Cerrar Visita", use_container_width=True, type="primary")
                    if submit_cierre:
                        if not estatus_final:
                            st.error("❌ Por favor especifique el estatus final")
                        else:
                            try:
                                id_visita = st.session_state.visita_info_cerrar['id_visita']
                                db.execute_query(
                                    "CALL cerrar_visita(%s, %s, %s)",
                                    (id_visita, estatus_final, comentarios if comentarios else None)
                                )
                                st.success(f"✅ Visita {st.session_state.visita_info_cerrar['folio']} cerrada exitosamente como {estatus_final}!")
                                st.balloons()
                                st.info(f"""
                                **Resumen del cierre:**
                                - **ID Visita:** {st.session_state.visita_info_cerrar['id_visita']}
                                - **Ticket:** {st.session_state.visita_info_cerrar['numero_ticket']}
                                - **Folio:** {st.session_state.visita_info_cerrar['folio']}
                                - **Equipo:** {st.session_state.visita_info_cerrar['id_equipo']}
                                - **Estatus final:** {estatus_final}
                                """)
                                del st.session_state.visita_info_cerrar
                            except Exception as e:
                                st.error(f"❌ Error al cerrar visita: {str(e)}")
                else:
                    st.warning("⚠️ Seleccione una visita y haga clic en 'Cargar Información de la Visita' para continuar")
        else:
            st.info("✅ No hay visitas programadas pendientes de cierre")

    with tab4:
        st.subheader("⏰ Visitas Sin Programar")
        query_sin_programar = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            v.fecha_solicitud,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad,
            CURRENT_DATE - v.fecha_solicitud as dias_desde_solicitud
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Sin programar'
            AND t.estatus_ticket IN ('Abierto', 'Programado')
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
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Visitas", len(df_sin_programar))
            with col2:
                alta_prioridad = len(df_sin_programar[df_sin_programar['prioridad'] == 'Alta'])
                st.metric("Alta Prioridad", alta_prioridad, delta_color="inverse")
            with col3:
                dias_promedio = df_sin_programar['dias_desde_solicitud'].mean()
                st.metric("Días Promedio", f"{dias_promedio:.1f}")
            st.dataframe(
                df_sin_programar[['folio', 'numero_ticket', 'id_equipo', 'nombre_cliente',
                                 'sucursal_atencion', 'fecha_solicitud', 'dias_desde_solicitud', 'prioridad']],
                use_container_width=True, hide_index=True,
                column_config={
                    'folio': 'Folio', 'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'fecha_solicitud': 'Fecha Solicitud', 'dias_desde_solicitud': 'Días Pendiente',
                    'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay visitas sin programar")

    with tab5:
        st.subheader("📅 Visitas para Hoy")
        query_hoy = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            v.fecha_solicitud,
            v.fecha_respuesta,
            v.fecha_atencion,
            v.tiempo_respuesta,
            v.tiempo_atencion,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion = CURRENT_DATE
            AND t.estatus_ticket IN ('Abierto', 'Programado')
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            v.fecha_atencion;
        """
        data_hoy = db.execute_query(query_hoy)
        if data_hoy:
            df_hoy = pd.DataFrame(data_hoy)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Visitas Hoy", len(df_hoy))
            with col2:
                alta_prioridad = len(df_hoy[df_hoy['prioridad'] == 'Alta'])
                st.metric("Alta Prioridad", alta_prioridad, delta_color="inverse")
            with col3:
                tiempo_respuesta_prom = df_hoy['tiempo_respuesta'].mean()
                st.metric("Respuesta Promedio", f"{tiempo_respuesta_prom:.1f} días")
            st.dataframe(
                df_hoy[['folio', 'numero_ticket', 'id_equipo', 'nombre_cliente',
                       'sucursal_atencion', 'fecha_atencion', 'prioridad']],
                use_container_width=True, hide_index=True,
                column_config={
                    'folio': 'Folio', 'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'fecha_atencion': 'Fecha Atención', 'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay visitas para hoy")

    with tab6:
        st.subheader("📋 Visitas Programadas Futuras")
        query_programadas = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            v.fecha_atencion,
            v.fecha_atencion - CURRENT_DATE as dias_para_atencion,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion > CURRENT_DATE
            AND t.estatus_ticket IN ('Abierto', 'Programado')
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            v.fecha_atencion;
        """
        data_programadas = db.execute_query(query_programadas)
        if data_programadas:
            df_programadas = pd.DataFrame(data_programadas)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Visitas Futuras", len(df_programadas))
            with col2:
                proxima_atencion = df_programadas['fecha_atencion'].min()
                if proxima_atencion:
                    dias_proxima = (proxima_atencion - datetime.now().date()).days
                    st.metric("Próxima Atención", f"En {dias_proxima} días")
            with col3:
                avg_dias_para = df_programadas['dias_para_atencion'].mean()
                st.metric("Promedio Días", f"{avg_dias_para:.1f}")
            st.dataframe(
                df_programadas[['folio', 'numero_ticket', 'id_equipo', 'nombre_cliente',
                               'sucursal_atencion', 'fecha_atencion', 'dias_para_atencion', 'prioridad']],
                use_container_width=True, hide_index=True,
                column_config={
                    'folio': 'Folio', 'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'fecha_atencion': 'Fecha Atención', 'dias_para_atencion': 'Días para Atención',
                    'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay visitas programadas futuras")

    with tab7:
        st.subheader("⚠️ Visitas Pendientes de Cierre")
        query_pendientes = """
        SELECT 
            v.id_visita,
            v.folio,
            t.numero_ticket,
            t.id_equipo,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            v.fecha_atencion,
            CURRENT_DATE - v.fecha_atencion as dias_desde_atencion,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE v.estatus = 'Programado'
            AND v.fecha_atencion < CURRENT_DATE
            AND t.estatus_ticket IN ('Abierto', 'Programado')
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            v.fecha_atencion;
        """
        data_pendientes = db.execute_query(query_pendientes)
        if data_pendientes:
            df_pendientes = pd.DataFrame(data_pendientes)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Visitas Pendientes", len(df_pendientes))
            with col2:
                max_dias = df_pendientes['dias_desde_atencion'].max()
                st.metric("Máximo Días", f"{max_dias} días", delta_color="inverse")
            with col3:
                avg_dias = df_pendientes['dias_desde_atencion'].mean()
                st.metric("Promedio Días", f"{avg_dias:.1f} días")
            st.dataframe(
                df_pendientes[['folio', 'numero_ticket', 'id_equipo', 'nombre_cliente',
                              'sucursal_atencion', 'fecha_atencion', 'dias_desde_atencion', 'prioridad']],
                use_container_width=True, hide_index=True,
                column_config={
                    'folio': 'Folio', 'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'fecha_atencion': 'Fecha Atención', 'dias_desde_atencion': 'Días Pendiente',
                    'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay visitas pendientes de cierre")


def _show_agregar_equipo():
    """Contenido de la pestaña Agregar Equipo (modificado según actualización 07-04)."""

    # Obtener sucursales de la tabla Sucursales
    sucursales_data = db.execute_query("SELECT id_sucursal, nombre_sucursal, zona FROM sucursales ORDER BY nombre_sucursal")
    sucursales_map = {}
    sucursales_nombres = []
    if sucursales_data:
        for s in sucursales_data:
            sucursales_map[s['nombre_sucursal']] = s['zona']
            sucursales_nombres.append(s['nombre_sucursal'])

    with st.form("agregar_equipo_form"):
        col1, col2 = st.columns(2)
        with col1:
            id_equipo = st.text_input("ID del Equipo*", placeholder="Ej: EQ001")
            nombre_cliente = st.text_input("Nombre del Cliente*", placeholder="Ej: Cliente Corporativo S.A.")
            # Tipo de producto: SelectBox con opciones fijas
            tipo_producto = st.selectbox("Tipo de Producto*", ["Compusafe", "Brinks"])
        with col2:
            # Sucursal de atención: SelectBox desde BD
            if sucursales_nombres:
                sucursal_atencion = st.selectbox("Sucursal de Atención*", sucursales_nombres, key="sucursal_selectbox")
                # Zona: auto-asignada según sucursal seleccionada (no visible en el formulario)
                zona_auto = sucursales_map.get(sucursal_atencion, "")
            else:
                sucursal_atencion = st.text_input("Sucursal de Atención*", placeholder="Ej: Sucursal Centro")
                zona_auto = st.selectbox("Zona*", ["SUR", "CENTRO", "VALLE", "BAJIO", "NORTE", "NOROESTE"])

        submit = st.form_submit_button("➕ Agregar Equipo", use_container_width=True, type="primary")

        if submit:
            zona_final = zona_auto if sucursales_nombres else zona_auto
            if not all([id_equipo, nombre_cliente, tipo_producto, sucursal_atencion, zona_final]):
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
                        (id_equipo, nombre_cliente, tipo_producto, sucursal_atencion, zona_final),
                        fetch=False
                    )
                    st.success("✅ Equipo agregado/actualizado exitosamente!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


def show_operacion():
    """Página unificada de Operación: Tickets + Servicios + Agregar Equipo."""
    st.markdown('<h1 class="main-header">🛠️ Operación</h1>', unsafe_allow_html=True)

    tab_tickets, tab_servicios, tab_equipo = st.tabs([
        "🎫 Tickets", "🔧 Servicios", "➕ Agregar Equipo"
    ])

    with tab_tickets:
        _show_tickets()

    with tab_servicios:
        _show_servicios()

    with tab_equipo:
        _show_agregar_equipo()
