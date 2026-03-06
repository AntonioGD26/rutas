import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
from db import db

def show_tickets():
    st.markdown('<h1 class="main-header">🎫 Gestión de Tickets</h1>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Crear Ticket", "📋 Sin Visitas", "📅 Con Visitas",
        "✅ Cerrados", "🔒 Cerrar Ticket", "📊 Todos los Tickets"
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
                submit = st.form_submit_button("📋 Crear Ticket", width='stretch', type="primary")

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

    with tab2:
        st.subheader("📋 Tickets Abiertos Sin Visitas")
        query_tickets_sin_visitas = """
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
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            t.fecha_alta;
        """
        data_sin_visitas = db.execute_query(query_tickets_sin_visitas)
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
                               'sucursal_atencion', 'dias_transcurridos', 'prioridad']],
                width='stretch', hide_index=True,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'dias_transcurridos': 'Días Abierto', 'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay tickets abiertos sin visitas")

    with tab3:
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
                width='stretch', hide_index=True,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'cantidad_visitas': '# Visitas', 'visitas_fallidas': '# Fallidas',
                    'dias_transcurridos': 'Días Abierto', 'prioridad': 'Prioridad'
                }
            )
        else:
            st.info("✅ No hay tickets programados con visitas")

    with tab4:
        st.subheader("✅ Tickets Cerrados")
        query_tickets_cerrados = """
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
            (SELECT MAX(fecha_atencion) FROM visitas WHERE id_ticket = t.id_ticket) as fecha_cierre,
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 'Baja'
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 'Media'
                ELSE 'Alta'
            END as prioridad
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE t.estatus_ticket = 'Cerrado'
        ORDER BY 
            CASE 
                WHEN (CURRENT_DATE - t.fecha_alta) <= 2 THEN 3
                WHEN (CURRENT_DATE - t.fecha_alta) <= 4 THEN 2
                ELSE 1
            END,
            t.fecha_alta DESC;
        """
        data_cerrados = db.execute_query(query_tickets_cerrados)
        if data_cerrados:
            df_cerrados = pd.DataFrame(data_cerrados)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Cerrados", len(df_cerrados))
            with col2:
                dias_promedio = df_cerrados['fecha_cierre'].apply(
                    lambda x: (datetime.now().date() - x).days if x else None
                ).mean()
                st.metric("Días Promedio", f"{dias_promedio:.1f}" if dias_promedio else "N/A")
            with col3:
                tasa_exito = (len(df_cerrados) - df_cerrados['visitas_fallidas'].sum()) / len(df_cerrados) * 100
                st.metric("Tasa Éxito", f"{tasa_exito:.1f}%")
            st.dataframe(
                df_cerrados[['numero_ticket', 'id_equipo', 'nombre_cliente',
                            'sucursal_atencion', 'cantidad_visitas', 'visitas_fallidas',
                            'fecha_alta', 'fecha_cierre']],
                width='stretch', hide_index=True,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'cantidad_visitas': '# Visitas', 'visitas_fallidas': '# Fallidas',
                    'fecha_alta': 'Fecha Alta', 'fecha_cierre': 'Fecha Cierre'
                }
            )
        else:
            st.info("✅ No hay tickets cerrados")

    with tab5:
        st.subheader("🔒 Cerrar Ticket")
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
            with st.form("cerrar_ticket_form"):
                ticket_seleccionado = st.selectbox(
                    "Seleccionar Ticket para Cerrar*", opciones_tickets,
                    help="Seleccione un ticket en estado 'Abierto' para cerrar"
                )
                if ticket_seleccionado:
                    numero_ticket_seleccionado = ticket_seleccionado.split(" - ")[0]
                    ticket_info = next((t for t in tickets_abiertos if t['numero_ticket'] == numero_ticket_seleccionado), None)
                    if ticket_info:
                        st.info(f"""
                        **Información del Ticket:**
                        - **Número:** {ticket_info['numero_ticket']}
                        - **ID Equipo:** {ticket_info['id_equipo']}
                        - **Cliente:** {ticket_info['nombre_cliente']}
                        - **Días Abierto:** {ticket_info['dias_abierto']} días
                        """)
                        fecha_cierre = st.date_input("Fecha de Cierre del Ticket*", value=datetime.now())
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    submit_cierre = st.form_submit_button("🔒 Cerrar Ticket", width='stretch', type="primary")
                if submit_cierre:
                    if not ticket_seleccionado or not fecha_cierre:
                        st.error("❌ Por favor seleccione un ticket y especifique la fecha de cierre")
                    else:
                        try:
                            id_ticket = ticket_info['id_ticket']
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
                        except Exception as e:
                            st.error(f"❌ Error al cerrar ticket: {str(e)}")
        else:
            st.info("✅ No hay tickets abiertos para cerrar")

    with tab6:
        st.subheader("📊 Todos los Tickets")
        query_todos_tickets = """
        WITH ultimas_visitas AS (
            SELECT 
                v.id_ticket,
                v.estatus as estatus_ultima_visita,
                ROW_NUMBER() OVER (PARTITION BY v.id_ticket ORDER BY v.fecha_solicitud DESC) as rn
            FROM visitas v
        )
        SELECT 
            t.id_ticket,
            t.numero_ticket,
            t.id_equipo,
            t.estatus_ticket,
            COALESCE(uv.estatus_ultima_visita, 'Sin visita') as estatus_ultima_visita,
            c.nombre_cliente,
            c.sucursal_atencion,
            c.zona,
            t.fecha_alta,
            t.cantidad_visitas,
            t.visitas_fallidas,
            CASE 
                WHEN t.estatus_ticket = 'Abierto' AND t.cantidad_visitas = 0 THEN '📭 Sin visitas'
                WHEN t.estatus_ticket = 'Abierto' AND t.cantidad_visitas > 0 THEN '🔄 Con visitas abiertas'
                WHEN t.estatus_ticket = 'Programado' THEN '📅 Programado'
                WHEN t.estatus_ticket = 'Cerrado' THEN '✅ Cerrado'
                ELSE t.estatus_ticket
            END as estado_detallado
        FROM tickets t
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        LEFT JOIN ultimas_visitas uv ON t.id_ticket = uv.id_ticket AND uv.rn = 1
        ORDER BY 
            CASE 
                WHEN t.estatus_ticket = 'Abierto' THEN 1
                WHEN t.estatus_ticket = 'Programado' THEN 2
                WHEN t.estatus_ticket = 'Cerrado' THEN 3
                ELSE 4
            END,
            t.numero_ticket ASC;
        """
        data_todos_tickets = db.execute_query(query_todos_tickets)
        if data_todos_tickets:
            df_todos = pd.DataFrame(data_todos_tickets)
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Tickets", len(df_todos))
            with col2:
                st.metric("Abiertos", len(df_todos[df_todos['estatus_ticket'] == 'Abierto']))
            with col3:
                st.metric("Programados", len(df_todos[df_todos['estatus_ticket'] == 'Programado']))
            with col4:
                st.metric("Cerrados", len(df_todos[df_todos['estatus_ticket'] == 'Cerrado']))
            with col5:
                st.metric("Sin visitas", len(df_todos[df_todos['estatus_ultima_visita'] == 'Sin visita']))

            st.markdown("### 🎯 Filtros Avanzados")
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            with col_filtro1:
                filtro_estatus_ticket = st.multiselect(
                    "Filtrar por Estatus de Ticket",
                    options=df_todos['estatus_ticket'].unique(),
                    default=df_todos['estatus_ticket'].unique()
                )
            with col_filtro2:
                estatus_visita_opciones = sorted(df_todos['estatus_ultima_visita'].unique())
                filtro_estatus_visita = st.multiselect(
                    "Filtrar por Estatus de Visita",
                    options=estatus_visita_opciones,
                    default=estatus_visita_opciones
                )
            with col_filtro3:
                zonas_opciones = sorted(df_todos['zona'].dropna().unique())
                filtro_zona = st.multiselect(
                    "Filtrar por Zona",
                    options=zonas_opciones,
                    default=zonas_opciones
                )

            df_filtrado = df_todos.copy()
            if filtro_estatus_ticket:
                df_filtrado = df_filtrado[df_filtrado['estatus_ticket'].isin(filtro_estatus_ticket)]
            if filtro_estatus_visita:
                df_filtrado = df_filtrado[df_filtrado['estatus_ultima_visita'].isin(filtro_estatus_visita)]
            if filtro_zona:
                df_filtrado = df_filtrado[df_filtrado['zona'].isin(filtro_zona)]

            col_btns1, col_btns2 = st.columns(2)
            with col_btns1:
                if st.button("🔍 Mostrar solo tickets sin visitas", width='stretch'):
                    df_filtrado = df_filtrado[df_filtrado['estatus_ultima_visita'] == 'Sin visita']
            with col_btns2:
                if st.button("🔄 Limpiar filtros", width='stretch'):
                    st.rerun()

            st.markdown(f"### 📋 Resultados ({len(df_filtrado)} tickets)")

            def formatear_estatus_ticket(estatus):
                return {"Abierto": "🟡 Abierto", "Programado": "🔵 Programado", "Cerrado": "✅ Cerrado"}.get(estatus, f"❓ {estatus}")

            def formatear_estatus_visita(estatus):
                mapa = {
                    'Sin visita': '📭 Sin visita',
                    'Sin programar': '⏰ Sin programar',
                    'Programado': '📅 Programado',
                    'Efectivo': '✅ Efectivo',
                    'Fallido': '❌ Fallido',
                    'Cancelado': '⚫ Cancelado'
                }
                return mapa.get(estatus, f"❓ {estatus}")

            df_display = df_filtrado.copy()
            df_display['estatus_ticket_formateado'] = df_display['estatus_ticket'].apply(formatear_estatus_ticket)
            df_display['estatus_visita_formateado'] = df_display['estatus_ultima_visita'].apply(formatear_estatus_visita)

            st.dataframe(
                df_display[['numero_ticket', 'id_equipo', 'estatus_ticket_formateado',
                            'estatus_visita_formateado', 'nombre_cliente', 'sucursal_atencion']],
                width='stretch', hide_index=True,
                column_config={
                    'numero_ticket': 'TICKET',
                    'id_equipo': 'ID EQUIPO',
                    'estatus_ticket_formateado': 'ESTATUS TICKET',
                    'estatus_visita_formateado': 'ESTATUS VISITA',
                    'nombre_cliente': 'CLIENTE',
                    'sucursal_atencion': 'SUCURSAL'
                }
            )

            st.markdown("---")
            col_export1, col_export2 = st.columns(2)
            with col_export1:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar a CSV",
                    data=csv,
                    file_name=f"todos_tickets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    width='stretch'
                )
            with col_export2:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_filtrado.to_excel(writer, sheet_name='Todos_Tickets', index=False)
                excel_data = output.getvalue()
                st.download_button(
                    label="📊 Exportar a Excel",
                    data=excel_data,
                    file_name=f"todos_tickets_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch'
                )

            with st.expander("📈 Ver estadísticas detalladas"):
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    estatus_counts = df_todos['estatus_ticket'].value_counts()
                    fig_estatus = px.pie(values=estatus_counts.values, names=estatus_counts.index, title="Tickets por Estatus")
                    st.plotly_chart(fig_estatus, width='stretch')
                with col_stat2:
                    visita_counts = df_todos['estatus_ultima_visita'].value_counts()
                    fig_visita = px.bar(x=visita_counts.index, y=visita_counts.values,
                                         title="Última Visita por Estatus", labels={'x': 'Estatus', 'y': 'Cantidad'})
                    fig_visita.update_layout(xaxis_tickangle=45)
                    st.plotly_chart(fig_visita, width='stretch')
                with col_stat3:
                    cliente_counts = df_todos['nombre_cliente'].value_counts().head(10)
                    fig_clientes = px.bar(x=cliente_counts.index, y=cliente_counts.values,
                                          title="Top 10 Clientes", labels={'x': 'Cliente', 'y': 'Número de Tickets'})
                    fig_clientes.update_layout(xaxis_tickangle=45)
                    st.plotly_chart(fig_clientes, width='stretch')

            with st.expander("🔍 Ver detalles completos de todos los campos"):
                st.dataframe(df_filtrado, width='stretch', hide_index=True)
        else:
            st.info("No hay tickets registrados en el sistema")