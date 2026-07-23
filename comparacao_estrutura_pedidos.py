"""Compara estruturas enviadas por CSV com estruturas dos itens de pedidos abertos."""

from __future__ import annotations

import io
import os
from collections.abc import Iterable

import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
MYSQL_DATABASE = "SOFTDIB_ADEX"


def normalizar_codigo(valor: object) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    return texto.upper()


def extrair_produto_base(valor: object) -> str:
    """Remove a embalagem/sufixo: UL41BR006.200 -> UL41BR006."""
    codigo = normalizar_codigo(valor)
    return codigo.split(".", 1)[0] if codigo else ""


def conectar_mysql():
    config = {
        "host": os.getenv("MYSQL_HOST", "").strip(),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "").strip(),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": MYSQL_DATABASE,
        "connection_timeout": 30,
    }
    faltantes = [campo for campo in ("host", "user", "password") if not config[campo]]
    if faltantes:
        raise ValueError("Configuração MySQL ausente: " + ", ".join(faltantes))
    return mysql.connector.connect(**config)


def em_lotes(valores: Iterable[str], tamanho: int = 800):
    lista = list(dict.fromkeys(valores))
    for inicio in range(0, len(lista), tamanho):
        yield lista[inicio : inicio + tamanho]


@st.cache_data(ttl=300, show_spinner=False)
def consultar_itens_abertos() -> pd.DataFrame:
    sql = """
        SELECT
            p.nro_pedido,
            CAST(i.cliente AS CHAR) AS cliente,
            p.cliente_compl AS desc_cliente,
            p.situacao_pedido,
            p.origem_venda,
            i.situacao_item,
            CAST(i.codigo_produto AS CHAR) AS codigo_produto,
            i.quantidade_pedida,
            i.quantidade_atendida,
            (COALESCE(i.quantidade_pedida, 0) -
             COALESCE(i.quantidade_atendida, 0)) AS saldo
        FROM PEDIDO p
        INNER JOIN ITENS_PEDIDO i
            ON i.nro_pedido = p.nro_pedido
           AND i.codigo_filial = p.codigo_filial
        WHERE p.situacao_pedido IN (1, 2)
          AND COALESCE(p.origem_venda, 0) <> 997
          AND i.situacao_item NOT IN (6, 9)
        ORDER BY p.nro_pedido, i.codigo_produto
    """
    conexao = conectar_mysql()
    try:
        return pd.read_sql(sql, conexao)
    finally:
        conexao.close()


@st.cache_data(ttl=300, show_spinner=False)
def consultar_estruturas(produtos: tuple[str, ...]) -> pd.DataFrame:
    colunas = ["produto", "sequencia", "componente", "quantidade"]
    produtos = tuple(filter(None, (normalizar_codigo(p) for p in produtos)))
    if not produtos:
        return pd.DataFrame(columns=colunas)

    partes: list[pd.DataFrame] = []
    conexao = conectar_mysql()
    try:
        for lote in em_lotes(produtos):
            marcadores = ", ".join(["%s"] * len(lote))
            sql = f"""
                SELECT CAST(produto AS CHAR) AS produto,
                       sequencia,
                       CAST(componente AS CHAR) AS componente,
                       quantidade
                FROM ESTRUTURA
                WHERE CAST(produto AS CHAR) IN ({marcadores})
                ORDER BY produto, sequencia, componente
            """
            partes.append(pd.read_sql(sql, conexao, params=tuple(lote)))
    finally:
        conexao.close()

    if not partes:
        return pd.DataFrame(columns=colunas)
    resultado = pd.concat(partes, ignore_index=True)
    resultado["produto"] = resultado["produto"].map(normalizar_codigo)
    resultado["componente"] = resultado["componente"].map(normalizar_codigo)
    resultado["quantidade"] = pd.to_numeric(resultado["quantidade"], errors="coerce").fillna(0)
    return resultado


@st.cache_data(ttl=300, show_spinner=False)
def consultar_ofs_abertas(produtos: tuple[str, ...]) -> pd.DataFrame:
    """Busca OFs abertas para o produto compatível, considerando sua BASE."""
    colunas = ["produto_base", "produto_of", "nro_of", "data_abertura", "qtde"]
    produtos = tuple(filter(None, (normalizar_codigo(p) for p in produtos)))
    if not produtos:
        return pd.DataFrame(columns=colunas)

    partes = []
    conexao = conectar_mysql()
    try:
        for lote in em_lotes(produtos):
            marcadores = ", ".join(["%s"] * len(lote))
            sql = f"""
                SELECT
                    UPPER(TRIM(SUBSTRING_INDEX(CAST(produto AS CHAR), '.', 1))) AS produto_base,
                    CAST(produto AS CHAR) AS produto_of,
                    nro_of,
                    data_abertura,
                    qtde
                FROM ORDEM_FABRIC
                WHERE UPPER(TRIM(CAST(status_of AS CHAR))) = 'A'
                  AND UPPER(TRIM(SUBSTRING_INDEX(CAST(produto AS CHAR), '.', 1)))
                      IN ({marcadores})
                ORDER BY produto_base, data_abertura, nro_of
            """
            partes.append(pd.read_sql(sql, conexao, params=tuple(lote)))
    finally:
        conexao.close()

    if not partes:
        return pd.DataFrame(columns=colunas)
    resultado = pd.concat(partes, ignore_index=True)
    resultado["produto_base"] = resultado["produto_base"].map(normalizar_codigo)
    resultado["produto_of"] = resultado["produto_of"].map(normalizar_codigo)
    resultado["data_abertura"] = pd.to_datetime(resultado["data_abertura"], errors="coerce")
    resultado["qtde"] = pd.to_numeric(resultado["qtde"], errors="coerce").fillna(0)
    return resultado


def adicionar_ofs_compativeis(compativeis: pd.DataFrame, ofs: pd.DataFrame) -> pd.DataFrame:
    resultado = compativeis.copy()
    resultado["tem_of_andamento"] = "Não"
    resultado["nro_of"] = ""
    resultado["data_abertura_of"] = ""
    resultado["qtde_of"] = ""
    if resultado.empty or ofs.empty:
        return resultado

    agrupado = {}
    for produto, grupo in ofs.groupby("produto_base"):
        grupo = grupo.sort_values(["data_abertura", "nro_of"], na_position="last")
        agrupado[produto] = {
            "nro_of": " | ".join(
                normalizar_codigo(valor) for valor in grupo["nro_of"]
            ),
            "data_abertura_of": " | ".join(
                data.strftime("%d/%m/%Y") if pd.notna(data) else ""
                for data in grupo["data_abertura"]
            ),
            "qtde_of": " | ".join(
                f"{valor:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                for valor in grupo["qtde"]
            ),
        }

    for indice, linha in resultado.iterrows():
        dados = agrupado.get(linha["produto_compativel_pedido"])
        if dados:
            resultado.at[indice, "tem_of_andamento"] = "Sim"
            resultado.at[indice, "nro_of"] = dados["nro_of"]
            resultado.at[indice, "data_abertura_of"] = dados["data_abertura_of"]
            resultado.at[indice, "qtde_of"] = dados["qtde_of"]
    return resultado


@st.cache_data(ttl=300, show_spinner=False)
def consultar_produtos_vencidos(produtos: tuple[str, ...]) -> pd.DataFrame:
    """Busca produtos vencidos cuja base coincide com o produto analisado."""
    colunas = [
        "produto_base", "produto_vencido", "quantidade", "deposito", "vcto_lote"
    ]
    produtos_base = tuple(filter(None, (extrair_produto_base(p) for p in produtos)))
    if not produtos_base:
        return pd.DataFrame(columns=colunas)

    partes: list[pd.DataFrame] = []
    conexao = conectar_mysql()
    try:
        for lote in em_lotes(produtos_base):
            marcadores = ", ".join(["%s"] * len(lote))
            sql = f"""
                SELECT
                    UPPER(TRIM(SUBSTRING_INDEX(CAST(produto AS CHAR), '.', 1)))
                        AS produto_base,
                    UPPER(TRIM(CAST(produto AS CHAR))) AS produto_vencido,
                    quantidade,
                    deposito,
                    vcto_lote
                FROM POSICAO_ESTOQUE_ATUAL
                WHERE vcto_lote IS NOT NULL
                  AND vcto_lote < CURDATE()
                  AND UPPER(TRIM(SUBSTRING_INDEX(CAST(produto AS CHAR), '.', 1)))
                      IN ({marcadores})
                ORDER BY produto_base, produto_vencido, vcto_lote, deposito
            """
            partes.append(pd.read_sql(sql, conexao, params=tuple(lote)))
    finally:
        conexao.close()

    if not partes:
        return pd.DataFrame(columns=colunas)

    resultado = pd.concat(partes, ignore_index=True)
    resultado["produto_base"] = resultado["produto_base"].map(normalizar_codigo)
    resultado["produto_vencido"] = resultado["produto_vencido"].map(normalizar_codigo)
    resultado["quantidade"] = pd.to_numeric(
        resultado["quantidade"], errors="coerce"
    ).fillna(0)
    resultado["vcto_lote"] = pd.to_datetime(resultado["vcto_lote"], errors="coerce")
    return resultado


def adicionar_produtos_vencidos(
    compativeis: pd.DataFrame,
    produtos_vencidos: pd.DataFrame,
) -> pd.DataFrame:
    resultado = compativeis.copy()
    resultado["produto_vencido_compativel"] = ""
    resultado["quantidade_produto_vencido"] = ""
    resultado["deposito_produto_vencido"] = ""
    resultado["vcto_lote_produto_vencido"] = ""

    if resultado.empty or produtos_vencidos.empty:
        return resultado

    vencidos_por_base = {}
    for produto_base, grupo in produtos_vencidos.groupby("produto_base", sort=False):
        vencidos_por_base[produto_base] = {
            "produto": " | ".join(grupo["produto_vencido"].fillna("").astype(str)),
            "quantidade": " | ".join(
                f"{valor:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                for valor in grupo["quantidade"]
            ),
            "deposito": " | ".join(grupo["deposito"].fillna("").astype(str)),
            "vencimento": " | ".join(
                data.strftime("%d/%m/%Y") if pd.notna(data) else ""
                for data in grupo["vcto_lote"]
            ),
        }

    for indice, linha in resultado.iterrows():
        dados = vencidos_por_base.get(extrair_produto_base(linha["produto_upload"]))
        if dados:
            resultado.at[indice, "produto_vencido_compativel"] = dados["produto"]
            resultado.at[indice, "quantidade_produto_vencido"] = dados["quantidade"]
            resultado.at[indice, "deposito_produto_vencido"] = dados["deposito"]
            resultado.at[indice, "vcto_lote_produto_vencido"] = dados["vencimento"]
    return resultado


def ler_csv_produtos(arquivo) -> list[str]:
    conteudo = arquivo.getvalue()
    ultimo_erro: Exception | None = None
    for encoding in ("utf-8-sig", "latin1"):
        try:
            # O detector automático do pandas pode interpretar letras como
            # separador quando o CSV possui somente a coluna "produto".
            primeira_linha = conteudo.decode(encoding).splitlines()[0]
            separador = next(
                (sep for sep in (";", ",", "\t", "|") if sep in primeira_linha),
                ";",
            )
            df = pd.read_csv(
                io.BytesIO(conteudo),
                sep=separador,
                encoding=encoding,
                dtype=str,
            )
            break
        except Exception as erro:
            ultimo_erro = erro
    else:
        raise ValueError(f"Não foi possível ler o CSV: {ultimo_erro}")

    df.columns = [str(coluna).strip().lower() for coluna in df.columns]
    if "produto" not in df.columns:
        raise ValueError("O CSV precisa possuir uma coluna chamada 'produto'.")
    produtos = [p for p in df["produto"].map(normalizar_codigo).tolist() if p]
    return list(dict.fromkeys(produtos))


def calcular_comparacoes(produtos_upload, estrutura_upload, estrutura_pedidos):
    componentes_carteira = set(estrutura_pedidos["componente"].dropna())
    por_produto_pedido = {
        produto: set(grupo["componente"].dropna())
        for produto, grupo in estrutura_pedidos.groupby("produto")
    }
    resumo, detalhes = [], []

    for produto_upload in produtos_upload:
        componentes = set(estrutura_upload.loc[
            estrutura_upload["produto"] == produto_upload, "componente"
        ].dropna())
        componentes.discard("")
        presentes = componentes & componentes_carteira

        melhor_produto, melhor_itens, melhor_pct = "", set(), 0.0
        for produto_pedido, itens_pedido in por_produto_pedido.items():
            comuns = componentes & itens_pedido
            pct = 100 * len(comuns) / len(componentes) if componentes else 0.0
            if pct > melhor_pct or (pct == melhor_pct and len(comuns) > len(melhor_itens)):
                melhor_produto, melhor_itens, melhor_pct = produto_pedido, comuns, pct

        resumo.append({
            "produto_upload": produto_upload,
            "itens_estrutura_upload": len(componentes),
            "itens_presentes_na_carteira": len(presentes),
            "itens_ausentes_na_carteira": len(componentes - presentes),
            "percentual_presente": round(100 * len(presentes) / len(componentes), 2)
            if componentes else 0.0,
            "melhor_produto_pedido": melhor_produto,
            "percentual_melhor_produto": round(melhor_pct, 2),
        })
        for componente in sorted(componentes):
            detalhes.append({
                "produto_upload": produto_upload,
                "componente": componente,
                "presente_nas_estruturas_dos_pedidos": componente in componentes_carteira,
                "presente_no_melhor_produto": componente in melhor_itens,
                "melhor_produto_pedido": melhor_produto,
            })
    return pd.DataFrame(resumo), pd.DataFrame(detalhes)


def calcular_produtos_compativeis(
    produtos_upload, estrutura_upload, estrutura_pedidos, itens_pedidos=None,
    percentual_minimo=50.0
):
    """Lista todos os produtos do pedido com compatibilidade acima do limite."""
    componentes_pedido = {
        produto: set(grupo["componente"].dropna()) - {""}
        for produto, grupo in estrutura_pedidos.groupby("produto")
    }
    pedidos_por_produto = {}
    clientes_por_produto = {}
    itens_originais_por_produto = {}
    if itens_pedidos is not None and not itens_pedidos.empty:
        for produto, grupo in itens_pedidos.groupby("produto_base"):
            pedidos_clientes = sorted({
                (
                    normalizar_codigo(linha["nro_pedido"]),
                    normalizar_codigo(linha["cliente"]),
                )
                for _, linha in grupo.iterrows()
                if normalizar_codigo(linha["nro_pedido"])
            })
            pedidos_por_produto[produto] = " | ".join(
                pedido for pedido, _ in pedidos_clientes
            )
            clientes_por_produto[produto] = " | ".join(
                cliente for _, cliente in pedidos_clientes
            )
        itens_originais_por_produto = {
            produto: ", ".join(sorted({
                normalizar_codigo(codigo)
                for codigo in grupo["codigo_produto"].dropna()
                if normalizar_codigo(codigo)
            }))
            for produto, grupo in itens_pedidos.groupby("produto_base")
        }
    linhas = []
    for produto_upload in produtos_upload:
        componentes_upload = set(estrutura_upload.loc[
            estrutura_upload["produto"] == produto_upload, "componente"
        ].dropna()) - {""}
        if not componentes_upload:
            continue
        for produto_pedido, componentes in componentes_pedido.items():
            comuns = componentes_upload & componentes
            percentual = 100 * len(comuns) / len(componentes_upload)
            if percentual > percentual_minimo:
                linhas.append({
                    "produto_upload": produto_upload,
                    "produto_compativel_pedido": produto_pedido,
                    "item_pedido_original": itens_originais_por_produto.get(produto_pedido, ""),
                    "nro_pedido": pedidos_por_produto.get(produto_pedido, ""),
                    "cliente": clientes_por_produto.get(produto_pedido, ""),
                    "itens_estrutura_upload": len(componentes_upload),
                    "itens_em_comum": len(comuns),
                    "percentual_compatibilidade": round(percentual, 2),
                    "componentes_em_comum": ", ".join(sorted(comuns)),
                })
    colunas = [
        "produto_upload", "produto_compativel_pedido", "item_pedido_original", "nro_pedido",
        "cliente",
        "itens_estrutura_upload",
        "itens_em_comum", "percentual_compatibilidade", "componentes_em_comum",
    ]
    return pd.DataFrame(linhas, columns=colunas).sort_values(
        ["produto_upload", "percentual_compatibilidade"], ascending=[True, False]
    ) if linhas else pd.DataFrame(columns=colunas)


def para_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def subpage() -> None:
    st.markdown("""
        <style>
        .hero-estrutura {padding:24px 28px;border-radius:16px;margin-bottom:18px;
          background:linear-gradient(120deg,#123b5d,#1976a3);color:white;
          box-shadow:0 8px 24px rgba(18,59,93,.18)}
        .hero-estrutura h1 {font-size:29px;margin:0 0 7px 0;color:white}
        .hero-estrutura p {font-size:15px;margin:0;color:#e8f4fa}
        .info-analise {background:#f3f8fc;border-left:5px solid #1976a3;
          padding:14px 18px;border-radius:8px;margin:10px 0 20px}
        div[data-testid="stMetric"] {background:white;border:1px solid #dce7ef;
          padding:14px;border-radius:12px;box-shadow:0 3px 12px rgba(18,59,93,.07)}
        </style>
        <div class="hero-estrutura">
          <h1>Comparação de Estruturas × Carteira de Pedidos</h1>
          <p>Análise de similaridade para apoiar decisões de produção e aproveitamento da carteira.</p>
        </div>
        <div class="info-analise"><b>Como interpretar:</b> o sistema busca a estrutura dos
        produtos informados e verifica quantos de seus componentes aparecem nas estruturas dos
        itens de pedidos abertos. Também identifica todos os produtos com compatibilidade superior
        a 50%. A análise utiliza componentes distintos do primeiro nível da estrutura.</div>
    """, unsafe_allow_html=True)

    st.caption("Filtros fixos: PEDIDO 1/2 · ITENS_PEDIDO exceto 6/9 · SOFTDIB_ADEX")

    def limpar_analise():
        st.cache_data.clear()
        st.session_state.pop("estrutura_pedidos_csv", None)
        st.session_state["produtos_estrutura_manual"] = ""

    col_modo, col_limpar = st.columns([4, 1])
    with col_modo:
        modo_entrada = st.radio(
            "Origem dos produtos",
            ["Upload de CSV", "Informar produtos"],
            horizontal=True,
            key="modo_entrada_estrutura",
        )
    with col_limpar:
        st.write("")
        st.button(
            "Limpar análise",
            on_click=limpar_analise,
            use_container_width=True,
            help="Limpa o arquivo, os produtos informados e o cache das consultas.",
        )

    arquivo = None
    texto_produtos = ""
    if modo_entrada == "Upload de CSV":
        arquivo = st.file_uploader(
            "Selecione o CSV com a coluna produto", type=["csv"], key="estrutura_pedidos_csv"
        )
        st.caption("Exemplo: uma coluna chamada produto, com um código por linha.")
    else:
        texto_produtos = st.text_area(
            "Produtos específicos",
            placeholder="UL41BR006\nUL41Z205.200\nUL41Z319.200",
            help="Informe um código por linha. Também são aceitos vírgula ou ponto e vírgula.",
            height=140,
            key="produtos_estrutura_manual",
        )

    if not st.button("Analisar compatibilidade", type="primary", use_container_width=True):
        return

    try:
        if modo_entrada == "Upload de CSV":
            produtos_upload = ler_csv_produtos(arquivo) if arquivo is not None else []
        else:
            texto_normalizado = texto_produtos.replace(";", "\n").replace(",", "\n")
            produtos_upload = list(dict.fromkeys(
                normalizar_codigo(produto) for produto in texto_normalizado.splitlines()
                if normalizar_codigo(produto)
            ))
        if not produtos_upload:
            st.warning("Envie um CSV ou informe pelo menos um produto específico.")
            return
        with st.spinner("Consultando pedidos e estruturas..."):
            itens = consultar_itens_abertos()
            if itens.empty:
                st.warning("Nenhum item de pedido corresponde aos filtros.")
                return
            itens["codigo_produto"] = itens["codigo_produto"].map(normalizar_codigo)
            itens["produto_base"] = itens["codigo_produto"].map(extrair_produto_base)
            estrutura_pedidos = consultar_estruturas(tuple(itens["produto_base"].unique()))
            estrutura_upload = consultar_estruturas(tuple(produtos_upload))
            resumo, detalhes = calcular_comparacoes(
                produtos_upload, estrutura_upload, estrutura_pedidos
            )
            compativeis = calcular_produtos_compativeis(
                produtos_upload, estrutura_upload, estrutura_pedidos, itens, 50.0
            )
            produtos_compativeis = tuple(
                compativeis["produto_compativel_pedido"].dropna().unique()
            )
            ofs_abertas = consultar_ofs_abertas(produtos_compativeis)
            compativeis = adicionar_ofs_compativeis(compativeis, ofs_abertas)
            produtos_vencidos = consultar_produtos_vencidos(tuple(produtos_upload))
            compativeis = adicionar_produtos_vencidos(compativeis, produtos_vencidos)

        sem_estrutura = sorted(set(produtos_upload) - set(estrutura_upload["produto"]))
        if sem_estrutura:
            st.warning("Produtos do upload sem estrutura: " + ", ".join(sem_estrutura))

        st.markdown("### Resumo executivo")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pedidos", itens["nro_pedido"].nunique())
        c2.metric("Itens de pedido", len(itens))
        c3.metric("Produtos enviados", len(produtos_upload))
        media = resumo.loc[resumo["itens_estrutura_upload"] > 0, "percentual_presente"].mean()
        c4.metric("Cobertura média", f"{media:.2f}%" if pd.notna(media) else "0,00%")
        c5.metric("Compatibilidades > 50%", len(compativeis))

        st.markdown("### Visão gerencial por produto")
        colunas_principais = [
            "produto_upload", "itens_estrutura_upload", "itens_presentes_na_carteira",
            "itens_ausentes_na_carteira", "percentual_presente",
            "melhor_produto_pedido", "percentual_melhor_produto",
        ]
        st.dataframe(
            resumo[colunas_principais].style
                .format({"percentual_presente": "{:.2f}%",
                         "percentual_melhor_produto": "{:.2f}%"})
                .background_gradient(subset=["percentual_presente"], cmap="Blues")
                .background_gradient(subset=["percentual_melhor_produto"], cmap="Greens"),
            use_container_width=True, hide_index=True, height=min(600, 38 * len(resumo) + 40),
        )

        grafico = resumo.set_index("produto_upload")[[
            "percentual_presente", "percentual_melhor_produto"
        ]].rename(columns={
            "percentual_presente": "Presença na carteira (%)",
            "percentual_melhor_produto": "Melhor compatibilidade (%)",
        })
        st.bar_chart(grafico, horizontal=True, height=max(260, min(650, 42 * len(resumo))))

        st.markdown("### Produtos potencialmente compatíveis")
        st.caption(
            "São exibidos todos os produtos da carteira que possuem mais de 50% dos "
            "componentes da estrutura do produto analisado. As colunas de OF indicam se "
            "o produto compatível já possui ordem de fabricação com status A."
        )
        if compativeis.empty:
            st.info("Nenhum produto apresentou compatibilidade superior a 50%.")
        else:
            def exibir_tabela_compativeis():
                st.dataframe(
                    compativeis,
                    use_container_width=True,
                    hide_index=True,
                    height=max(190, min(620, 46 * len(compativeis) + 85)),
                    row_height=42,
                    column_config={
                        "produto_upload": st.column_config.TextColumn(
                            "Produto analisado", width="medium"
                        ),
                        "produto_compativel_pedido": st.column_config.TextColumn(
                            "Produto compatível", width="medium"
                        ),
                        "produto_vencido_compativel": st.column_config.TextColumn(
                            "Produto vencido compatível", width="medium"
                        ),
                        "quantidade_produto_vencido": st.column_config.TextColumn(
                            "Quantidade vencida", width="medium"
                        ),
                        "deposito_produto_vencido": st.column_config.TextColumn(
                            "Depósito do vencido", width="medium"
                        ),
                        "vcto_lote_produto_vencido": st.column_config.TextColumn(
                            "Vencimento do lote", width="medium"
                        ),
                        "item_pedido_original": st.column_config.TextColumn(
                            "Item original", width="medium"
                        ),
                        "nro_pedido": st.column_config.TextColumn("Nº pedido", width="medium"),
                        "cliente": st.column_config.TextColumn("Cliente", width="medium"),
                        "percentual_compatibilidade": st.column_config.ProgressColumn(
                            "Compatibilidade", format="%.2f%%", min_value=0, max_value=100,
                            width="medium",
                        ),
                        "componentes_em_comum": st.column_config.TextColumn(
                            "Componentes em comum", width="large"
                        ),
                        "tem_of_andamento": st.column_config.TextColumn("OF aberta"),
                        "nro_of": st.column_config.TextColumn("Nº OF", width="medium"),
                        "qtde_of": st.column_config.TextColumn(
                            "Quantidade da OF", width="medium"
                        ),
                        "data_abertura_of": st.column_config.TextColumn(
                            "Abertura da OF", width="medium"
                        ),
                    },
                )

            if modo_entrada == "Informar produtos":
                aba_visual, aba_tabela = st.tabs(["Visão rápida", "Tabela completa"])
                with aba_visual:
                    for _, compatibilidade in compativeis.iterrows():
                        titulo = (
                            f'{compatibilidade["produto_upload"]}  →  '
                            f'{compatibilidade["produto_compativel_pedido"]}'
                        )
                        with st.expander(titulo, expanded=len(compativeis) == 1):
                            v1, v2, v3, v4 = st.columns(4)
                            v1.metric(
                                "Compatibilidade",
                                f'{compatibilidade["percentual_compatibilidade"]:.2f}%',
                            )
                            v2.metric("Itens em comum", int(compatibilidade["itens_em_comum"]))
                            v3.metric(
                                "OF em andamento",
                                compatibilidade.get("tem_of_andamento", "Não"),
                            )
                            v4.metric(
                                "Nº da OF", compatibilidade.get("nro_of", "") or "—",
                            )
                            d1, d2 = st.columns(2)
                            d1.markdown(
                                f'**Item original do pedido:**  '
                                f'{compatibilidade["item_pedido_original"]}'
                            )
                            d1.markdown(f'**Nº do pedido:**  {compatibilidade["nro_pedido"]}')
                            d1.markdown(f'**Cliente:**  {compatibilidade["cliente"] or "—"}')
                            d2.markdown(
                                f'**Data de abertura da OF:**  '
                                f'{compatibilidade.get("data_abertura_of", "") or "—"}'
                            )
                            d2.markdown(
                                f'**Quantidade da OF:**  '
                                f'{compatibilidade.get("qtde_of", "") or "—"}'
                            )
                            st.markdown(
                                f'**Componentes em comum:**  '
                                f'{compatibilidade["componentes_em_comum"] or "—"}'
                            )
                with aba_tabela:
                    exibir_tabela_compativeis()
            else:
                exibir_tabela_compativeis()

        st.markdown("### Exportação")
        st.write("Após revisar a análise acima, baixe os resultados para tratamento adicional.")
        d1, d2 = st.columns(2)
        d1.download_button("Baixar resumo CSV", para_csv(resumo),
                           "comparacao_estruturas.csv", "text/csv", use_container_width=True)
        d2.download_button("Baixar compatibilidades CSV", para_csv(compativeis),
                           "produtos_compativeis.csv", "text/csv", use_container_width=True)

        st.markdown("### Memória da análise")
        with st.expander("Itens dos pedidos"):
            st.dataframe(itens, use_container_width=True, hide_index=True)
        with st.expander("Componentes presentes e ausentes"):
            st.dataframe(detalhes, use_container_width=True, hide_index=True)
        with st.expander("Estruturas dos produtos enviados"):
            st.dataframe(estrutura_upload, use_container_width=True, hide_index=True)
        with st.expander("Estruturas dos itens dos pedidos"):
            st.dataframe(estrutura_pedidos, use_container_width=True, hide_index=True)
        with st.expander("Ordens de fabricação em andamento"):
            if ofs_abertas.empty:
                st.info("Nenhuma OF com status A foi localizada para os produtos compatíveis.")
            else:
                st.dataframe(
                    ofs_abertas.style.format({"data_abertura": lambda data: data.strftime("%d/%m/%Y")
                                              if pd.notna(data) else ""}),
                    use_container_width=True,
                    hide_index=True,
                )
    except (ValueError, mysql.connector.Error) as erro:
        st.error(str(erro))
    except Exception as erro:
        st.exception(erro)


if __name__ == "__main__":
    st.set_page_config(page_title="Comparação de Estruturas", layout="wide")
    subpage()
