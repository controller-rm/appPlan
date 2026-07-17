"""
============================================================
PLANEJAMENTO DE NECESSIDADE DE MATÉRIAS-PRIMAS
Interface inspirada em dashboard ERP industrial
============================================================
"""
def subpage():
    #from __future__ import annotations

    import io
    import os
    from datetime import datetime

    import mysql.connector
    import pandas as pd
    import streamlit as st
    from dotenv import load_dotenv


    # ============================================================
    # CONFIGURAÇÃO
    # ============================================================


    load_dotenv()

    MYSQL_HOST = os.getenv("MYSQL_HOST", "").strip()
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "").strip()
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = "SOFTDIB_ADEX"


    # ============================================================
    # ESTILO VISUAL
    # ============================================================

    st.markdown(
        """
        <style>
            :root {
                --bg: #eaf1f8;
                --bg-secondary: #dfe9f4;

                --panel: #f8fafc;
                --panel-secondary: #f1f5f9;
                --panel-hover: #edf3f8;

                --border: #cbd8e6;
                --border-strong: #b6c7d9;

                --text: #243447;
                --text-strong: #172033;
                --muted: #64748b;

                --blue: #2563eb;
                --blue-light: #3b82f6;
                --blue-dark: #1d4ed8;
                --blue-soft: #dbeafe;

                --green: #15803d;
                --green-soft: #dcfce7;

                --shadow:
                    0 6px 18px rgba(52, 72, 94, 0.08);
            }

            html,
            body,
            [class*="css"] {
                font-family:
                    Inter,
                    ui-sans-serif,
                    system-ui,
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;
            }

            body {
                color: var(--text);
            }

            .stApp {
                background:
                    radial-gradient(
                        circle at 90% 0%,
                        rgba(59, 130, 246, 0.10),
                        transparent 28%
                    ),
                    linear-gradient(
                        180deg,
                        var(--bg) 0%,
                        var(--bg-secondary) 100%
                    );
                color: var(--text);
            }

            .block-container {
                max-width: 1700px;
                padding-top: 1.3rem;
                padding-bottom: 2.5rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }

            #MainMenu,
            footer {
                visibility: hidden;
            }

            /* Mantém o cabeçalho disponível para o botão da sidebar */
            header[data-testid="stHeader"] {
                visibility: visible;
                background: transparent;
            }

            /* ==================================================
            CABEÇALHO
            ================================================== */

            .topbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                padding: 0.4rem 0.2rem 1rem 0.2rem;
                border-bottom: 1px solid var(--border);
            }

            .brand {
                font-size: 1.02rem;
                font-weight: 750;
                color: var(--blue-dark);
                letter-spacing: 0.2px;
            }

            .title {
                font-size: 1.65rem;
                font-weight: 780;
                color: var(--text-strong);
                margin-top: 0.2rem;
                line-height: 1.2;
            }

            .subtitle {
                color: var(--muted);
                font-size: 0.9rem;
                margin-top: 0.3rem;
            }

            /* ==================================================
            CARDS GERAIS
            ================================================== */

            .erp-card {
                background:
                    linear-gradient(
                        180deg,
                        #ffffff 0%,
                        var(--panel) 100%
                    );
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 18px;
                box-shadow: var(--shadow);
            }

            .section-title {
                font-size: 1.02rem;
                font-weight: 750;
                color: var(--text-strong);
                margin-bottom: 0.25rem;
            }

            .section-caption {
                color: var(--muted);
                font-size: 0.85rem;
                margin-bottom: 1rem;
            }

            /* ==================================================
            CARDS DE KPI
            ================================================== */

            div[data-testid="stMetric"] {
                background:
                    linear-gradient(
                        180deg,
                        #ffffff 0%,
                        #f6f9fc 100%
                    );
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 17px 18px;
                min-height: 126px;
                box-shadow: var(--shadow);
                transition:
                    transform 0.18s ease,
                    box-shadow 0.18s ease,
                    border-color 0.18s ease;
            }

            div[data-testid="stMetric"]:hover {
                transform: translateY(-2px);
                border-color: #9db8d5;
                box-shadow:
                    0 10px 24px rgba(52, 72, 94, 0.12);
            }

            div[data-testid="stMetricLabel"] {
                color: var(--muted);
                font-weight: 650;
                font-size: 0.86rem;
            }

            div[data-testid="stMetricValue"] {
                color: var(--text-strong);
                font-weight: 780;
                font-size: 1.8rem;
            }

            div[data-testid="stMetricDelta"] {
                color: var(--green);
                background: var(--green-soft);
                border-radius: 999px;
                padding: 2px 8px;
                width: fit-content;
                font-weight: 650;
            }

            /* ==================================================
            BOTÕES
            ================================================== */

            .stButton > button {
                width: 100%;
                min-height: 44px;
                border-radius: 9px;
                border: 1px solid var(--border-strong);
                background: #ffffff;
                color: var(--text);
                font-weight: 700;
                box-shadow:
                    0 2px 5px rgba(52, 72, 94, 0.06);
                transition:
                    background 0.18s ease,
                    transform 0.18s ease,
                    border-color 0.18s ease;
            }

            .stButton > button:hover {
                background: var(--panel-hover);
                border-color: #92aac3;
                color: var(--text-strong);
                transform: translateY(-1px);
            }

            .stButton > button[kind="primary"] {
                background:
                    linear-gradient(
                        90deg,
                        var(--blue-dark),
                        var(--blue-light)
                    );
                color: #ffffff;
                border: 1px solid var(--blue-dark);
                box-shadow:
                    0 6px 14px rgba(37, 99, 235, 0.22);
            }

            .stButton > button[kind="primary"]:hover {
                background:
                    linear-gradient(
                        90deg,
                        #1e40af,
                        var(--blue)
                    );
                color: #ffffff;
                border-color: #1e40af;
            }

            .stDownloadButton > button {
                border-radius: 9px;
                border: 1px solid var(--blue);
                background: #ffffff;
                color: var(--blue-dark);
                font-weight: 700;
                min-height: 42px;
                box-shadow:
                    0 3px 8px rgba(37, 99, 235, 0.08);
            }

            .stDownloadButton > button:hover {
                background: var(--blue-soft);
                border-color: var(--blue-dark);
                color: var(--blue-dark);
            }

            /* ==================================================
            SELECTBOX E CAMPOS
            ================================================== */

            div[data-baseweb="select"] > div,
            div[data-baseweb="input"] > div,
            div[data-baseweb="base-input"] {
                background-color: #ffffff !important;
                border-color: var(--border-strong) !important;
                color: var(--text-strong) !important;
                border-radius: 9px !important;
                box-shadow:
                    0 1px 3px rgba(52, 72, 94, 0.05);
            }

            div[data-baseweb="select"] > div:hover,
            div[data-baseweb="input"] > div:hover {
                border-color: #8ba8c5 !important;
            }

            div[data-testid="stNumberInput"] input,
            div[data-testid="stTextInput"] input {
                background-color: #ffffff !important;
                color: var(--text-strong) !important;
                border-radius: 9px !important;
            }

            div[data-testid="stNumberInput"] button {
                background: var(--panel-secondary);
                color: var(--text);
                border-color: var(--border);
            }

            div[data-testid="stNumberInput"] button:hover {
                background: var(--blue-soft);
                color: var(--blue-dark);
            }

            /* Texto selecionado no selectbox */
            div[data-baseweb="select"] span {
                color: var(--text-strong) !important;
            }

            /* Menu suspenso */
            ul[role="listbox"] {
                background: #ffffff !important;
                border: 1px solid var(--border) !important;
                border-radius: 9px !important;
            }

            li[role="option"] {
                color: var(--text-strong) !important;
            }

            li[role="option"]:hover {
                background: var(--blue-soft) !important;
            }

            /* ==================================================
            TABELAS
            ================================================== */

            div[data-testid="stDataFrame"] {
                border: 1px solid var(--border);
                border-radius: 11px;
                overflow: hidden;
                box-shadow: var(--shadow);
                background: #ffffff;
            }

            div[data-testid="stDataFrame"] iframe {
                background: #ffffff;
            }

            /* ==================================================
            ABAS
            ================================================== */

            button[data-baseweb="tab"] {
                color: var(--muted);
                font-weight: 680;
                background: transparent;
            }

            button[data-baseweb="tab"]:hover {
                color: var(--blue);
                background: rgba(219, 234, 254, 0.55);
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                color: var(--blue-dark);
                font-weight: 750;
            }

            div[data-baseweb="tab-highlight"] {
                background-color: var(--blue);
            }

            /* ==================================================
            CAIXA DE INFORMAÇÕES
            ================================================== */

            .info-box {
                margin-top: 14px;
                background:
                    linear-gradient(
                        180deg,
                        #ffffff 0%,
                        #f5f8fc 100%
                    );
                border: 1px solid var(--border);
                border-left: 4px solid var(--blue);
                border-radius: 14px;
                padding: 18px;
                color: var(--muted);
                font-size: 0.85rem;
                line-height: 1.55;
                box-shadow: var(--shadow);
            }

            .info-box strong {
                color: var(--blue-dark);
                font-size: 0.95rem;
            }

            /* ==================================================
            RÓTULOS
            ================================================== */

            .row-label {
                color: var(--muted);
                font-size: 0.74rem;
                font-weight: 750;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.15rem;
            }

            label {
                color: var(--text) !important;
            }

            p,
            span,
            div {
                text-rendering: optimizeLegibility;
            }

            hr {
                border: none;
                border-top: 1px solid var(--border);
            }

            /* ==================================================
            ALERTAS DO STREAMLIT
            ================================================== */

            div[data-testid="stAlert"] {
                border-radius: 10px;
                border: 1px solid var(--border);
                box-shadow:
                    0 3px 8px rgba(52, 72, 94, 0.05);
            }

            /* ==================================================
            RESPONSIVIDADE
            ================================================== */

            @media (max-width: 1100px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .title {
                    font-size: 1.35rem;
                }

                div[data-testid="stMetric"] {
                    min-height: 108px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # ============================================================
    # BANCO DE DADOS
    # ============================================================

    def validar_configuracao_banco() -> None:
        faltantes = []

        if not MYSQL_HOST:
            faltantes.append("MYSQL_HOST")
        if not MYSQL_USER:
            faltantes.append("MYSQL_USER")
        if not MYSQL_PASSWORD:
            faltantes.append("MYSQL_PASSWORD")

        if faltantes:
            raise ValueError(
                "Variáveis de ambiente não configuradas: "
                + ", ".join(faltantes)
            )


    def conectar_mysql():
        validar_configuracao_banco()

        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connection_timeout=30,
        )


    @st.cache_data(ttl=600, show_spinner=False)
    def carregar_produtos_disponiveis() -> list[str]:
        sql = """
            SELECT DISTINCT
                CAST(produto AS CHAR) AS produto
            FROM ESTRUTURA
            WHERE produto IS NOT NULL
            AND TRIM(CAST(produto AS CHAR)) <> ''
            ORDER BY produto
        """

        conexao = conectar_mysql()

        try:
            cursor = conexao.cursor(dictionary=True)
            cursor.execute(sql)
            registros = cursor.fetchall()

            return [
                str(registro["produto"]).strip()
                for registro in registros
            ] if registros else []

        finally:
            if "cursor" in locals():
                cursor.close()
            conexao.close()


    def consultar_estrutura(produtos: list[str]) -> pd.DataFrame:
        if not produtos:
            return pd.DataFrame()

        placeholders = ", ".join(["%s"] * len(produtos))

        sql = f"""
            SELECT
                CAST(produto AS CHAR) AS produto,
                sequencia,
                CAST(componente AS CHAR) AS componente,
                quantidade
            FROM ESTRUTURA
            WHERE CAST(produto AS CHAR) IN ({placeholders})
            ORDER BY produto, sequencia, componente
        """

        conexao = conectar_mysql()

        try:
            cursor = conexao.cursor(dictionary=True)
            cursor.execute(sql, tuple(produtos))
            registros = cursor.fetchall()
            return pd.DataFrame(registros)

        finally:
            if "cursor" in locals():
                cursor.close()
            conexao.close()


    # ============================================================
    # FORMATAÇÃO
    # ============================================================

    def formatar_numero_br(valor, casas: int = 3) -> str:
        if pd.isna(valor):
            return ""

        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return ""

        return (
            f"{numero:,.{casas}f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )


    def formatar_inteiro_br(valor) -> str:
        try:
            return f"{int(valor):,}".replace(",", ".")
        except (TypeError, ValueError):
            return "0"


    # ============================================================
    # REGRAS DE NEGÓCIO
    # ============================================================

    def obter_dataframe_entrada() -> pd.DataFrame:
        linhas = []

        for indice, item in enumerate(st.session_state["linhas_produtos"]):
            produto = item.get("produto", "")
            quantidade = item.get("quantidade", 0.0)

            if produto or quantidade:
                linhas.append(
                    {
                        "Produto": produto,
                        "Quantidade desejada": quantidade,
                    }
                )

        return pd.DataFrame(linhas)


    def preparar_entradas(df_entrada: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        if df_entrada is None or df_entrada.empty:
            return pd.DataFrame(), []

        df = df_entrada.copy()

        df["Produto"] = (
            df["Produto"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df["Quantidade desejada"] = pd.to_numeric(
            df["Quantidade desejada"],
            errors="coerce",
        )

        erros = []

        for indice, linha in df.iterrows():
            numero_linha = indice + 1

            if not linha["Produto"]:
                erros.append(
                    f"Linha {numero_linha}: selecione o produto."
                )

            if pd.isna(linha["Quantidade desejada"]) or linha["Quantidade desejada"] <= 0:
                erros.append(
                    f"Linha {numero_linha}: informe uma quantidade maior que zero."
                )

        if not erros:
            df = (
                df.groupby("Produto", as_index=False)["Quantidade desejada"]
                .sum()
            )

        return df, erros


    def calcular_necessidades(
        df_estrutura: pd.DataFrame,
        df_entradas: pd.DataFrame,
    ) -> pd.DataFrame:
        if df_estrutura.empty or df_entradas.empty:
            return pd.DataFrame()

        estrutura = df_estrutura.copy()

        estrutura["produto"] = (
            estrutura["produto"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        estrutura["componente"] = (
            estrutura["componente"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        estrutura["quantidade"] = pd.to_numeric(
            estrutura["quantidade"],
            errors="coerce",
        ).fillna(0)

        resultado = estrutura.merge(
            df_entradas,
            left_on="produto",
            right_on="Produto",
            how="inner",
        )

        resultado["Quantidade calculada"] = (
            resultado["quantidade"] / 100
        ) * resultado["Quantidade desejada"]

        return resultado.rename(
            columns={
                "produto": "Produto pai",
                "sequencia": "Sequência",
                "componente": "Componente",
                "quantidade": "Quantidade base 100 kg",
            }
        )[
            [
                "Produto pai",
                "Sequência",
                "Componente",
                "Quantidade base 100 kg",
                "Quantidade desejada",
                "Quantidade calculada",
            ]
        ]


    def consolidar_componentes(df_resultado: pd.DataFrame) -> pd.DataFrame:
        """
        Consolida os componentes, desconsiderando registros com Sequência = 0.
        """

        if df_resultado.empty:
            return pd.DataFrame()

        df_valido = df_resultado.copy()

        df_valido["Sequência"] = pd.to_numeric(
            df_valido["Sequência"],
            errors="coerce",
        ).fillna(0)

        # Não considerar sequência 0 nos totalizadores
        df_valido = df_valido[
            df_valido["Sequência"] != 0
        ].copy()

        if df_valido.empty:
            return pd.DataFrame()

        consolidado = (
            df_valido.groupby(
                ["Componente"],
                as_index=False,
                dropna=False,
            )
            .agg(
                Sequência=("Sequência", "min"),
                **{
                    "Quantidade base 100 kg": (
                        "Quantidade base 100 kg",
                        "sum",
                    ),
                    "Quantidade total necessária": (
                        "Quantidade calculada",
                        "sum",
                    ),
                    "Produtos que utilizam": (
                        "Produto pai",
                        "nunique",
                    ),
                },
            )
            .sort_values(
                "Quantidade total necessária",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        return consolidado


    def formatar_detalhado(df: pd.DataFrame) -> pd.DataFrame:
        resultado = df.copy()

        for coluna in [
            "Quantidade base 100 kg",
            "Quantidade desejada",
            "Quantidade calculada",
        ]:
            resultado[coluna] = resultado[coluna].map(
                lambda valor: formatar_numero_br(valor, 3)
            )

        return resultado


    def formatar_consolidado(df: pd.DataFrame) -> pd.DataFrame:
        resultado = df.copy()

        for coluna in [
            "Quantidade base 100 kg",
            "Quantidade total necessária",
        ]:
            resultado[coluna] = resultado[coluna].map(
                lambda valor: formatar_numero_br(valor, 3)
            )

        return resultado

    def normalizar_codigo(serie: pd.Series) -> pd.Series:
        return (
            serie
            .fillna("")
            .astype(str)
            .str.replace("\ufeff", "", regex=False)  # Remove BOM
            .str.replace("\xa0", " ", regex=False)   # Espaço invisível
            .str.replace("–", "-", regex=False)      # Hífen longo
            .str.replace("—", "-", regex=False)      # Travessão
            .str.strip()
            .str.upper()
            .str.replace(r"\s+", "", regex=True)     # Remove todos os espaços
        )



    def adicionar_qtde_csv(
        consolidado: pd.DataFrame,
        arquivo_csv,
    ) -> pd.DataFrame:

        resultado = consolidado.copy()

        # Quando nenhum CSV for carregado
        if arquivo_csv is None:
            resultado["Qtde"] = 0.0
            return resultado

        # Detecta automaticamente ; ou ,
        df_csv = pd.read_csv(
            arquivo_csv,
            sep=";",
            encoding="cp1252",
            dtype=str,
            index_col=False,
            usecols=range(38),
        )  

        df_csv.columns = df_csv.columns.str.strip()

        colunas_obrigatorias = {"Produto", "Qtde"}

        if not colunas_obrigatorias.issubset(df_csv.columns):
            raise ValueError(
                "O CSV deve possuir as colunas Produto e Qtde."
            )

        df_csv["Produto"] = normalizar_codigo(
            df_csv["Produto"]
        )

        # Aceita valores como 1.250,50 ou 1250.50
        df_csv["Qtde"] = (
            df_csv["Qtde"]
            .fillna("0")
            .astype(str)
            .str.strip()
            .str.replace("\xa0", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

        df_csv["Qtde"] = pd.to_numeric(
            df_csv["Qtde"],
            errors="coerce",
        ).fillna(0)

        # Caso o mesmo produto apareça mais de uma vez
        df_csv = (
            df_csv.groupby("Produto", as_index=False)["Qtde"]
            .sum()
        )

        resultado["Componente"] = normalizar_codigo(
            resultado["Componente"]
        )

        resultado = resultado.merge(
            df_csv,
            left_on="Componente",
            right_on="Produto",
            how="left",
        )

        resultado["Qtde"] = resultado["Qtde"].fillna(0)

        resultado.drop(
            columns=["Produto"],
            inplace=True,
            errors="ignore",
        )
        
        resultado["Saldo necessário"] = (
            resultado["Quantidade total necessária"]
            - resultado["Qtde"]
        )

        return resultado

    def gerar_excel(
        detalhado: pd.DataFrame,
        consolidado: pd.DataFrame,
    ) -> bytes:
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            detalhado.to_excel(
                writer,
                sheet_name="Por Produto",
                index=False,
            )

            consolidado.to_excel(
                writer,
                sheet_name="Consolidado",
                index=False,
            )

            for nome_aba, dataframe in {
                "Por Produto": detalhado,
                "Consolidado": consolidado,
            }.items():
                planilha = writer.sheets[nome_aba]

                for indice, coluna in enumerate(
                    dataframe.columns,
                    start=1,
                ):
                    maior = max(
                        len(str(coluna)),
                        dataframe[coluna]
                        .astype(str)
                        .map(len)
                        .max()
                        if not dataframe.empty
                        else 0,
                    )

                    planilha.column_dimensions[
                        planilha.cell(
                            row=1,
                            column=indice,
                        ).column_letter
                    ].width = min(max(maior + 3, 12), 38)

        return buffer.getvalue()


    # ============================================================
    # ESTADO DA INTERFACE
    # ============================================================

    if "linhas_produtos" not in st.session_state:
        st.session_state["linhas_produtos"] = [
            {"produto": "", "quantidade": 0.0}
            for _ in range(5)
        ]

    if "resultado_detalhado" not in st.session_state:
        st.session_state["resultado_detalhado"] = pd.DataFrame()

    if "resultado_consolidado" not in st.session_state:
        st.session_state["resultado_consolidado"] = pd.DataFrame()

    if "data_calculo" not in st.session_state:
        st.session_state["data_calculo"] = None


    def adicionar_linha():
        st.session_state["linhas_produtos"].append(
            {"produto": "", "quantidade": 0.0}
        )


    def limpar_tudo():
        st.session_state["linhas_produtos"] = [
            {"produto": "", "quantidade": 0.0}
            for _ in range(5)
        ]

        st.session_state["resultado_detalhado"] = pd.DataFrame()
        st.session_state["resultado_consolidado"] = pd.DataFrame()
        st.session_state["data_calculo"] = None


    # ============================================================
    # CABEÇALHO
    # ============================================================

    st.markdown(
        """
        <div class="topbar">
            <div>
                <div class="brand">◆ Controller Virtual</div>
                <div class="title">Planejamento de Necessidade de Matérias-Primas</div>
                <div class="subtitle">
                    Simulação da necessidade de componentes com base na estrutura para 100 kg.
                </div>
            </div>
            <div class="subtitle">SOFTDIB_ADEX · ESTRUTURA</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ============================================================
    # INTERFACE PRINCIPAL
    # ============================================================

    try:
        produtos_disponiveis = carregar_produtos_disponiveis()

        coluna_entrada, coluna_resultado = st.columns(
            [0.95, 2.15],
            gap="medium",
        )

        # --------------------------------------------------------
        # PAINEL ESQUERDO
        # --------------------------------------------------------

        with coluna_entrada:
            st.markdown(
                """
                <div class="erp-card">
                    <div class="section-title">Produtos e Quantidades Desejadas</div>
                    <div class="section-caption">
                        Informe os produtos e as quantidades que deseja produzir.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            cab1, cab2, cab3 = st.columns([0.16, 1.15, 0.85])

            with cab1:
                st.markdown('<div class="row-label">#</div>', unsafe_allow_html=True)
            with cab2:
                st.markdown('<div class="row-label">Produto</div>', unsafe_allow_html=True)
            with cab3:
                st.markdown('<div class="row-label">Quantidade desejada (kg)</div>', unsafe_allow_html=True)

            for indice in range(len(st.session_state["linhas_produtos"])):
                c_numero, c_produto, c_quantidade = st.columns(
                    [0.16, 1.15, 0.85],
                    vertical_alignment="center",
                )

                with c_numero:
                    st.markdown(
                        f"<div style='padding-top:12px;color:#b7c4d5;font-weight:700'>{indice + 1}</div>",
                        unsafe_allow_html=True,
                    )

                with c_produto:
                    produto_atual = st.session_state["linhas_produtos"][indice]["produto"]

                    produto = st.selectbox(
                        label=f"Produto {indice + 1}",
                        options=[""] + produtos_disponiveis,
                        index=(
                            ([""] + produtos_disponiveis).index(produto_atual)
                            if produto_atual in produtos_disponiveis
                            else 0
                        ),
                        key=f"produto_linha_{indice}",
                        label_visibility="collapsed",
                    )

                    st.session_state["linhas_produtos"][indice]["produto"] = produto

                with c_quantidade:
                    quantidade = st.number_input(
                        label=f"Quantidade {indice + 1}",
                        min_value=0.0,
                        value=float(
                            st.session_state["linhas_produtos"][indice]["quantidade"]
                            or 0.0
                        ),
                        step=1.0,
                        format="%.3f",
                        key=f"quantidade_linha_{indice}",
                        label_visibility="collapsed",
                    )

                    st.session_state["linhas_produtos"][indice]["quantidade"] = quantidade

            botao_adicionar, botao_limpar = st.columns([1.3, 1])

            with botao_adicionar:
                st.button(
                    "＋ Adicionar linha",
                    on_click=adicionar_linha,
                    use_container_width=True,
                )

            with botao_limpar:
                st.button(
                    "Limpar",
                    on_click=limpar_tudo,
                    use_container_width=True,
                )

            calcular = st.button(
                "⇩  Calcular",
                type="primary",
                use_container_width=True,
            )

            st.markdown(
                """
                <div class="info-box">
                    <strong>ⓘ Como funciona</strong><br><br>
                    A quantidade base dos componentes está cadastrada para
                    <b>100 kg</b> do produto final.<br><br>
                    A necessidade é calculada proporcionalmente à quantidade
                    desejada informada.
                </div>
                """,
                unsafe_allow_html=True,
            )

        # --------------------------------------------------------
        # PROCESSAMENTO
        # --------------------------------------------------------

        if calcular:
            df_entrada = obter_dataframe_entrada()
            df_entradas, erros = preparar_entradas(df_entrada)

            if erros:
                for erro in erros:
                    st.error(erro)

            elif df_entradas.empty:
                st.warning(
                    "Selecione pelo menos um produto e informe uma quantidade."
                )

            else:
                produtos = df_entradas["Produto"].tolist()

                with st.spinner(
                    "Consultando estrutura e calculando necessidades..."
                ):
                    df_estrutura = consultar_estrutura(produtos)

                    encontrados = set(
                        df_estrutura["produto"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    ) if not df_estrutura.empty else set()

                    nao_encontrados = [
                        produto
                        for produto in produtos
                        if produto not in encontrados
                    ]

                    if nao_encontrados:
                        st.warning(
                            "Produtos sem estrutura cadastrada: "
                            + ", ".join(nao_encontrados)
                        )

                    detalhado = calcular_necessidades(
                        df_estrutura,
                        df_entradas,
                    )

                    consolidado = consolidar_componentes(detalhado)

                    st.session_state["resultado_detalhado"] = detalhado
                    st.session_state["resultado_consolidado"] = consolidado
                    st.session_state["data_calculo"] = datetime.now()

        # --------------------------------------------------------
        # PAINEL DIREITO
        # --------------------------------------------------------

        with coluna_resultado:
            detalhado = st.session_state["resultado_detalhado"]
            consolidado = st.session_state["resultado_consolidado"]
            data_calculo = st.session_state["data_calculo"]

            total_insumos = (
                consolidado["Componente"].nunique()
                if not consolidado.empty
                else 0
            )

            quantidade_total = (
                consolidado["Quantidade total necessária"].sum()
                if not consolidado.empty
                else 0
            )

            produtos_planejados = (
                detalhado["Produto pai"].nunique()
                if not detalhado.empty
                else 0
            )

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            kpi1.metric(
                "📦 Total de Insumos",
                formatar_inteiro_br(total_insumos),
                "componentes diferentes",
            )

            kpi2.metric(
                "⚖️ Quantidade Total",
                formatar_numero_br(quantidade_total, 3),
                "kg necessários",
            )

            kpi3.metric(
                "📋 Produtos Planejados",
                formatar_inteiro_br(produtos_planejados),
                "produtos",
            )

            kpi4.metric(
                "📅 Data do Cálculo",
                (
                    data_calculo.strftime("%d/%m/%Y")
                    if data_calculo
                    else "--/--/----"
                ),
                (
                    data_calculo.strftime("%H:%M")
                    if data_calculo
                    else "aguardando"
                ),
            )

            aba_consolidado, aba_produto, aba_componente = st.tabs(
                [
                    "Resultado Consolidado",
                    "Por Produto",
                    "Por Componente",
                ]
            )

            with aba_consolidado:
                if consolidado.empty:
                    st.info(
                        "Preencha os produtos ao lado e clique em Calcular."
                    )
                else:
                    tabela = formatar_consolidado(
                        consolidado[
                            [
                                "Componente",
                                "Sequência",
                                "Quantidade base 100 kg",
                                "Quantidade total necessária",
                            ]
                        ]
                    )

                    st.dataframe(
                        tabela,
                        use_container_width=True,
                        hide_index=True,
                        height=470,
                        column_config={
                            "Componente": st.column_config.TextColumn(
                                "Componente",
                                width="medium",
                            ),
                            "Sequência": st.column_config.NumberColumn(
                                "Sequência",
                                format="%d",
                                width="small",
                            ),
                            "Quantidade base 100 kg": st.column_config.TextColumn(
                                "Qtd. Base (p/100 kg)",
                                width="medium",
                            ),
                            "Quantidade total necessária": st.column_config.TextColumn(
                                "Quantidade Total (kg)",
                                width="medium",
                            ),
                        },
                    )

                    total_base = consolidado[
                        "Quantidade base 100 kg"
                    ].sum()

                    st.markdown(
                        f"""
                        <div class="erp-card" style="margin-top:8px;padding:14px 18px">
                            <div style="display:flex;justify-content:space-between;align-items:center">
                                <strong style="color:#4b9cff">Total Geral</strong>
                                <div>
                                    <span style="margin-right:85px;color:#4b9cff;font-weight:750">
                                        {formatar_numero_br(total_base, 3)}
                                    </span>
                                    <span style="color:#4b9cff;font-weight:750">
                                        {formatar_numero_br(quantidade_total, 3)}
                                    </span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with aba_produto:
                if detalhado.empty:
                    st.info("Nenhum resultado calculado.")
                else:
                    produto_filtro = st.multiselect(
                        "Filtrar produto",
                        options=sorted(
                            detalhado["Produto pai"].unique()
                        ),
                        placeholder="Todos os produtos",
                    )

                    tabela_produto = detalhado.copy()

                    if produto_filtro:
                        tabela_produto = tabela_produto[
                            tabela_produto["Produto pai"].isin(
                                produto_filtro
                            )
                        ]

                    st.dataframe(
                        formatar_detalhado(tabela_produto),
                        use_container_width=True,
                        hide_index=True,
                        height=505,
                    )

            with aba_componente:
                if consolidado.empty:
                    st.info("Nenhum resultado calculado.")
                else:
                    componente = st.text_input(
                        "Pesquisar componente",
                        placeholder="Digite o código do componente",
                    )

                    tabela_componente = consolidado.copy()

                    if componente:
                        tabela_componente = tabela_componente[
                            tabela_componente["Componente"]
                            .astype(str)
                            .str.contains(
                                componente.strip(),
                                case=False,
                                na=False,
                            )
                        ]

                    st.dataframe(
                        formatar_consolidado(tabela_componente),
                        use_container_width=True,
                        hide_index=True,
                        height=505,
                    )

            arquivo_csv_estoque = st.file_uploader(
                "Carregar CSV de quantidades",
                type=["csv"],
                help="O arquivo deve possuir as colunas Produto e Qtde.",
                key="csv_quantidade_componentes",
            )
            
            if not detalhado.empty:

                consolidado_excel = adicionar_qtde_csv(
                    consolidado,
                    arquivo_csv_estoque,
                )

                arquivo_excel = gerar_excel(
                    detalhado,
                    consolidado_excel,
                )

                _, coluna_exportar = st.columns([3.2, 1])

                with coluna_exportar:
                    st.download_button(
                        "⇩ Exportar para Excel",
                        data=arquivo_excel,
                        file_name="necessidade_materias_primas.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        use_container_width=True,
                    )

    except mysql.connector.Error as erro:
        st.error(
            "Erro ao conectar ou consultar o banco de dados."
        )
        st.code(str(erro))

    except ValueError as erro:
        st.error(str(erro))

    except Exception as erro:
        st.error(
            "Ocorreu um erro inesperado durante o processamento."
        )
        st.exception(erro)
