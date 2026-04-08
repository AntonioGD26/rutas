import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db import db
import io

def _generar_pdf(titulo_periodo, kpis, df_zonas, df_sucursales, figuras, top5_tickets):
    """Genera un reporte PDF con todas las gráficas y tablas."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Title'], fontSize=18, spaceAfter=12)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=14, spaceAfter=8, textColor=colors.HexColor('#667eea'))
    normal_style = styles['Normal']

    elements = []

    # Titulo
    elements.append(Paragraph(f"📊 Reporte de Métricas - {titulo_periodo}", titulo_style))
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Spacer(1, 20))

    # KPIs
    elements.append(Paragraph("KPIs Principales", subtitulo_style))
    if kpis:
        total_ef_fall = (kpis['visitas_efectivas'] or 0) + (kpis['visitas_fallidas'] or 0)
        efectividad = (kpis['visitas_efectivas'] / total_ef_fall * 100) if total_ef_fall > 0 else 0
        kpi_data = [
            ['Métrica', 'Valor'],
            ['Total Visitas', str(kpis['total_visitas'] or 0)],
            ['Efectividad', f"{efectividad:.1f}%"],
            ['En Proceso', str(kpis['visitas_en_proceso'] or 0)],
            ['Tiempo Respuesta Prom.', f"{kpis['tiempo_respuesta_promedio'] or 0:.1f} días"],
            ['Tiempo Atención Prom.', f"{kpis['tiempo_atencion_promedio'] or 0:.1f} días"],
            ['Visitas Fallidas', str(kpis['visitas_fallidas'] or 0)],
            ['Zonas Activas', str(kpis['zonas_activas'] or 0)],
            ['Sucursales Activas', str(kpis['sucursales_activas'] or 0)],
        ]
        t = Table(kpi_data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Gráficas como imágenes
    for nombre, fig in figuras:
        try:
            img_bytes = fig.to_image(format="png", width=900, height=400, scale=2)
            img_buffer = io.BytesIO(img_bytes)
            elements.append(Paragraph(nombre, subtitulo_style))
            elements.append(Image(img_buffer, width=8*inch, height=3.5*inch))
            elements.append(Spacer(1, 10))
        except Exception:
            elements.append(Paragraph(f"(No se pudo generar la gráfica: {nombre})", normal_style))

    elements.append(PageBreak())

    # Tabla de zonas
    if df_zonas is not None and not df_zonas.empty:
        elements.append(Paragraph("Detalle por Zona", subtitulo_style))
        zona_headers = ['Zona', 'Total Visitas', 'Efectivas', 'Fallidas', 'En Proceso', 'T. Resp. Prom.', 'T. Aten. Prom.']
        zona_data = [zona_headers]
        for _, row in df_zonas.iterrows():
            zona_data.append([
                str(row.get('zona', '')), str(row.get('total_visitas', 0)),
                str(row.get('efectivas', 0)), str(row.get('fallidas', 0)),
                str(row.get('en_proceso', 0)),
                f"{row.get('tiempo_respuesta_prom', 0) or 0:.1f}d",
                f"{row.get('tiempo_atencion_prom', 0) or 0:.1f}d"
            ])
        t = Table(zona_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Tabla de sucursales
    if df_sucursales is not None and not df_sucursales.empty:
        elements.append(Paragraph("Detalle por Sucursal", subtitulo_style))
        suc_headers = ['Sucursal', 'Zona', 'Total Visitas', 'Efectivas', 'Fallidas', 'T. Resp. Prom.', 'T. Aten. Prom.']
        suc_data = [suc_headers]
        for _, row in df_sucursales.iterrows():
            suc_data.append([
                str(row.get('sucursal_atencion', '')), str(row.get('zona', '')),
                str(row.get('total_visitas', 0)), str(row.get('efectivas', 0)),
                str(row.get('fallidas', 0)),
                f"{row.get('tiempo_respuesta_prom', 0) or 0:.1f}d",
                f"{row.get('tiempo_atencion_prom', 0) or 0:.1f}d"
            ])
        t = Table(suc_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Top 5 tickets con mayor tiempo de atención
    if top5_tickets is not None and len(top5_tickets) > 0:
        elements.append(Paragraph("Top 5 Tickets con Mayor Tiempo de Atención", subtitulo_style))
        top_headers = ['Ticket', 'Equipo', 'Cliente', 'Sucursal', 'Fecha Solicitud', 'Fecha Atención', 'Días']
        top_data = [top_headers]
        for t5 in top5_tickets:
            top_data.append([
                str(t5.get('numero_ticket', '')), str(t5.get('id_equipo', '')),
                str(t5.get('nombre_cliente', '')), str(t5.get('sucursal_atencion', '')),
                str(t5.get('fecha_solicitud', '')), str(t5.get('fecha_atencion', '')),
                str(t5.get('dias_atencion', ''))
            ])
        t = Table(top_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F44336')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def show_dashboard():
    st.markdown('<h1 class="main-header">📊 Dashboard — Métricas de Desempeño</h1>', unsafe_allow_html=True)

    # --- Filtro de período en sidebar ---
    with st.sidebar:
        st.subheader("⚙️ Configuración de Reportes")
        periodo = st.selectbox(
            "Período del Reporte",
            ["Últimos 7 días", "Últimos 30 días", "Este mes", "Mes anterior",
             "Este trimestre", "Personalizado"],
            key="periodo_selector"
        )
        fecha_inicio = None
        fecha_fin = None
        if periodo == "Personalizado":
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=30))
            with col2:
                fecha_fin = st.date_input("Fecha fin", value=datetime.now())

    # Construir condiciones de fecha — SIEMPRE por t.fecha_alta
    if periodo == "Últimos 7 días":
        condicion_fecha = "t.fecha_alta >= CURRENT_DATE - INTERVAL '7 days'"
        titulo_periodo = "Últimos 7 días"
    elif periodo == "Últimos 30 días":
        condicion_fecha = "t.fecha_alta >= CURRENT_DATE - INTERVAL '30 days'"
        titulo_periodo = "Últimos 30 días"
    elif periodo == "Este mes":
        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        condicion_fecha = f"EXTRACT(MONTH FROM t.fecha_alta) = {mes_actual} AND EXTRACT(YEAR FROM t.fecha_alta) = {año_actual}"
        titulo_periodo = f"Mes Actual ({datetime.now().strftime('%B %Y')})"
    elif periodo == "Mes anterior":
        mes_anterior = datetime.now().month - 1 if datetime.now().month > 1 else 12
        año = datetime.now().year if datetime.now().month > 1 else datetime.now().year - 1
        condicion_fecha = f"EXTRACT(MONTH FROM t.fecha_alta) = {mes_anterior} AND EXTRACT(YEAR FROM t.fecha_alta) = {año}"
        titulo_periodo = "Mes Anterior"
    elif periodo == "Este trimestre":
        trimestre_actual = (datetime.now().month - 1) // 3 + 1
        año_actual = datetime.now().year
        condicion_fecha = f"EXTRACT(QUARTER FROM t.fecha_alta) = {trimestre_actual} AND EXTRACT(YEAR FROM t.fecha_alta) = {año_actual}"
        titulo_periodo = f"Trimestre Actual (Q{trimestre_actual})"
    else:  # Personalizado
        condicion_fecha = f"t.fecha_alta >= '{fecha_inicio}' AND t.fecha_alta <= '{fecha_fin}'"
        titulo_periodo = f"Período Personalizado ({fecha_inicio} a {fecha_fin})"

    st.markdown(f'<h3 style="text-align: center; color: #667eea;">📅 Reporte: {titulo_periodo}</h3>', unsafe_allow_html=True)

    # =============================================
    # KPIs principales
    # =============================================
    st.markdown("---")
    st.subheader("📈 KPIs Principales")

    query_kpis = f"""
    WITH datos_periodo AS (
        SELECT 
            c.zona,
            c.sucursal_atencion,
            c.nombre_cliente,
            c.tipo_producto,
            v.id_visita,
            v.estatus,
            v.fecha_solicitud,
            v.fecha_respuesta,
            v.fecha_atencion,
            v.tiempo_respuesta,
            v.tiempo_atencion
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE {condicion_fecha}
    )
    SELECT 
        COUNT(*) as total_visitas,
        COUNT(CASE WHEN estatus = 'Efectivo' THEN 1 END) as visitas_efectivas,
        COUNT(CASE WHEN estatus = 'Fallido' THEN 1 END) as visitas_fallidas,
        COUNT(CASE WHEN estatus = 'Cancelado' THEN 1 END) as visitas_canceladas,
        COUNT(CASE WHEN estatus IN ('Sin programar', 'Programado') THEN 1 END) as visitas_en_proceso,
        ROUND(AVG(CASE WHEN estatus IN ('Programado', 'Efectivo', 'Fallido') AND fecha_respuesta IS NOT NULL THEN tiempo_respuesta END)::numeric, 1) as tiempo_respuesta_promedio,
        ROUND(AVG(CASE WHEN estatus IN ('Programado', 'Efectivo', 'Fallido') AND fecha_atencion IS NOT NULL THEN tiempo_atencion END)::numeric, 1) as tiempo_atencion_promedio,
        COUNT(DISTINCT zona) as zonas_activas,
        COUNT(DISTINCT sucursal_atencion) as sucursales_activas,
        COUNT(DISTINCT nombre_cliente) as clientes_activos
    FROM datos_periodo;
    """

    kpis_data = db.execute_query(query_kpis)
    kpis = None
    if kpis_data and kpis_data[0]:
        kpis = kpis_data[0]
        total_efectivas_fallidas = (kpis['visitas_efectivas'] or 0) + (kpis['visitas_fallidas'] or 0)
        efectividad = (kpis['visitas_efectivas'] / total_efectivas_fallidas * 100) if total_efectivas_fallidas > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Visitas", kpis['total_visitas'])
        with col2:
            st.metric("Efectividad", f"{efectividad:.1f}%")
        with col3:
            st.metric("En Proceso", kpis['visitas_en_proceso'])
        with col4:
            st.metric("Tiempo Respuesta Prom.", f"{kpis['tiempo_respuesta_promedio'] or 0:.1f} días")

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Tiempo Atención Prom.", f"{kpis['tiempo_atencion_promedio'] or 0:.1f} días")
        with col6:
            st.metric("Visitas Fallidas", kpis['visitas_fallidas'], delta_color="inverse")
        with col7:
            st.metric("Zonas Activas", kpis['zonas_activas'])
        with col8:
            st.metric("Sucursales Activas", kpis['sucursales_activas'])

    # =============================================
    # Desempeño por Zona
    # =============================================
    st.markdown("---")
    st.subheader("📊 Desempeño por Zona")

    query_zonas = f"""
    SELECT 
        c.zona,
        COUNT(*) as total_visitas,
        COUNT(CASE WHEN v.estatus = 'Efectivo' THEN 1 END) as efectivas,
        COUNT(CASE WHEN v.estatus = 'Fallido' THEN 1 END) as fallidas,
        COUNT(CASE WHEN v.estatus = 'Cancelado' THEN 1 END) as canceladas,
        COUNT(CASE WHEN v.estatus IN ('Sin programar', 'Programado') THEN 1 END) as en_proceso,
        ROUND(AVG(CASE WHEN v.estatus IN ('Programado', 'Efectivo', 'Fallido') AND v.fecha_respuesta IS NOT NULL THEN v.tiempo_respuesta END)::numeric, 1) as tiempo_respuesta_prom,
        ROUND(AVG(CASE WHEN v.estatus IN ('Programado', 'Efectivo', 'Fallido') AND v.fecha_atencion IS NOT NULL THEN v.tiempo_atencion END)::numeric, 1) as tiempo_atencion_prom
    FROM visitas v
    JOIN tickets t ON v.id_ticket = t.id_ticket
    JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
    WHERE {condicion_fecha}
    GROUP BY c.zona
    ORDER BY total_visitas DESC;
    """

    zonas_data = db.execute_query(query_zonas)
    df_zonas = None
    figuras_pdf = []  # Para PDF

    if zonas_data:
        df_zonas = pd.DataFrame(zonas_data)
        tab_z1, tab_z2, tab_z3, tab_z4 = st.tabs(["📈 Volumen de Visitas", "🎯 Efectividad", "⏱️ Tiempos", "📊 Gestión"])

        with tab_z1:
            fig_volumen = go.Figure()
            colores = {'en_proceso': '#FFC107', 'efectivas': '#4CAF50', 'fallidas': '#F44336', 'canceladas': '#9E9E9E'}
            orden_barras = ['en_proceso', 'efectivas', 'fallidas', 'canceladas']
            nombres_legenda = {'en_proceso': 'En proceso', 'efectivas': 'Efectivas', 'fallidas': 'Fallidas', 'canceladas': 'Canceladas'}
            for resultado in orden_barras:
                fig_volumen.add_trace(go.Bar(
                    x=df_zonas['zona'], y=df_zonas[resultado], name=nombres_legenda[resultado],
                    marker_color=colores[resultado], text=df_zonas[resultado], textposition='inside'
                ))
            fig_volumen.update_layout(title=f'Visitas por Zona - {titulo_periodo}', barmode='stack',
                                      xaxis_title="Zona", yaxis_title="Número de Visitas", height=400)
            st.plotly_chart(fig_volumen, use_container_width=True)
            figuras_pdf.append(("Volumen de Visitas por Zona", fig_volumen))

        with tab_z2:
            df_zonas['efectividad'] = df_zonas.apply(
                lambda row: (row['efectivas'] / (row['efectivas'] + row['fallidas']) * 100)
                if (row['efectivas'] + row['fallidas']) > 0 else 0, axis=1
            )
            fig_efectividad = px.bar(
                df_zonas, x='zona', y='efectividad', title=f'Efectividad por Zona - {titulo_periodo}',
                color='efectividad', color_continuous_scale='RdYlGn', range_color=[0, 100],
                text=df_zonas['efectividad'].apply(lambda x: f'{x:.1f}%')
            )
            fig_efectividad.update_layout(xaxis_title="Zona", yaxis_title="Efectividad (%)", height=400, yaxis_range=[0, 100])
            st.plotly_chart(fig_efectividad, use_container_width=True)
            figuras_pdf.append(("Efectividad por Zona", fig_efectividad))

        with tab_z3:
            fig_tiempos = go.Figure()
            fig_tiempos.add_trace(go.Bar(
                x=df_zonas['zona'], y=df_zonas['tiempo_respuesta_prom'], name='Tiempo Respuesta Prom.',
                marker_color='#2196F3', text=df_zonas['tiempo_respuesta_prom'].apply(lambda x: f'{x:.1f}d' if pd.notnull(x) else 'N/A'),
                textposition='outside'
            ))
            fig_tiempos.add_trace(go.Bar(
                x=df_zonas['zona'], y=df_zonas['tiempo_atencion_prom'], name='Tiempo Atención Prom.',
                marker_color='#9C27B0', text=df_zonas['tiempo_atencion_prom'].apply(lambda x: f'{x:.1f}d' if pd.notnull(x) else 'N/A'),
                textposition='outside'
            ))
            fig_tiempos.update_layout(title=f'Tiempos Promedio por Zona - {titulo_periodo}',
                                      xaxis_title="Zona", yaxis_title="Días Promedio", height=400, barmode='group')
            st.plotly_chart(fig_tiempos, use_container_width=True)
            figuras_pdf.append(("Tiempos Promedio por Zona", fig_tiempos))

        with tab_z4:
            st.subheader("📊 Gestión")
            # Corregido: filtra por t.fecha_alta en vez de v.fecha_solicitud
            query_gestion_general = f"""
            WITH tickets_gest AS (
                SELECT 
                    c.zona,
                    t.id_ticket,
                    t.fecha_alta,
                    t.fecha_cierre,
                    SUM(CASE WHEN v.estatus IN ('Efectivo', 'Fallido') AND v.fecha_atencion IS NOT NULL 
                        THEN v.tiempo_atencion ELSE 0 END) as suma_tiempo_atencion
                FROM tickets t
                JOIN visitas v ON t.id_ticket = v.id_ticket
                JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
                WHERE t.estatus_ticket = 'Cerrado'
                    AND t.fecha_cierre IS NOT NULL
                    AND {condicion_fecha}
                    AND EXISTS (
                        SELECT 1 FROM visitas v3 
                        WHERE v3.id_ticket = t.id_ticket 
                        AND v3.estatus IN ('Efectivo', 'Fallido')
                    )
                GROUP BY c.zona, t.id_ticket, t.fecha_alta, t.fecha_cierre
            )
            SELECT 
                zona,
                ROUND(AVG(fecha_cierre - fecha_alta)::numeric, 1) as promedio_dias_alta_cierre,
                ROUND(AVG(suma_tiempo_atencion)::numeric, 1) as promedio_dias_gestion,
                COUNT(*) as total_tickets
            FROM tickets_gest
            GROUP BY zona
            ORDER BY zona;
            """
            gestion_general_data = db.execute_query(query_gestion_general)
            if gestion_general_data:
                df_gestion = pd.DataFrame(gestion_general_data)
                if not df_gestion.empty:
                    fig_gestion = go.Figure()
                    fig_gestion.add_trace(go.Bar(
                        x=df_gestion['zona'], y=df_gestion['promedio_dias_alta_cierre'],
                        name='Alta a Cierre', marker_color='#4CAF50',
                        text=df_gestion['promedio_dias_alta_cierre'].apply(lambda x: f'{x:.1f}d'), textposition='outside'
                    ))
                    fig_gestion.add_trace(go.Bar(
                        x=df_gestion['zona'], y=df_gestion['promedio_dias_gestion'],
                        name='Gestión Visitas', marker_color='#2196F3',
                        text=df_gestion['promedio_dias_gestion'].apply(lambda x: f'{x:.1f}d'), textposition='outside'
                    ))
                    fig_gestion.update_layout(title=f'Promedio de días por tipo de gestión - {titulo_periodo}',
                                              xaxis_title="Zona", yaxis_title="Días Promedio", height=400, barmode='group')
                    st.plotly_chart(fig_gestion, use_container_width=True)
                    figuras_pdf.append(("Gestión por Zona", fig_gestion))
                else:
                    st.info("No hay datos de gestión general disponibles")
            else:
                st.info("No hay datos de gestión general disponibles")

        # Tabla desplegable "Ver detalle de zonas"
        with st.expander("📋 Ver detalle de zonas"):
            df_zona_detalle = df_zonas.copy()
            if 'efectividad' not in df_zona_detalle.columns:
                df_zona_detalle['efectividad'] = df_zona_detalle.apply(
                    lambda row: f"{(row['efectivas']/(row['efectivas']+row['fallidas'])*100):.1f}%"
                    if (row['efectivas']+row['fallidas']) > 0 else "0%", axis=1
                )
            else:
                df_zona_detalle['efectividad'] = df_zona_detalle['efectividad'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(
                df_zona_detalle[['zona', 'total_visitas', 'en_proceso',
                            'efectivas', 'fallidas', 'canceladas', 'efectividad',
                            'tiempo_respuesta_prom', 'tiempo_atencion_prom']],
                column_config={
                    'zona': 'Zona', 'total_visitas': 'Total Visitas',
                    'en_proceso': 'En Proceso', 'efectivas': 'Efectivas', 'fallidas': 'Fallidas',
                    'canceladas': 'Canceladas', 'efectividad': 'Efectividad',
                    'tiempo_respuesta_prom': 'Respuesta Prom. (días)',
                    'tiempo_atencion_prom': 'Atención Prom. (días)',
                },
                hide_index=True, use_container_width=True
            )

    # =============================================
    # Desempeño por Sucursal
    # =============================================
    st.markdown("---")
    st.subheader("🏢 Desempeño por Sucursal")

    df_sucursales = None
    if zonas_data:
        zonas_lista = [z['zona'] for z in zonas_data]
        zonas_lista.insert(0, "Todas")
        zona_seleccionada = st.selectbox("Filtrar por Zona:", zonas_lista, key="filtro_zona_sucursal")
        condicion_zona = "" if zona_seleccionada == "Todas" else f"AND c.zona = '{zona_seleccionada}'"

        query_sucursales = f"""
        SELECT 
            c.sucursal_atencion,
            c.zona,
            COUNT(*) as total_visitas,
            COUNT(CASE WHEN v.estatus = 'Efectivo' THEN 1 END) as efectivas,
            COUNT(CASE WHEN v.estatus = 'Fallido' THEN 1 END) as fallidas,
            COUNT(CASE WHEN v.estatus = 'Cancelado' THEN 1 END) as canceladas,
            COUNT(CASE WHEN v.estatus IN ('Sin programar', 'Programado') THEN 1 END) as en_proceso,
            ROUND(AVG(CASE WHEN v.estatus IN ('Programado', 'Efectivo', 'Fallido') AND v.fecha_respuesta IS NOT NULL THEN v.tiempo_respuesta END)::numeric, 1) as tiempo_respuesta_prom,
            ROUND(AVG(CASE WHEN v.estatus IN ('Programado', 'Efectivo', 'Fallido') AND v.fecha_atencion IS NOT NULL THEN v.tiempo_atencion END)::numeric, 1) as tiempo_atencion_prom,
            COUNT(DISTINCT c.nombre_cliente) as clientes_unicos
        FROM visitas v
        JOIN tickets t ON v.id_ticket = t.id_ticket
        JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
        WHERE {condicion_fecha}
            {condicion_zona}
        GROUP BY c.sucursal_atencion, c.zona
        ORDER BY total_visitas DESC
        LIMIT 20;
        """
        sucursales_data = db.execute_query(query_sucursales)
        if sucursales_data:
            df_sucursales = pd.DataFrame(sucursales_data)

            # Gráficas de sucursal (idénticas a las de zona)
            tab_s1, tab_s2, tab_s3, tab_s4 = st.tabs(["📈 Volumen", "🎯 Efectividad", "⏱️ Tiempos", "📊 Gestión"])

            with tab_s1:
                fig_vol_suc = go.Figure()
                colores = {'en_proceso': '#FFC107', 'efectivas': '#4CAF50', 'fallidas': '#F44336', 'canceladas': '#9E9E9E'}
                for resultado in ['en_proceso', 'efectivas', 'fallidas', 'canceladas']:
                    nombres = {'en_proceso': 'En proceso', 'efectivas': 'Efectivas', 'fallidas': 'Fallidas', 'canceladas': 'Canceladas'}
                    fig_vol_suc.add_trace(go.Bar(
                        x=df_sucursales['sucursal_atencion'], y=df_sucursales[resultado],
                        name=nombres[resultado], marker_color=colores[resultado],
                        text=df_sucursales[resultado], textposition='inside'
                    ))
                fig_vol_suc.update_layout(title=f'Visitas por Sucursal - {titulo_periodo}', barmode='stack',
                                          xaxis_title="Sucursal", yaxis_title="Número de Visitas", height=400)
                fig_vol_suc.update_xaxes(tickangle=45)
                st.plotly_chart(fig_vol_suc, use_container_width=True)
                figuras_pdf.append(("Volumen de Visitas por Sucursal", fig_vol_suc))

            with tab_s2:
                df_sucursales['efectividad'] = df_sucursales.apply(
                    lambda row: (row['efectivas'] / (row['efectivas'] + row['fallidas']) * 100)
                    if (row['efectivas'] + row['fallidas']) > 0 else 0, axis=1
                )
                fig_ef_suc = px.bar(
                    df_sucursales, x='sucursal_atencion', y='efectividad',
                    title=f'Efectividad por Sucursal - {titulo_periodo}',
                    color='efectividad', color_continuous_scale='RdYlGn', range_color=[0, 100],
                    text=df_sucursales['efectividad'].apply(lambda x: f'{x:.1f}%')
                )
                fig_ef_suc.update_layout(xaxis_title="Sucursal", yaxis_title="Efectividad (%)", height=400, yaxis_range=[0, 100])
                fig_ef_suc.update_xaxes(tickangle=45)
                st.plotly_chart(fig_ef_suc, use_container_width=True)
                figuras_pdf.append(("Efectividad por Sucursal", fig_ef_suc))

            with tab_s3:
                fig_t_suc = go.Figure()
                fig_t_suc.add_trace(go.Bar(
                    x=df_sucursales['sucursal_atencion'], y=df_sucursales['tiempo_respuesta_prom'],
                    name='Tiempo Respuesta Prom.', marker_color='#2196F3',
                    text=df_sucursales['tiempo_respuesta_prom'].apply(lambda x: f'{x:.1f}d' if pd.notnull(x) else 'N/A'),
                    textposition='outside'
                ))
                fig_t_suc.add_trace(go.Bar(
                    x=df_sucursales['sucursal_atencion'], y=df_sucursales['tiempo_atencion_prom'],
                    name='Tiempo Atención Prom.', marker_color='#9C27B0',
                    text=df_sucursales['tiempo_atencion_prom'].apply(lambda x: f'{x:.1f}d' if pd.notnull(x) else 'N/A'),
                    textposition='outside'
                ))
                fig_t_suc.update_layout(title=f'Tiempos Promedio por Sucursal - {titulo_periodo}',
                                        xaxis_title="Sucursal", yaxis_title="Días Promedio", height=400, barmode='group')
                fig_t_suc.update_xaxes(tickangle=45)
                st.plotly_chart(fig_t_suc, use_container_width=True)
                figuras_pdf.append(("Tiempos Promedio por Sucursal", fig_t_suc))

            with tab_s4:
                # Gestión por Sucursal
                query_gestion_suc = f"""
                WITH tickets_gest AS (
                    SELECT 
                        c.sucursal_atencion,
                        t.id_ticket,
                        t.fecha_alta,
                        t.fecha_cierre,
                        SUM(CASE WHEN v.estatus IN ('Efectivo', 'Fallido') AND v.fecha_atencion IS NOT NULL 
                            THEN v.tiempo_atencion ELSE 0 END) as suma_tiempo_atencion
                    FROM tickets t
                    JOIN visitas v ON t.id_ticket = v.id_ticket
                    JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
                    WHERE t.estatus_ticket = 'Cerrado'
                        AND t.fecha_cierre IS NOT NULL
                        AND {condicion_fecha}
                        {condicion_zona}
                        AND EXISTS (
                            SELECT 1 FROM visitas v3 
                            WHERE v3.id_ticket = t.id_ticket 
                            AND v3.estatus IN ('Efectivo', 'Fallido')
                        )
                    GROUP BY c.sucursal_atencion, t.id_ticket, t.fecha_alta, t.fecha_cierre
                )
                SELECT 
                    sucursal_atencion,
                    ROUND(AVG(fecha_cierre - fecha_alta)::numeric, 1) as promedio_dias_alta_cierre,
                    ROUND(AVG(suma_tiempo_atencion)::numeric, 1) as promedio_dias_gestion,
                    COUNT(*) as total_tickets
                FROM tickets_gest
                GROUP BY sucursal_atencion
                ORDER BY sucursal_atencion;
                """
                gestion_suc_data = db.execute_query(query_gestion_suc)
                if gestion_suc_data:
                    df_gest_suc = pd.DataFrame(gestion_suc_data)
                    if not df_gest_suc.empty:
                        fig_gest_suc = go.Figure()
                        fig_gest_suc.add_trace(go.Bar(
                            x=df_gest_suc['sucursal_atencion'], y=df_gest_suc['promedio_dias_alta_cierre'],
                            name='Alta a Cierre', marker_color='#4CAF50',
                            text=df_gest_suc['promedio_dias_alta_cierre'].apply(lambda x: f'{x:.1f}d'), textposition='outside'
                        ))
                        fig_gest_suc.add_trace(go.Bar(
                            x=df_gest_suc['sucursal_atencion'], y=df_gest_suc['promedio_dias_gestion'],
                            name='Gestión Visitas', marker_color='#2196F3',
                            text=df_gest_suc['promedio_dias_gestion'].apply(lambda x: f'{x:.1f}d'), textposition='outside'
                        ))
                        fig_gest_suc.update_layout(title=f'Gestión por Sucursal - {titulo_periodo}',
                                                    xaxis_title="Sucursal", yaxis_title="Días Promedio", height=400, barmode='group')
                        fig_gest_suc.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_gest_suc, use_container_width=True)
                        figuras_pdf.append(("Gestión por Sucursal", fig_gest_suc))
                    else:
                        st.info("No hay datos de gestión por sucursal disponibles")
                else:
                    st.info("No hay datos de gestión por sucursal disponibles")

            # Tabla desplegable de sucursales
            with st.expander("📋 Ver detalle de sucursales"):
                df_detalle = df_sucursales.copy()
                if 'efectividad' in df_detalle.columns and df_detalle['efectividad'].dtype != object:
                    df_detalle['efectividad'] = df_detalle['efectividad'].apply(lambda x: f"{x:.1f}%")
                elif 'efectividad' not in df_detalle.columns:
                    df_detalle['efectividad'] = df_detalle.apply(
                        lambda row: f"{(row['efectivas']/(row['efectivas']+row['fallidas'])*100):.1f}%"
                        if (row['efectivas']+row['fallidas']) > 0 else "0%", axis=1
                    )
                st.dataframe(
                    df_detalle[['sucursal_atencion', 'zona', 'total_visitas', 'en_proceso',
                                'efectivas', 'fallidas', 'canceladas', 'efectividad',
                                'tiempo_respuesta_prom', 'tiempo_atencion_prom', 'clientes_unicos']],
                    column_config={
                        'sucursal_atencion': 'Sucursal', 'zona': 'Zona', 'total_visitas': 'Total Visitas',
                        'en_proceso': 'En Proceso', 'efectivas': 'Efectivas', 'fallidas': 'Fallidas',
                        'canceladas': 'Canceladas', 'efectividad': 'Efectividad',
                        'tiempo_respuesta_prom': 'Respuesta Prom. (días)',
                        'tiempo_atencion_prom': 'Atención Prom. (días)',
                        'clientes_unicos': 'Clientes Únicos'
                    },
                    hide_index=True, use_container_width=True
                )
        else:
            st.info(f"No hay datos de sucursales para la zona {zona_seleccionada}")

    # =============================================
    # Generación de Reporte PDF
    # =============================================
    st.markdown("---")
    st.subheader("📄 Generar Reporte PDF")

    # Top 5 tickets con mayor tiempo de atención
    query_top5 = f"""
    SELECT 
        t.numero_ticket,
        t.id_equipo,
        c.nombre_cliente,
        c.sucursal_atencion,
        v.fecha_solicitud,
        v.fecha_atencion,
        (v.fecha_atencion - v.fecha_solicitud) as dias_atencion
    FROM visitas v
    JOIN tickets t ON v.id_ticket = t.id_ticket
    JOIN catalogo_equipos c ON t.id_equipo = c.id_equipo
    WHERE {condicion_fecha}
        AND t.estatus_ticket != 'Cancelado'
        AND v.fecha_atencion IS NOT NULL
        AND v.fecha_solicitud IS NOT NULL
        AND v.estatus NOT IN ('Cancelado')
    ORDER BY (v.fecha_atencion - v.fecha_solicitud) DESC
    LIMIT 5;
    """
    top5_data = db.execute_query(query_top5)

    if top5_data:
        with st.expander("🏆 Top 5 Tickets con Mayor Tiempo de Atención"):
            df_top5 = pd.DataFrame(top5_data)
            st.dataframe(
                df_top5,
                column_config={
                    'numero_ticket': 'Ticket', 'id_equipo': 'Equipo',
                    'nombre_cliente': 'Cliente', 'sucursal_atencion': 'Sucursal',
                    'fecha_solicitud': 'Fecha Solicitud', 'fecha_atencion': 'Fecha Atención',
                    'dias_atencion': 'Días de Atención'
                },
                hide_index=True, use_container_width=True
            )

    if st.button("📄 Generar Reporte PDF", type="primary", use_container_width=True):
        with st.spinner("Generando reporte PDF..."):
            try:
                pdf_buffer = _generar_pdf(
                    titulo_periodo, kpis, df_zonas, df_sucursales,
                    figuras_pdf, top5_data
                )
                st.download_button(
                    label="📥 Descargar Reporte PDF",
                    data=pdf_buffer,
                    file_name=f"reporte_metricas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ Reporte PDF generado exitosamente!")
            except Exception as e:
                st.error(f"❌ Error al generar PDF: {str(e)}")
                st.info("💡 Asegúrese de tener instaladas las dependencias: `pip install reportlab kaleido`")

    # Footer
    st.markdown("---")
    footer_cols = st.columns(4)
    with footer_cols[0]:
        st.caption(f"📅 Período: {titulo_periodo}")
    with footer_cols[1]:
        if kpis:
            st.caption(f"📊 Total visitas: {kpis['total_visitas']}")
    with footer_cols[2]:
        st.caption(f"🕒 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with footer_cols[3]:
        st.caption("© Sistema de Gestión de Visitas")