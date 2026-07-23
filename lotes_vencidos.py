import os

import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv


BANCO_DADOS = "SOFTDIB_ADEX"


def conectar_mysql():
    load_dotenv()

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=BANCO_DADOS,
        connection_timeout=30,
    )


@st.cache_data(ttl=300, show_spinner=False)
def carregar_lotes_vencidos() -> pd.DataFrame:
    conexao = None
    cursor = None

    try:
        conexao = conectar_mysql()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                produto,
                descricao_produto,
                tipo_material,
                quantidade,
                custo_unitario,
                quantidade * custo_unitario AS valor_total,
                nro_lote,
                vcto_lote,
                deposito,
                codigo_filial
            FROM `SOFTDIB_ADEX`.`POSICAO_ESTOQUE_ATUAL`
            WHERE vcto_lote IS NOT NULL
              AND vcto_lote < CURDATE()
            ORDER BY vcto_lote, produto, nro_lote
            """
        )
        dados = cursor.fetchall()

        return pd.DataFrame(
            dados,
            columns=[
                "produto",
                "descricao_produto",
                "tipo_material",
                "quantidade",
                "custo_unitario",
                "valor_total",
                "nro_lote",
                "vcto_lote",
                "deposito",
                "codigo_filial",
            ],
        )
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None and conexao.is_connected():
            conexao.close()


def gerar_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(
        index=False,
        sep=";",
        decimal=",",
        date_format="%d/%m/%Y",
    ).encode("utf-8-sig")


def subpage():
    st.title("📅 Produtos com lotes vencidos")
    st.caption(
        "Registros de SOFTDIB_ADEX.POSICAO_ESTOQUE_ATUAL cuja data "
        "de vencimento do lote é anterior à data atual."
    )

    if st.button("🔄 Atualizar dados", key="atualizar_lotes_vencidos"):
        carregar_lotes_vencidos.clear()

    try:
        with st.spinner("Consultando lotes vencidos..."):
            df = carregar_lotes_vencidos()
    except (ValueError, mysql.connector.Error) as erro:
        st.error(f"Não foi possível consultar os lotes vencidos: {erro}")
        return

    if df.empty:
        st.success("Nenhum lote vencido foi encontrado.")
        return

    df["vcto_lote"] = pd.to_datetime(df["vcto_lote"], errors="coerce")
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0)
    df["custo_unitario"] = pd.to_numeric(
        df["custo_unitario"], errors="coerce"
    ).fillna(0)
    df["valor_total"] = pd.to_numeric(
        df["valor_total"], errors="coerce"
    ).fillna(0)

    st.subheader("Filtros")
    col1, col2, col3, col4 = st.columns(4)

    produtos = col1.multiselect(
        "Produto",
        sorted(df["produto"].dropna().astype(str).unique()),
    )
    tipos = col2.multiselect(
        "Tipo de material",
        sorted(df["tipo_material"].dropna().astype(str).unique()),
    )
    depositos = col3.multiselect(
        "Depósito",
        sorted(df["deposito"].dropna().astype(str).unique()),
    )
    filiais = col4.multiselect(
        "Código da filial",
        sorted(df["codigo_filial"].dropna().unique()),
    )

    df_filtrado = df.copy()

    if produtos:
        df_filtrado = df_filtrado[df_filtrado["produto"].astype(str).isin(produtos)]
    if tipos:
        df_filtrado = df_filtrado[
            df_filtrado["tipo_material"].astype(str).isin(tipos)
        ]
    if depositos:
        df_filtrado = df_filtrado[
            df_filtrado["deposito"].astype(str).isin(depositos)
        ]
    if filiais:
        df_filtrado = df_filtrado[df_filtrado["codigo_filial"].isin(filiais)]

    metrica1, metrica2, metrica3, metrica4 = st.columns(4)
    metrica1.metric("Produtos", df_filtrado["produto"].nunique())
    metrica2.metric("Lotes vencidos", len(df_filtrado))
    metrica3.metric(
        "Quantidade total",
        f"{df_filtrado['quantidade'].sum():,.4f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
    )
    metrica4.metric(
        "Valor total vencido",
        "R$ "
        + f"{df_filtrado['valor_total'].sum():,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
    )

    st.subheader("Relação de lotes vencidos")
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        column_config={
            "produto": "Produto",
            "descricao_produto": "Descrição do produto",
            "tipo_material": "Tipo de material",
            "quantidade": st.column_config.NumberColumn(
                "Quantidade",
                format="%.4f",
            ),
            "custo_unitario": st.column_config.NumberColumn(
                "Custo unitário",
                format="R$ %.6f",
            ),
            "valor_total": st.column_config.NumberColumn(
                "Valor total",
                format="R$ %.2f",
            ),
            "nro_lote": "Número do lote",
            "vcto_lote": st.column_config.DateColumn(
                "Vencimento do lote",
                format="DD/MM/YYYY",
            ),
            "deposito": "Depósito",
            "codigo_filial": "Código da filial",
        },
    )

    st.download_button(
        "📥 Baixar lotes vencidos (CSV)",
        data=gerar_csv(df_filtrado),
        file_name="lotes_vencidos.csv",
        mime="text/csv",
        use_container_width=True,
    )
