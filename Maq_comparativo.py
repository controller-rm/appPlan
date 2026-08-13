def subpage():    
    import streamlit as st
    import pandas as pd
    import mysql.connector
    import os
    from dotenv import load_dotenv
    import plotly.graph_objects as go
    from datetime import date, datetime
    from fpdf import FPDF
    import io
    import base64

    # ---------------- CONFIG ----------------
    st.set_page_config(layout="wide", page_title="C.Q. Liberação - Comparativo Máquinas", page_icon="📊")

    load_dotenv()

    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT"))
    database = os.getenv("MYSQL_DATABASE")
    username = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")

    # Códigos das máquinas envolvidas no comparativo
    MAQUINA_A = "6020"          # máquina de referência (sozinha)
    MAQUINAS_B = ["1008", "1009"]  # máquinas que formam o consolidado
    TODAS_MAQUINAS = [MAQUINA_A] + MAQUINAS_B


    # ---------------- CONEXÃO ----------------
    def connect_to_mysql():
        return mysql.connector.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database
        )


    def executar_query(query):
        conn = connect_to_mysql()
        df = pd.read_sql(query, conn)
        conn.close()
        return df


    # ---------------- QUERY ----------------
    placeholders = ",".join(["%s"] * len(TODAS_MAQUINAS))
    query = f"""
    SELECT
        h.nro_of,
        h.data_abertura,
        h.produto,
        h.equipamento,
        o.qtde,
        o.origem
    FROM HORAS_TRAB h
    LEFT JOIN ORDEM_FABRIC o
        ON o.nro_of = h.nro_of
    WHERE h.data_abertura IS NOT NULL
    AND h.equipamento IN ({placeholders})
    """


    def executar_query_maquinas(query, params):
        conn = connect_to_mysql()
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df


    df = executar_query_maquinas(query, TODAS_MAQUINAS)

    # ---------------- TRATAMENTO DE DADOS ----------------
    df["data_abertura"] = pd.to_datetime(df["data_abertura"], errors="coerce")
    df = df.dropna(subset=["data_abertura"])

    df["equipamento"] = df["equipamento"].astype(str).str.strip()

    df["origem"] = df["origem"].fillna("SEM_ORIGEM").astype(str).str.strip()
    mask_num = df["origem"].str.match(r"^\d+(\.0+)?$")
    df.loc[mask_num, "origem"] = (
        df.loc[mask_num, "origem"].astype(float).astype(int).astype(str)
    )
    df.loc[~mask_num, "origem"] = df.loc[~mask_num, "origem"].where(
        df.loc[~mask_num, "origem"] == "SEM_ORIGEM", "SEM_ORIGEM"
    )

    if df.empty:
        st.warning("Não há dados de HORAS_TRAB para os equipamentos 6020, 1008 e 1009.")
        st.stop()

    data_min = df["data_abertura"].min().date()
    data_max = df["data_abertura"].max().date()

    # ---------------- SIDEBAR - FILTROS ----------------
    st.sidebar.header("Filtros")

    hoje = datetime.now().date()
    inicio_padrao = max(date(hoje.year, hoje.month, 1), data_min)
    fim_padrao = min(data_max, hoje)
    if inicio_padrao > fim_padrao:
        inicio_padrao, fim_padrao = data_min, data_max

    periodo = st.sidebar.date_input(
        "Período",
        value=(inicio_padrao, fim_padrao),
        min_value=data_min,
        max_value=data_max,
        format="DD/MM/YYYY",
    )
    if isinstance(periodo, date):
        periodo = (periodo, periodo)

    origens = sorted(df["origem"].dropna().unique().tolist())
    origens_excluir = st.sidebar.multiselect(
        "Desconsiderar Origem",
        options=origens,
        key="origens_excluir_comparativo"
    )

    inicio_periodo = pd.to_datetime(periodo[0])
    fim_periodo = pd.to_datetime(periodo[1])

    # ---------------- APLICA FILTROS ----------------
    df_filtrado = df[
        (df["data_abertura"] >= inicio_periodo)
        & (df["data_abertura"] <= fim_periodo)
        & (~df["origem"].isin(origens_excluir))
    ].copy()

    # Remove duplicidade proveniente do LEFT JOIN com ORDEM_FABRIC
    # (mesma OF/produto pode repetir por múltiplas linhas em ORDEM_FABRIC)
    df_dedup = df_filtrado.drop_duplicates(subset=["equipamento", "nro_of", "produto"])

    # ---------------- CÁLCULO DOS TOTAIS ----------------
    def qtd_produtos(equipamento_codigo):
        return int(df_dedup[df_dedup["equipamento"] == equipamento_codigo].shape[0])


    qtd_6020 = qtd_produtos(MAQUINA_A)
    qtd_1008 = qtd_produtos("1008")
    qtd_1009 = qtd_produtos("1009")
    qtd_consolidado = qtd_1008 + qtd_1009  # soma direta, sem deduplicação entre máquinas

    # ---------------- CABEÇALHO ----------------
    st.title("📊 Relatório Comparativo - C.Q. Liberação")
    st.caption(
        f"Período analisado: {inicio_periodo.strftime('%d/%m/%Y')} a {fim_periodo.strftime('%d/%m/%Y')}"
    )

    # ---------------- TABELA NO FORMATO DA PLANILHA MODELO ----------------
    st.markdown("### Comparativo de Produtos Apontados")

    tabela_html = f"""
    <style>
    .tabela-cq {{
        border-collapse: collapse;
        width: 100%;
        text-align: center;
        font-family: Arial, sans-serif;
    }}
    .tabela-cq td, .tabela-cq th {{
        border: 1px solid #444;
        padding: 8px;
    }}
    .bloco-consolidado {{
        border: 3px solid black;
    }}
    </style>
    <table class="tabela-cq">
    <tr>
    <td style="width:16%"><b>DESCRITIVO</b></td>
    <td style="width:16%"><b>MAQUINA {MAQUINA_A}</b></td>
    <td class="bloco-consolidado" style="width:16%"><b>DESCRITIVO</b></td>
    <td class="bloco-consolidado" style="width:16%"><b>MAQUINA 1008</b></td>
    <td class="bloco-consolidado" style="width:16%"><b>MAQUINA 1009</b></td>
    <td class="bloco-consolidado" style="width:20%"><b>CONSOLIDADO 1008 E 1009</b></td>
    </tr>
    <tr>
    <td>QTD DE PRODUTOS</td>
    <td>{qtd_6020}</td>
    <td class="bloco-consolidado">QTD DE PRODUTOS</td>
    <td class="bloco-consolidado">{qtd_1008}</td>
    <td class="bloco-consolidado">{qtd_1009}</td>
    <td class="bloco-consolidado">{qtd_consolidado}</td>
    </tr>
    </table>
    """
    st.markdown(tabela_html, unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- GRÁFICO COMPARATIVO ----------------
    st.header("Gráfico Comparativo: Máquina 6020 x Consolidado 1008+1009")

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
        x=[f"Máquina {MAQUINA_A}", "Consolidado 1008+1009"],
        y=[qtd_6020, qtd_consolidado],
        text=[qtd_6020, qtd_consolidado],
        textposition="auto",
        marker=dict(color=["black", "orange"])
    ))
    fig_comp.update_layout(
        height=420,
        yaxis_title="Quantidade de Produtos Apontados",
        template="plotly_white"
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    # Gráfico auxiliar detalhando 1008 vs 1009
    st.header("Detalhamento: Máquina 1008 x Máquina 1009")
    fig_detalhe = go.Figure()
    fig_detalhe.add_trace(go.Bar(
        x=["Máquina 1008", "Máquina 1009"],
        y=[qtd_1008, qtd_1009],
        text=[qtd_1008, qtd_1009],
        textposition="auto",
        marker=dict(color=["#1f77b4", "#2ca02c"])
    ))
    fig_detalhe.update_layout(height=380, yaxis_title="Quantidade de Produtos", template="plotly_white")
    st.plotly_chart(fig_detalhe, use_container_width=True)

    st.markdown("---")

    # ---------------- CSV: TODOS OS PRODUTOS APONTADOS ----------------
    st.header("Exportação para Conferência")

    df_csv = df_dedup[["equipamento", "nro_of", "produto", "data_abertura", "qtde", "origem"]].sort_values(
        ["equipamento", "data_abertura", "nro_of"]
    )
    csv_bytes = df_csv.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")

    st.download_button(
        label="⬇️ Baixar CSV - Todos os Produtos Apontados",
        data=csv_bytes,
        file_name=f"produtos_apontados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

    st.dataframe(df_csv, use_container_width=True)


    # ---------------- FUNÇÃO PARA GERAR PDF ----------------
    def gerar_pdf():
        pdf = FPDF(orientation="L")
        pdf.set_auto_page_break(auto=True, margin=15)

        # ================= PÁGINA 1 =================
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Relatório Comparativo - C.Q. Liberação", ln=True, align="C")

        data_emissao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pdf.set_font("Arial", size=8)
        pdf.cell(0, 10, txt=f"Emitido em {data_emissao}", ln=True, align="R")

        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, f"Periodo analisado: {inicio_periodo.strftime('%d/%m/%Y')} a {fim_periodo.strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(2)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Comparativo de Produtos Apontados", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, f"Maquina {MAQUINA_A}: {qtd_6020} produtos", ln=True)
        pdf.cell(0, 8, f"Maquina 1008: {qtd_1008} produtos", ln=True)
        pdf.cell(0, 8, f"Maquina 1009: {qtd_1009} produtos", ln=True)
        pdf.cell(0, 8, f"Consolidado 1008 + 1009: {qtd_consolidado} produtos", ln=True)
        pdf.ln(4)

        fig_comp.write_image("fig_comp.png", width=1000, height=420)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Grafico Comparativo: Maquina 6020 x Consolidado 1008+1009", ln=True)
        pdf.image("fig_comp.png", x=10, w=270)

        # ================= PÁGINA 2 =================
        pdf.add_page()
        fig_detalhe.write_image("fig_detalhe.png", width=1000, height=380)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Detalhamento: Maquina 1008 x Maquina 1009", ln=True)
        pdf.image("fig_detalhe.png", x=10, w=270)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Regras de Analise", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(
            0,
            8,
            "1. A quantidade de produtos apontados considera pares distintos de OF e produto,\n"
            "   eliminando duplicidade gerada pelo cruzamento com ORDEM_FABRIC.\n"
            "2. O consolidado 1008+1009 e a soma direta das duas maquinas, sem deduplicacao entre elas.\n"
            "3. Os valores refletem o periodo e as origens selecionadas nos filtros."
        )

        conteudo_pdf = pdf.output(dest="S")
        pdf_bytes = (
            conteudo_pdf.encode("latin1")
            if isinstance(conteudo_pdf, str)
            else bytes(conteudo_pdf)
        )
        buffer = io.BytesIO(pdf_bytes)

        os.remove("fig_comp.png")
        os.remove("fig_detalhe.png")

        return buffer


    # ---------------- BOTÃO PARA GERAR PDF ----------------
    if st.button("Gerar PDF"):
        pdf_buffer = gerar_pdf()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"relatorio_comparativo_cq_{timestamp}.pdf"

        b64 = base64.b64encode(pdf_buffer.read()).decode()
        href = f'''
            <a href="data:application/pdf;base64,{b64}"
            download="{nome_arquivo}">
            Baixar PDF
            </a>
        '''
        st.markdown(href, unsafe_allow_html=True)

    # ---------------- OBSERVAÇÃO ----------------
    st.markdown("""
    **Regras para análise:**
    1. A quantidade de produtos apontados considera pares distintos de OF e produto, eliminando duplicidade gerada pelo cruzamento com ORDEM_FABRIC.
    2. O CONSOLIDADO 1008 E 1009 é a soma direta das duas máquinas, sem deduplicação entre elas.
    3. Os valores refletem o período e as origens selecionadas nos filtros da barra lateral.
    """)
