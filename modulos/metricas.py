import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db import db

def show_metricas():
    st.markdown('<h1 class="main-header">📈 Métricas de Desempeño y Reportes</h1>', unsafe_allow_html=True)

    with st.sidebar:
        st.subheader("⚙️ Configuración de Reportes")
        periodo = st.selectbox(
            "Período del Reporte",
            ["Últimos 7 días", "Últimos 30 días", "Este mes", "Mes anterior",
             "Este trimestre", "Personalizado"],
            key="periodo_selector"
        )
        if periodo == "Personalizado":
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=30))
            with col2:
                fecha_fin = st.date_input("Fecha fin", value=datetime.now())

    # Construir condiciones de fecha
    if periodo == "Últimos 7 días":
        condicion_fecha = "v.fecha_solicitud >= CURRENT_DATE - INTERVAL '7 days'"
        titulo_periodo = "Últimos 7 días"
    elif periodo == "Últimos 30 días":
        condicion_fecha = "v.fecha_solicitud >= CURRENT_DATE - INTERVAL '30 days'"
        titulo_periodo = "Últimos 30 días"
    elif periodo == "Este mes":
        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        condicion_fecha = f"EXTRACT(MONTH FROM v.fecha_solicitud) = {mes_actual} AND EXTRACT(YEAR FROM v.fecha_solicitud) = {año_actual}"
        titulo_periodo = f"Mes Actual ({datetime.now().strftime('%B %Y')})"
    elif periodo == "Mes anterior":
        mes_anterior = datetime.now().month - 1 if datetime.now().month > 1 else 12
        año = datetime.now().year if datetime.now().month > 1 else datetime.now().year - 1
        condicion_fecha = f"EXTRACT(MONTH FROM v.fecha_solicitud) = {mes_anterior} AND EXTRACT(YEAR FROM v.fecha_solicitud) = {año}"
        titulo_periodo = "Mes Anterior"
    elif periodo == "Este trimestre":
        trimestre_actual = (datetime.now().month - 1) // 3 + 1
        año_actual = datetime.now().year
        condicion_fecha = f"EXTRACT(QUARTER FROM v.fecha_solicitud) = {trimestre_actual} AND EXTRACT(YEAR FROM v.fecha_solicitud) = {año_actual}"
        titulo_periodo = f"Trimestre Actual (Q{trimestre_actual})"
    else:  # Personalizado
        condicion_fecha = f"v.fecha_solicitud >= '{fecha_inicio}' AND v.fecha_solicitud <= '{fecha_fin}'"
        titulo_periodo = f"Período Personalizado ({fecha_inicio} a {fecha_fin})"

    st.markdown(f'<h3 style="text-align: center; color: #667eea;">📅 Reporte: {titulo_periodo}</h3>', unsafe_allow_html=True)

    # KPIs principales
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
    if kpis_data and kpis_data[0]:
        kpis = kpis_data[0]
        total_efectivas_fallidas = kpis['visitas_efectivas'] + kpis['visitas_fallidas']
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

    # Desempeño por Zona
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
    if zonas_data:
        df_zonas = pd.DataFrame(zonas_data)
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Volumen de Visitas", "🎯 Efectividad", "⏱️ Tiempos", "📊 Gestión"])

        with tab1:
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
            st.plotly_chart(fig_volumen, width='stretch')

        with tab2:
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
            st.plotly_chart(fig_efectividad, width='stretch')

        with tab3:
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
            st.plotly_chart(fig_tiempos, width='stretch')

        with tab4:
            st.subheader("📊 Gestión")
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
                    AND v.fecha_solicitud >= CURRENT_DATE - INTERVAL '30 days'
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
                    fig_gestion.update_layout(title='Promedio de días por tipo de gestión (General)',
                                              xaxis_title="Zona", yaxis_title="Días Promedio", height=400, barmode='group')
                    st.plotly_chart(fig_gestion, width='stretch')
                else:
                    st.info("No hay datos de gestión general disponibles")
            else:
                st.info("No hay datos de gestión general disponibles")

    # Desempeño por Sucursal
    st.markdown("---")
    st.subheader("🏢 Desempeño por Sucursal")

    if zonas_data:
        zonas_lista = [z['zona'] for z in zonas_data]
        zonas_lista.insert(0, "Todas")
        zona_seleccionada = st.selectbox("Filtrar por Zona:", zonas_lista)
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
            # Aquí se pueden replicar las pestañas similares a las de zona, pero para sucursales
            # Por brevedad, se muestra una tabla resumen
            with st.expander("Ver detalle de sucursales"):
                df_detalle = df_sucursales.copy()
                df_detalle['efectividad'] = df_detalle.apply(
                    lambda row: f"{(row['efectivas']/(row['efectivas']+row['fallidas'])*100):.1f}%"
                    if (row['efectivas']+row['fallidas'])>0 else "0%", axis=1
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
                    hide_index=True, width='stretch'
                )
        else:
            st.info(f"No hay datos de sucursales para la zona {zona_seleccionada}")

    # Resumen ejecutivo
    st.markdown("---")
    st.subheader("👁️ Resumen Ejecutivo")

    if kpis_data and kpis_data[0]:
        kpis = kpis_data[0]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📋 Puntos Clave")
            if kpis['total_visitas'] > 0:
                efectividad = (kpis['visitas_efectivas'] / (kpis['visitas_efectivas'] + kpis['visitas_fallidas']) * 100) if (kpis['visitas_efectivas'] + kpis['visitas_fallidas']) > 0 else 0
                puntos = []
                if efectividad >= 90:
                    puntos.append(f"✅ **Excelente efectividad** ({efectividad:.1f}%)")
                elif efectividad >= 75:
                    puntos.append(f"👍 **Buena efectividad** ({efectividad:.1f}%)")
                else:
                    puntos.append(f"⚠️ **Efectividad a mejorar** ({efectividad:.1f}%)")
                if kpis['tiempo_respuesta_promedio'] and kpis['tiempo_respuesta_promedio'] <= 2:
                    puntos.append(f"✅ **Rápida respuesta** ({kpis['tiempo_respuesta_promedio']} días promedio)")
                elif kpis['tiempo_respuesta_promedio'] and kpis['tiempo_respuesta_promedio'] <= 4:
                    puntos.append(f"👍 **Respuesta aceptable** ({kpis['tiempo_respuesta_promedio']} días promedio)")
                else:
                    puntos.append(f"⚠️ **Respuesta lenta** ({kpis['tiempo_respuesta_promedio'] or 0} días promedio)")
                if kpis['visitas_en_proceso'] > 0:
                    porcentaje_en_proceso = (kpis['visitas_en_proceso'] / kpis['total_visitas']) * 100
                    puntos.append(f"📊 **{kpis['visitas_en_proceso']} visitas en proceso** ({porcentaje_en_proceso:.1f}% del total)")
                if zonas_data and len(zonas_data) > 0:
                    zona_top = df_zonas.iloc[0]
                    puntos.append(f"🏆 **Zona más activa**: {zona_top['zona']} con {zona_top['total_visitas']} visitas")
                for punto in puntos:
                    st.markdown(f"- {punto}")
        with col2:
            st.markdown("### 🎯 Recomendaciones")
            recomendaciones = []
            if kpis['visitas_fallidas'] > 0:
                tasa_fallos = (kpis['visitas_fallidas'] / (kpis['visitas_efectivas'] + kpis['visitas_fallidas'])) * 100 if (kpis['visitas_efectivas'] + kpis['visitas_fallidas']) > 0 else 0
                if tasa_fallos > 10:
                    recomendaciones.append("**Reducir visitas fallidas**: Implementar seguimiento adicional antes de las visitas")
            if kpis['tiempo_atencion_promedio'] and kpis['tiempo_atencion_promedio'] > 5:
                recomendaciones.append("**Optimizar tiempos de atención**: Revisar la programación de visitas")
            if zonas_data and len(zonas_data) > 1:
                zona_min_efectividad = None
                min_efectividad = 100
                for zona in zonas_data:
                    efectivas = zona['efectivas']
                    fallidas = zona['fallidas']
                    if (efectivas + fallidas) > 0:
                        efectividad_zona = (efectivas / (efectivas + fallidas)) * 100
                        if efectividad_zona < min_efectividad:
                            min_efectividad = efectividad_zona
                            zona_min_efectividad = zona['zona']
                if zona_min_efectividad and min_efectividad < 70:
                    recomendaciones.append(f"**Foco en zona {zona_min_efectividad}**: Efectividad del {min_efectividad:.1f}%")
            if kpis['visitas_en_proceso'] > 10:
                recomendaciones.append("**Revisar visitas en proceso**: Hay varias visitas pendientes de programación o cierre")
            if not recomendaciones:
                recomendaciones.append("✅ **Desempeño general satisfactorio** - Continuar con las prácticas actuales")
            for rec in recomendaciones:
                st.markdown(f"- {rec}")

    st.markdown("---")
    footer_cols = st.columns(4)
    with footer_cols[0]:
        st.caption(f"📅 Período: {titulo_periodo}")
    with footer_cols[1]:
        if kpis_data and kpis_data[0]:
            st.caption(f"📊 Total visitas: {kpis_data[0]['total_visitas']}")
    with footer_cols[2]:
        st.caption(f"🕒 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with footer_cols[3]:
        st.caption("© Sistema de Gestión de Visitas")