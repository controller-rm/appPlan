"""
Página Streamlit — Relatório Diário de Recuperação por Motivo
=================================================================
Exibe, por dia, a quantidade e o custo total recuperados na tabela
REQUISICOES, filtrando por cod_historico (padrão: '031'), status = 'R'
e numero_da_of preenchido (não vazio/nulo).

Colunas reais utilizadas (conforme DESCRIBE REQUISICOES):
    - data_abertura   -> data de referência (agrupamento por dia)
    - cod_historico   -> motivo (filtro, ex: '031')
    - status          -> status da requisição (filtro, ex: 'R')
    - numero_da_of    -> número da OF (filtro: apenas não vazio)
    - quantidade      -> quantidade requisitada/consumida
    - custo_total     -> valor (R$) correspondente
    - grupo_compl     -> filtro opcional de grupo
    - subgrupo_compl  -> filtro opcional de subgrupo

Como integrar ao seu app existente:
- Se seu app já é multipage (pasta `pages/`), copie este arquivo para
  `pages/XX_Recuperacao_Motivo031.py` dentro do seu projeto Streamlit.
- Se preferir chamar como função dentro de uma página já existente,
  importe `render()` e chame onde quiser.
- Requer: streamlit, mysql-connector-python, pandas, python-dotenv, plotly,
  kaleido (para exportar o gráfico como imagem no PDF), reportlab (montagem do PDF)

    pip install streamlit mysql-connector-python pandas python-dotenv plotly kaleido reportlab
"""

import os
from datetime import date, timedelta

import mysql.connector
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

# =========================================================
# .ENV / CREDENCIAIS
# =========================================================
load_dotenv()
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT") or 3306)
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")


# =========================================================
# CONEXÃO
# =========================================================
def connect_to_mysql():
    try:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
        )
    except Exception as e:
        st.error(f"Erro ao conectar no MySQL: {e}")
        return None


# =========================================================
# CONSULTA (cacheada por 5 minutos para não sobrecarregar o banco)
# =========================================================
@st.cache_data(ttl=300, show_spinner="Consultando recuperações...")
def buscar_recuperacoes(
    cod_historico: str,
    data_inicio: date,
    data_fim: date,
    grupo_compl: str = "",
    subgrupo_compl: str = "",
    status: str = "R",
) -> pd.DataFrame:
    conn = connect_to_mysql()
    if conn is None:
        return pd.DataFrame()

    # ---------------------------------------------------------------
    # Filtros:
    #   - cod_historico = '031'
    #   - status = 'R'
    #   - numero_da_of preenchido (não vazio/nulo)
    #   - data_abertura dentro do período
    #   - grupo_compl / subgrupo_compl opcionais (só aplica se informado)
    # ---------------------------------------------------------------
    query = """
        SELECT
            DATE(data_abertura)  AS data_ref,
            SUM(quantidade)      AS quantidade_total,
            SUM(custo_total)     AS valor_reais
        FROM REQUISICOES
        WHERE cod_historico = %s
          AND status = %s
          AND numero_da_of IS NOT NULL
          AND TRIM(numero_da_of) <> ''
          AND data_abertura BETWEEN %s AND %s
    """
    params = [cod_historico, status, data_inicio, data_fim]

    if grupo_compl:
        query += " AND grupo_compl = %s"
        params.append(grupo_compl)

    if subgrupo_compl:
        query += " AND subgrupo_compl = %s"
        params.append(subgrupo_compl)

    query += " GROUP BY DATE(data_abertura) ORDER BY data_ref"

    try:
        df = pd.read_sql(query, conn, params=tuple(params))
    except Exception as e:
        st.error(f"Erro ao executar a consulta: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

    # Garante que todos os dias do período apareçam, mesmo sem movimento
    todos_dias = pd.DataFrame({"data_ref": pd.date_range(data_inicio, data_fim, freq="D")})
    if not df.empty:
        df["data_ref"] = pd.to_datetime(df["data_ref"])
    df = todos_dias.merge(df, on="data_ref", how="left").fillna(0)
    df = df.rename(columns={"quantidade_total": "quantidade_kg"})

    return df


@st.cache_data(ttl=600, show_spinner=False)
def buscar_opcoes_filtro(coluna: str) -> list:
    """Busca valores distintos e não vazios de uma coluna, para popular os selects."""
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        query = f"""
            SELECT DISTINCT {coluna} AS valor
            FROM REQUISICOES
            WHERE {coluna} IS NOT NULL AND TRIM({coluna}) <> ''
            ORDER BY {coluna}
        """
        df = pd.read_sql(query, conn)
        return df["valor"].tolist()
    except Exception:
        return []
    finally:
        conn.close()


# =========================================================
# GRÁFICO (barras = kg, linha = R$) — estilo do relatório exemplo
# =========================================================
def montar_grafico(df: pd.DataFrame) -> go.Figure:
    dias = df["data_ref"].dt.strftime("%d/%m").tolist()
    qtd = df["quantidade_kg"].astype(float).tolist()
    val = df["valor_reais"].astype(float).tolist()

    max_qtd = max(qtd) if qtd and max(qtd) > 0 else 1
    max_val = max(val) if val and max(val) > 0 else 1

    fig = go.Figure()

    # As séries são desenhadas sem textos nativos. Os valores são incluídos
    # por annotations para termos controle total sobre posição, cor e recuo.
    fig.add_trace(
        go.Bar(
            x=dias,
            y=qtd,
            name="Quantidade (kg)",
            marker_color="#2E75D6",
            marker_line_width=0,
            width=0.55,
            yaxis="y",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Quantidade: %{y:,.0f} kg<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dias,
            y=val,
            name="Valor (R$)",
            mode="lines+markers",
            line=dict(color="#1B9E4B", width=3.5, shape="spline", smoothing=0.4),
            marker=dict(size=11, color="white", line=dict(color="#1B9E4B", width=3)),
            yaxis="y2",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>",
        )
    )

    # Quantidades:
    # - barras com altura suficiente: texto dentro da barra, em branco;
    # - barras pequenas: texto acima da barra, em azul escuro.
    limite_interno = max(max_qtd * 0.075, 20)

    for dia, quantidade in zip(dias, qtd):
        if quantidade <= 0:
            continue

        dentro = quantidade >= limite_interno
        fig.add_annotation(
            x=dia,
            y=quantidade,
            xref="x",
            yref="y",
            text=f"<b>{fmt_kg(quantidade)}</b>",
            showarrow=False,
            xanchor="center",
            yanchor="top" if dentro else "bottom",
            yshift=-10 if dentro else 8,
            font=dict(
                size=15,
                color="#FFFFFF" if dentro else "#1B4B8C",
                family="Arial Black, Arial, sans-serif",
            ),
        )

    # Valores em R$:
    # Sempre acima do marcador, dentro de uma pequena caixa branca.
    # Assim, rótulos de valores baixos não ficam abaixo do eixo nem são cortados.
    for dia, valor in zip(dias, val):
        if valor <= 0:
            continue

        fig.add_annotation(
            x=dia,
            y=valor,
            xref="x",
            yref="y2",
            text=f"<b>{fmt_reais(valor)}</b>",
            showarrow=False,
            xanchor="center",
            yanchor="bottom",
            yshift=16,
            font=dict(
                color="#138A3D",
                size=13,
                family="Arial Black, Arial, sans-serif",
            ),
            bgcolor="rgba(255,255,255,0.94)",
            bordercolor="rgba(27,158,75,0.30)",
            borderwidth=1,
            borderpad=3,
        )

    fig.update_layout(
        xaxis=dict(
            tickfont=dict(size=14, color="#333333"),
            showgrid=False,
            showline=True,
            linecolor="#DDDDDD",
            automargin=True,
        ),
        yaxis=dict(
            title=dict(text="Quantidade (kg)", font=dict(size=15, color="#1B4B8C")),
            side="left",
            showgrid=True,
            gridcolor="#F0F0F0",
            gridwidth=1,
            tickfont=dict(size=13, color="#1B4B8C"),
            range=[0, max_qtd * 1.35],
            zeroline=False,
            automargin=True,
        ),
        yaxis2=dict(
            title=dict(text="Valor (R$)", font=dict(size=15, color="#1B9E4B")),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=13, color="#1B9E4B"),
            range=[0, max_val * 1.45],
            zeroline=False,
            automargin=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.06,
            xanchor="center",
            x=0.5,
            font=dict(size=15),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(t=105, b=65, l=70, r=90),
        height=540,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=14, family="Arial, sans-serif"),
        bargap=0.35,
        hovermode="x unified",
    )

    return fig


# =========================================================
# FORMATAÇÃO AUXILIAR
# =========================================================
def fmt_reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_kg(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


# =========================================================
# GERAÇÃO DE PDF
# =========================================================
def gerar_pdf(df: pd.DataFrame, fig: go.Figure, programa: str, periodo_str: str) -> bytes:
    """Monta um PDF com título, gráfico (como imagem) e tabela de dados."""
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    )

    # Gráfico -> PNG em memória (requer pacote "kaleido" instalado)
    img_bytes = fig.to_image(format="png", width=1400, height=650, scale=2)
    img_buffer = io.BytesIO(img_bytes)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Recuperação por Dia (Motivo -031)", styles["Title"]))
    story.append(Paragraph(f"Programa: {programa}  |  Período: {periodo_str}", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Image(img_buffer, width=25 * cm, height=11.6 * cm))
    story.append(Spacer(1, 14))

    # Tabela (dias nas colunas, igual à exibida no Streamlit)
    dias = df["data_ref"].dt.strftime("%d/%m").tolist()
    qtd = df["quantidade_kg"].tolist()
    val = df["valor_reais"].tolist()

    total_kg = sum(qtd)
    total_val = sum(val)

    header = ["Data"] + dias + ["TOTAL"]
    linha_qtd = ["Qtd (kg)"] + [fmt_kg(v) for v in qtd] + [fmt_kg(total_kg)]
    linha_val = ["Valor (R$)"] + [fmt_reais(v) for v in val] + [fmt_reais(total_val)]

    tabela_dados = [header, linha_qtd, linha_val]
    n_dias = len(dias)
    largura_disponivel = 25 * cm
    largura_label = 2.6 * cm
    largura_total_col = 2.4 * cm
    largura_dia = (largura_disponivel - largura_label - largura_total_col) / n_dias
    col_widths = [largura_label] + [largura_dia] * n_dias + [largura_total_col]

    tabela = Table(tabela_dados, colWidths=col_widths, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (-1, 0), (-1, -1), colors.HexColor("#EAEAEA")),
        ("FONTNAME", (-1, 0), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
    ]))
    story.append(tabela)
    story.append(Spacer(1, 14))

    resumo = (
        f"<b>Total Recuperado (kg):</b> {fmt_kg(total_kg)} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Total Recuperado (R$):</b> {fmt_reais(total_val)} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Período:</b> {periodo_str}"
    )
    story.append(Paragraph(resumo, styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"<i>* Relatório gerado automaticamente em {pd.Timestamp.now().strftime('%d/%m/%Y às %H:%M')}</i>",
        styles["Normal"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# PÁGINA STREAMLIT
# =========================================================
def render():
    st.set_page_config(page_title="Recuperação por Dia", layout="wide")

    st.title("Recuperação por Dia (Motivo -031)")

    with st.sidebar:
        st.header("Filtros")
        cod_historico = st.text_input("Código do Histórico", value="031")
        status = st.text_input("Status", value="R")
        programa = st.text_input("Programa (rótulo exibido)", value="SGM415")
        data_fim = st.date_input("Data final", value=date.today())
        data_inicio = st.date_input("Data inicial", value=date.today() - timedelta(days=8))

        opcoes_grupo = ["(Todos)"] + buscar_opcoes_filtro("grupo_compl")
        grupo_sel = st.selectbox("Grupo Compl.", opcoes_grupo)
        grupo_compl = "" if grupo_sel == "(Todos)" else grupo_sel

        opcoes_subgrupo = ["(Todos)"] + buscar_opcoes_filtro("subgrupo_compl")
        subgrupo_sel = st.selectbox("Subgrupo Compl.", opcoes_subgrupo)
        subgrupo_compl = "" if subgrupo_sel == "(Todos)" else subgrupo_sel

        atualizar = st.button("🔄 Atualizar relatório", use_container_width=True)

    if atualizar:
        buscar_recuperacoes.clear()
        buscar_opcoes_filtro.clear()

    if data_inicio > data_fim:
        st.warning("A data inicial não pode ser maior que a data final.")
        return

    df = buscar_recuperacoes(
        cod_historico, data_inicio, data_fim,
        grupo_compl=grupo_compl, subgrupo_compl=subgrupo_compl, status=status,
    )

    if df.empty:
        st.info("Nenhum dado encontrado para o período e código informados.")
        return

    st.caption(
        f"Programa: **{programa}**  |  Período: **{data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')}**"
    )

    st.plotly_chart(montar_grafico(df), use_container_width=True)

    # -------------------- Tabela detalhada --------------------
    tabela = df.copy()
    tabela["Data"] = tabela["data_ref"].dt.strftime("%d/%m")
    tabela_exibicao = tabela[["Data", "quantidade_kg", "valor_reais"]].rename(
        columns={"quantidade_kg": "Qtd (kg)", "valor_reais": "Valor (R$)"}
    )

    total_kg = df["quantidade_kg"].sum()
    total_valor = df["valor_reais"].sum()

    linha_total = pd.DataFrame(
        [{"Data": "TOTAL", "Qtd (kg)": total_kg, "Valor (R$)": total_valor}]
    )
    tabela_final = pd.concat([tabela_exibicao, linha_total], ignore_index=True)
    tabela_final["Qtd (kg)"] = tabela_final["Qtd (kg)"].apply(fmt_kg)
    tabela_final["Valor (R$)"] = tabela_final["Valor (R$)"].apply(fmt_reais)

    st.dataframe(tabela_final.set_index("Data").T, use_container_width=True)

    # -------------------- Cards de resumo --------------------
    periodo_str = f"{data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')}"

    st.markdown(
        f"""
        <style>
        .card-resumo {{
            display: flex;
            align-items: center;
            gap: 16px;
            background: white;
            border: 1px solid #E3E3E3;
            border-radius: 10px;
            padding: 16px 22px;
            height: 88px;
        }}
        .card-icone {{
            width: 46px;
            height: 46px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }}
        .card-texto .card-label {{
            font-size: 13px;
            color: #666666;
            margin: 0 0 4px 0;
            white-space: nowrap;
        }}
        .card-texto .card-valor {{
            font-size: 22px;
            font-weight: 700;
            margin: 0;
            white-space: nowrap;
        }}
        </style>
        <div style="display:flex; gap:16px;">
            <div class="card-resumo" style="flex:1;">
                <div class="card-icone" style="background:#2E75D6;">⚖️</div>
                <div class="card-texto">
                    <p class="card-label">TOTAL RECUPERADO (KG)</p>
                    <p class="card-valor" style="color:#1B4B8C;">{fmt_kg(total_kg)} kg</p>
                </div>
            </div>
            <div class="card-resumo" style="flex:1;">
                <div class="card-icone" style="background:#1B9E4B;">💲</div>
                <div class="card-texto">
                    <p class="card-label">TOTAL RECUPERADO (R$)</p>
                    <p class="card-valor" style="color:#1B9E4B;">{fmt_reais(total_valor)}</p>
                </div>
            </div>
            <div class="card-resumo" style="flex:1;">
                <div class="card-icone" style="background:#F0F0F0;">📅</div>
                <div class="card-texto">
                    <p class="card-label">PERÍODO</p>
                    <p class="card-valor" style="color:#1B2A4A;">{periodo_str}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(f"* Relatório gerado automaticamente em {pd.Timestamp.now().strftime('%d/%m/%Y às %H:%M')}")

    # -------------------- Exportar PDF --------------------
    st.divider()
    if st.button("📄 Gerar PDF do relatório"):
        with st.spinner("Gerando PDF..."):
            try:
                pdf_bytes = gerar_pdf(df, montar_grafico(df), programa, periodo_str)
                st.download_button(
                    label="⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"recuperacao_motivo_031_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")


if __name__ == "__main__":
    render()