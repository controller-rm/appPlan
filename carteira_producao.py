def subpage():
    import os
    import pandas as pd
    import streamlit as st
    import mysql.connector
    from dotenv import load_dotenv
    from datetime import date


    from io import BytesIO
    from datetime import date, datetime

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        PageBreak
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont




    st.set_page_config(
        page_title="Carteira x Estoque ALMOX x OF",
        layout="wide"
    )

    st.title("📦 Carteira de Pedidos x Estoque ALMOX x Ordem de Fabricação")

    load_dotenv()

    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", 3306))
    database = os.getenv("MYSQL_DATABASE")
    username = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")


    def connect_to_mysql():
        try:
            return mysql.connector.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database
            )
        except mysql.connector.Error as e:
            st.error(f"Erro ao conectar ao MySQL: {e}")
            return None

    def br_numero(valor, casas=2):
        try:
            valor = float(valor)
            return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00"


    def br_data(data):
        try:
            return pd.to_datetime(data).strftime("%d/%m/%Y")
        except Exception:
            return ""


    def registrar_fonte_pdf():
        try:
            pdfmetrics.registerFont(
                TTFont("DejaVu", "C:/Windows/Fonts/arial.ttf")
            )
            return "DejaVu"
        except Exception:
            return "Helvetica"


    def cabecalho_rodape(canvas, doc, titulo, periodo, gerado_em, usuario):
        canvas.saveState()

        largura, altura = landscape(A4)

        canvas.setFillColor(colors.HexColor("#1f4e79"))
        canvas.rect(0, altura - 2.2 * cm, largura, 2.2 * cm, fill=True, stroke=False)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(1.2 * cm, altura - 0.9 * cm, "")

        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(1.2 * cm, altura - 1.5 * cm, titulo)

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(largura - 1.2 * cm, altura - 0.9 * cm, f"Periodo Fechamento: {periodo}")
        canvas.drawRightString(largura - 1.2 * cm, altura - 1.35 * cm, f"Gerado em: {gerado_em}")
        canvas.drawRightString(largura - 1.2 * cm, altura - 1.8 * cm, f"Por: {usuario}")

        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(1.2 * cm, 0.8 * cm, "Controladoria Remota")
        canvas.drawRightString(largura - 1.2 * cm, 0.8 * cm, f"Pagina {doc.page}")

        canvas.restoreState()


    def tabela_card_pdf(titulo, df_base):
        qtd_of = df_base["nro_of"].nunique() if not df_base.empty else 0
        qtd_kg = df_base["qtd_kg_relatorio"].sum() if not df_base.empty else 0

        dados = [
            [titulo],
            ["QTD OF", "QTD KG"],
            [f"{qtd_of:,.0f}", br_numero(qtd_kg)]
        ]

        tabela = Table(dados, colWidths=[6.4 * cm, 6.4 * cm])

        tabela.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))

        return tabela


    def gerar_pdf_of_estoque(
        data_ini,
        data_fim,
        fechadas_com,
        fechadas_sem,
        andamento_com,
        andamento_sem,
        df_auditoria
    ):
        buffer = BytesIO()

        titulo = "RELATORIO OF x ESTOQUE MINIMO"
        periodo = f"{data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}"
        gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        usuario = "Controladoria Remota"

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1.2 * cm,
            leftMargin=1.2 * cm,
            topMargin=2.8 * cm,
            bottomMargin=1.5 * cm
        )

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            "TituloSecao",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            alignment=1,
            spaceAfter=8
        )

        elementos = []

        elementos.append(Paragraph("OF FECHADAS NO PERIODO", estilo_titulo))

        tabela_fechadas = Table(
            [[
                tabela_card_pdf("Produtos Produzido Estoque minimo", fechadas_com),
                tabela_card_pdf("Produtos Produzido S/ Estoque minimo", fechadas_sem)
            ]],
            colWidths=[
        12.9*cm,
        12.9*cm
    ]
        )

        tabela_fechadas.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))

        elementos.append(tabela_fechadas)
        elementos.append(Spacer(1, 0.8 * cm))

        elementos.append(Paragraph("OF EM ANDAMENTO", estilo_titulo))

        tabela_andamento = Table(
            [[
                tabela_card_pdf("Produtos Produzido Estoque minimo", andamento_com),
                tabela_card_pdf("Produtos Produzido S/ Estoque minimo", andamento_sem)
            ]],
            colWidths=[
        12.9*cm,
        12.9*cm
    ]
        )

        tabela_andamento.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))

        elementos.append(tabela_andamento)

        elementos.append(PageBreak())
        elementos.append(Paragraph("BASE DE AUDITORIA", estilo_titulo))

        colunas_pdf = [
            "grupo_of",
            "tipo_estoque_minimo",
            "nro_of",
            "produto",
            "status_of",
            "data_abertura",
            "data_fechamento",
            "qtde",
            "qtde_produzida",
            "qtd_kg_relatorio",
            "estoque_minimo"
        ]

        df_pdf = df_auditoria[colunas_pdf].copy()

        for col in ["data_abertura", "data_fechamento"]:
            df_pdf[col] = df_pdf[col].apply(br_data)

        for col in ["qtde", "qtde_produzida", "qtd_kg_relatorio", "estoque_minimo"]:
            df_pdf[col] = df_pdf[col].apply(lambda x: br_numero(x))

        dados_tabela = [colunas_pdf] + df_pdf.astype(str).values.tolist()

        tabela_auditoria = Table(
            dados_tabela,
            repeatRows=1,
            colWidths=[
                3.2 * cm,
                4.2 * cm,
                2.4 * cm,
                2.2 * cm,
                1.5 * cm,
                2.2 * cm,
                2.2 * cm,
                2.0 * cm,
                2.2 * cm,
                2.4 * cm,
                2.2 * cm
            ]
        )

        tabela_auditoria.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
        ]))

        elementos.append(tabela_auditoria)

        doc.build(
            elementos,
            onFirstPage=lambda canvas, doc: cabecalho_rodape(
                canvas, doc, titulo, periodo, gerado_em, usuario
            ),
            onLaterPages=lambda canvas, doc: cabecalho_rodape(
                canvas, doc, titulo, periodo, gerado_em, usuario
            )
        )

        pdf = buffer.getvalue()
        buffer.close()

        return pdf

    def gerar_csv(df_csv):
        return df_csv.to_csv(
            index=False,
            sep=";",
            decimal=","
        ).encode("utf-8-sig")


    def formatar_numero(valor, casas=2):
        try:
            return f"{float(valor):,.{casas}f}"
        except Exception:
            return "0,00"


    @st.cache_data(ttl=300)
    def carregar_dados():
        conn = connect_to_mysql()

        if conn is None:
            return pd.DataFrame()

        sql = """
        WITH carteira AS (
            SELECT
                c.numero_pedido,
                c.sequencia_pedido AS item_pedido,
                c.cod_produto,
                c.produto AS produto_pedido,
                c.desc_produto,
                SUBSTRING_INDEX(c.cod_produto, '.', 1) AS produto_join_of,
                c.ped_prod_int,
                c.situacao_pedido,
                c.situacao_item,
                c.desc_cliente,
                c.cod_cliente,
                c.cidade_cliente,
                c.uf_cliente,
                c.regiao_cliente,
                c.vendedor,
                c.vendedor_interno,
                c.data_pedido,
                c.data_previsao_entrega,
                c.quantidade_pedida,
                c.quantidade_atendida,
                c.quantidade_pronta,
                c.valor_total_item,
                c.valor_unitario,
                c.quantidade_pedida - c.quantidade_atendida AS saldo_pendente
            FROM CARTEIRA_PEDIDOS c
            WHERE c.situacao_pedido NOT IN (
                '8-Orcamento',
                '9-Cancelado',
                '3-Atendido Total',
                '7-Provisório'
            )
            AND c.situacao_item NOT IN (
                '6-Atendido Total',
                '9-Cancelado'
            )
            AND (c.quantidade_pedida - c.quantidade_atendida) > 0
            AND CAST(c.cme AS UNSIGNED) = 210
        ),

        estoque AS (
            SELECT
                p.produto,
                SUM(p.quantidade) AS estoque_total,
                SUM(p.qtde_reservada) AS estoque_reservado,
                SUM(p.quantidade - p.qtde_reservada) AS estoque_disponivel
            FROM POSICAO_ESTOQUE_ATUAL p
            WHERE p.deposito = 'ALMOX'
            GROUP BY p.produto
        ),

        ordem_fabric AS (
            SELECT
                o.produto,
                SUM(o.qtde) AS qtde_of_aberta
            FROM ORDEM_FABRIC o
            WHERE o.status_of = 'A'
            AND o.sub_grupo NOT IN (1, 3, 16)
            AND o.grupo NOT IN (801,800)
            AND o.origem NOT IN (997)
            GROUP BY o.produto
        )

        SELECT
            c.numero_pedido,
            c.item_pedido,
            c.cod_produto,
            c.produto_pedido,
            c.desc_produto,
            c.produto_join_of,
            c.ped_prod_int,
            c.desc_cliente,
            c.cod_cliente,
            c.cidade_cliente,
            c.uf_cliente,
            c.regiao_cliente,
            c.vendedor,
            c.vendedor_interno,
            c.situacao_pedido,
            c.situacao_item,
            c.data_pedido,
            c.data_previsao_entrega,
            c.quantidade_pedida,
            c.quantidade_atendida,
            c.quantidade_pronta,
            c.saldo_pendente,
            COALESCE(e.estoque_total, 0) AS estoque_total_almox,
            COALESCE(e.estoque_reservado, 0) AS estoque_reservado_almox,
            COALESCE(e.estoque_disponivel, 0) AS estoque_disponivel_almox,
            COALESCE(o.qtde_of_aberta, 0) AS qtde_of_aberta,
            COALESCE(e.estoque_disponivel, 0) + COALESCE(o.qtde_of_aberta, 0) AS cobertura_total,
            c.valor_unitario,
            c.valor_total_item
        FROM carteira c
        LEFT JOIN estoque e
            ON e.produto = c.cod_produto
        LEFT JOIN ordem_fabric o
            ON o.produto = c.produto_join_of
        ORDER BY
            c.data_previsao_entrega,
            c.numero_pedido,
            c.item_pedido,
            c.cod_produto
        """

        df = pd.read_sql(sql, conn)
        conn.close()
        return df


    @st.cache_data(ttl=300)
    def carregar_auditoria_of(data_ini, data_fim):
        conn = connect_to_mysql()

        if conn is None:
            return pd.DataFrame()

        sql = """
        SELECT
            o.nro_of,
            o.produto,
            p.codigo_produto_material,
            o.status_of,
            o.data_abertura,
            o.data_fechamento,
            o.qtde,
            o.qtde_produzida,

            CASE
                WHEN o.status_of = 'F' THEN 'OF FECHADAS NO PERÍODO'
                WHEN o.status_of = 'A' THEN 'OF EM ANDAMENTO'
                ELSE 'OUTROS'
            END AS grupo_of,

            COALESCE(p.estoque_minimo, 0) AS estoque_minimo,

            CASE
                WHEN COALESCE(p.estoque_minimo, 0) > 0
                    THEN 'Produtos Produzido Estoque minimo'
                ELSE 'Produtos Produzido S/ Estoque minimo'
            END AS tipo_estoque_minimo,

            CASE
                WHEN o.status_of = 'F'
                    THEN COALESCE(o.qtde_produzida, o.qtde, 0)
                ELSE COALESCE(o.qtde, 0)
            END AS qtd_kg_relatorio

        FROM ORDEM_FABRIC o

        LEFT JOIN PRODUTO p
            ON p.codigo_produto_material = o.produto

        WHERE
        (
            o.status_of = 'F'
            AND o.data_fechamento BETWEEN %s AND %s
            AND o.sub_grupo NOT IN (1, 3, 16)
            AND o.grupo NOT IN (800, 801)
            AND o.origem NOT IN (997)
        )
        OR
        (
            o.status_of = 'A'
            AND o.data_abertura <= %s
            AND o.sub_grupo NOT IN (1, 3, 16)
            AND o.grupo NOT IN (800, 801)
            AND o.origem NOT IN (997)
        )

        ORDER BY
            grupo_of,
            tipo_estoque_minimo,
            o.produto,
            o.nro_of
        """

        df_auditoria = pd.read_sql(
            sql,
            conn,
            params=[data_ini, data_fim, data_fim]
        )

        conn.close()
        return df_auditoria


    def preparar_carteira(df):
        colunas_numericas = [
            "quantidade_pedida",
            "quantidade_atendida",
            "quantidade_pronta",
            "saldo_pendente",
            "estoque_total_almox",
            "estoque_reservado_almox",
            "estoque_disponivel_almox",
            "qtde_of_aberta",
            "cobertura_total",
            "valor_unitario",
            "valor_total_item"
        ]

        for col in colunas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["necessidade_produzir"] = (
            df["saldo_pendente"] - df["estoque_disponivel_almox"]
        ).clip(lower=0)

        df["saldo_final_cobertura"] = (
            df["cobertura_total"] - df["saldo_pendente"]
        )

        df["status_cobertura"] = df.apply(
            lambda x:
                "🟢 Atende com Estoque ALMOX"
                if x["estoque_disponivel_almox"] >= x["saldo_pendente"]
                else (
                    "🟡 Atende com Estoque ALMOX + OF"
                    if x["cobertura_total"] >= x["saldo_pendente"]
                    else "🔴 Sem Cobertura"
                ),
            axis=1
        )

        return df


    def preparar_auditoria(df):
        if df.empty:
            return df

        colunas_num = [
            "qtde",
            "qtde_produzida",
            "estoque_minimo",
            "qtd_kg_relatorio"
        ]

        for col in colunas_num:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["data_abertura"] = pd.to_datetime(
            df["data_abertura"],
            errors="coerce"
        ).dt.date

        df["data_fechamento"] = pd.to_datetime(
            df["data_fechamento"],
            errors="coerce"
        ).dt.date

        return df


    def card_resumo(titulo, df_base, nome_arquivo):
        qtd_of = df_base["nro_of"].nunique() if not df_base.empty else 0
        qtd_kg = df_base["qtd_kg_relatorio"].sum() if not df_base.empty else 0

        st.markdown(
            f"""
            <div style="
                border:1px solid #333;
                padding:10px;
                text-align:center;
                margin-bottom:8px;
            ">
                <div style="
                    font-weight:bold;
                    font-size:15px;
                    border-bottom:1px solid #333;
                    padding-bottom:6px;
                ">
                    {titulo}
                </div>
                <div style="display:flex;">
                    <div style="
                        width:30%;
                        border-right:1px solid #333;
                        padding:8px;
                    ">
                        <b>QTD OF</b><br>{qtd_of:,.0f}
                    </div>
                    <div style="width:70%; padding:8px;">
                        <b>QTD KG</b><br>{qtd_kg:,.2f}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if df_base.empty:
            st.download_button(
                label="📥 CSV Auditoria",
                data=gerar_csv(df_base),
                file_name=nome_arquivo,
                mime="text/csv",
                disabled=True
            )
        else:
            st.download_button(
                label="📥 CSV Auditoria",
                data=gerar_csv(df_base),
                file_name=nome_arquivo,
                mime="text/csv"
            )


    # =========================
    # CARTEIRA x ESTOQUE x OF
    # =========================

    df = carregar_dados()

    if df.empty:
        st.warning("Nenhum dado encontrado ou falha ao carregar as informações.")
        st.stop()

    df = preparar_carteira(df)

    st.sidebar.header("Filtros")

    clientes = st.sidebar.multiselect(
        "Cliente",
        sorted(df["desc_cliente"].dropna().unique())
    )

    produtos = st.sidebar.multiselect(
        "Código do Produto",
        sorted(df["cod_produto"].dropna().unique())
    )

    status = st.sidebar.multiselect(
        "Status Cobertura",
        sorted(df["status_cobertura"].dropna().unique())
    )

    ufs = st.sidebar.multiselect(
        "UF",
        sorted(df["uf_cliente"].dropna().unique())
    )

    vendedores = st.sidebar.multiselect(
        "Vendedor",
        sorted(df["vendedor"].dropna().unique())
    )

    df_filtrado = df.copy()

    if clientes:
        df_filtrado = df_filtrado[df_filtrado["desc_cliente"].isin(clientes)]

    if produtos:
        df_filtrado = df_filtrado[df_filtrado["cod_produto"].isin(produtos)]

    if status:
        df_filtrado = df_filtrado[df_filtrado["status_cobertura"].isin(status)]

    if ufs:
        df_filtrado = df_filtrado[df_filtrado["uf_cliente"].isin(ufs)]

    if vendedores:
        df_filtrado = df_filtrado[df_filtrado["vendedor"].isin(vendedores)]


    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Pedidos", df_filtrado["numero_pedido"].nunique())
    col2.metric("Itens Pendentes", len(df_filtrado))
    col3.metric("Qtd. Pendente", f"{df_filtrado['saldo_pendente'].sum():,.0f}")
    col4.metric("Necessidade Produzir", f"{df_filtrado['necessidade_produzir'].sum():,.0f}")
    col5.metric(
        "Sem Cobertura",
        len(df_filtrado[df_filtrado["status_cobertura"] == "🔴 Sem Cobertura"])
    )


    st.subheader("Resumo por Status de Cobertura")

    resumo_status = (
        df_filtrado
        .groupby("status_cobertura", as_index=False)
        .agg(
            pedidos=("numero_pedido", "nunique"),
            itens=("cod_produto", "count"),
            saldo_pendente=("saldo_pendente", "sum"),
            estoque_disponivel_almox=("estoque_disponivel_almox", "sum"),
            qtde_of_aberta=("qtde_of_aberta", "sum"),
            necessidade_produzir=("necessidade_produzir", "sum")
        )
    )

    st.dataframe(
        resumo_status,
        use_container_width=True,
        hide_index=True
    )


    st.subheader("Análise Detalhada")

    colunas_exibir = [
        "numero_pedido",
        "item_pedido",
        "cod_produto",
        "produto_pedido",
        "desc_produto",
        "produto_join_of",
        "ped_prod_int",
        "desc_cliente",
        "situacao_pedido",
        "situacao_item",
        "data_pedido",
        "data_previsao_entrega",
        "quantidade_pedida",
        "quantidade_atendida",
        "quantidade_pronta",
        "saldo_pendente",
        "estoque_total_almox",
        "estoque_reservado_almox",
        "estoque_disponivel_almox",
        "qtde_of_aberta",
        "cobertura_total",
        "necessidade_produzir",
        "saldo_final_cobertura",
        "status_cobertura"
    ]

    st.dataframe(
        df_filtrado[colunas_exibir],
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        label="📥 Baixar CSV Carteira",
        data=gerar_csv(df_filtrado[colunas_exibir]),
        file_name="carteira_cod_produto_estoque_almox_of.csv",
        mime="text/csv"
    )


    # =========================
    # RELATÓRIO OF x ESTOQUE MÍNIMO
    # =========================

    st.markdown("---")
    st.subheader("📊 Relatório de OF x Estoque Mínimo")

    col_data1, col_data2 = st.columns(2)

    data_ini = col_data1.date_input(
        "Data inicial Fechamento",
        value=date.today().replace(day=1),
        key="data_ini_of"
    )

    data_fim = col_data2.date_input(
        "Data final Fechamento",
        value=date.today(),
        key="data_fim_of"
    )

    if data_ini > data_fim:
        st.error("A data inicial não pode ser maior que a data final.")
        st.stop()

    df_auditoria = carregar_auditoria_of(data_ini, data_fim)
    df_auditoria = preparar_auditoria(df_auditoria)

    if df_auditoria.empty:
        st.warning("Nenhuma OF encontrada para o período informado.")
    else:
        fechadas_com = df_auditoria[
            (df_auditoria["grupo_of"] == "OF FECHADAS NO PERÍODO")
            & (df_auditoria["tipo_estoque_minimo"] == "Produtos Produzido Estoque minimo")
        ]

        fechadas_sem = df_auditoria[
            (df_auditoria["grupo_of"] == "OF FECHADAS NO PERÍODO")
            & (df_auditoria["tipo_estoque_minimo"] == "Produtos Produzido S/ Estoque minimo")
        ]

        andamento_com = df_auditoria[
            (df_auditoria["grupo_of"] == "OF EM ANDAMENTO")
            & (df_auditoria["tipo_estoque_minimo"] == "Produtos Produzido Estoque minimo")
        ]

        andamento_sem = df_auditoria[
            (df_auditoria["grupo_of"] == "OF EM ANDAMENTO")
            & (df_auditoria["tipo_estoque_minimo"] == "Produtos Produzido S/ Estoque minimo")
        ]

        st.markdown(
            """
            <div style="
                border:2px solid #333;
                padding:6px;
                text-align:center;
                font-weight:bold;
                font-size:17px;
                margin-top:25px;
                margin-bottom:10px;
            ">
                OF FECHADAS NO PERÍODO
            </div>
            """,
            unsafe_allow_html=True
        )

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            card_resumo(
                "Produtos Produzido Estoque minimo",
                fechadas_com,
                "auditoria_of_fechadas_com_estoque_minimo.csv"
            )

        with col_f2:
            card_resumo(
                "Produtos Produzido S/ Estoque minimo",
                fechadas_sem,
                "auditoria_of_fechadas_sem_estoque_minimo.csv"
            )

        st.markdown(
            """
            <div style="
                border:2px solid #333;
                padding:6px;
                text-align:center;
                font-weight:bold;
                font-size:17px;
                margin-top:25px;
                margin-bottom:10px;
            ">
                OF EM ANDAMENTO
            </div>
            """,
            unsafe_allow_html=True
        )

        col_a1, col_a2 = st.columns(2)

        with col_a1:
            card_resumo(
                "Produtos Produzido Estoque minimo",
                andamento_com,
                "auditoria_of_andamento_com_estoque_minimo.csv"
            )

        with col_a2:
            card_resumo(
                "Produtos Produzido S/ Estoque minimo",
                andamento_sem,
                "auditoria_of_andamento_sem_estoque_minimo.csv"
            )

        st.markdown("---")
        st.subheader("Base completa de auditoria")

        colunas_auditoria = [
            "grupo_of",
            "tipo_estoque_minimo",
            "nro_of",
            "produto",
            "codigo_produto_material",
            "status_of",
            "data_abertura",
            "data_fechamento",
            "qtde",
            "qtde_produzida",
            "qtd_kg_relatorio",
            "estoque_minimo"
        ]

        st.dataframe(
            df_auditoria[colunas_auditoria],
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            label="📥 Baixar CSV Auditoria Completa",
            data=gerar_csv(df_auditoria[colunas_auditoria]),
            file_name="auditoria_completa_of_estoque_minimo.csv",
            mime="text/csv"
        )
        

        pdf_bytes = gerar_pdf_of_estoque(
            data_ini=data_ini,
            data_fim=data_fim,
            fechadas_com=fechadas_com,
            fechadas_sem=fechadas_sem,
            andamento_com=andamento_com,
            andamento_sem=andamento_sem,
            df_auditoria=df_auditoria
        )

        st.download_button(
            label="📄 Gerar PDF Relatório",
            data=pdf_bytes,
            file_name="relatorio_of_estoque_minimo.pdf",
            mime="application/pdf"
        )    