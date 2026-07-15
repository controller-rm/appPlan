import streamlit as st
import pandas as pd  # Importando a biblioteca pandas
import matplotlib.pyplot as plt
import base64
from streamlit_option_menu import option_menu
import app_necessidade_materiais
from PIL import Image


# Configuração da página
st.set_page_config(
    page_title="Controller_Login",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
    
)
##### Oculta o botão Deploy do Streamilit
st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True
)
##### Remover o cabeçalho da pagina

REMOVE_PADDING_FROM_SIDES="""
<style>
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
    }   
</style>
"""
st.markdown(REMOVE_PADDING_FROM_SIDES, unsafe_allow_html=True)

# Função para carregar a imagem de fundo
def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# CSS para imagem de fundo
image_path = "Auditor.png"
base64_image = get_base64_image(image_path)
st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9)), 
                    url('data:image/png;base64,{base64_image}') no-repeat center center fixed;
        background-size: cover;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Estilos CSS Contorno dos campo stTextInput
st.markdown("""
<style>
    .stTextInput input {
        border: 3px solid #C0C0C0;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Estilos CSS cor e tamanho do botão stButton button
st.markdown("""
    <style>
    .stButton button {
        width: 100% !important;
        background-color: #808080 !important;
        color: white !important;
        font-size: 18px !important;
        padding: 10px;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# Estado da aplicação
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Função para a tela de login
def login_page():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:

        df = pd.read_csv("Lk-grupo.csv", sep=';')  # O arquivo deve estar no mesmo diretório que o script

        # Verifique se as colunas existem
        if 'LK_GRUPO' not in df.columns or 'username' not in df.columns or 'password' not in df.columns:
            st.error("Uma ou mais colunas necessárias não foram encontradas no arquivo CSV.")
            return  # Saia da função se as colunas não existirem

        # Remover espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Converter colunas para string e tratar valores nulos
        df['LK_GRUPO'] = df['LK_GRUPO'].astype(str).str.strip()
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()

        # Extrair as empresas da coluna 'LK_GRUPO'
        companies = df['LK_GRUPO'].tolist()  # Usando o nome correto da coluna

        # Exibir a imagem
        image = plt.imread("Controller.png")
        st.image(image)
        st.markdown("<p style='margin-top: -40px; margin-bottom: 10px;'>" "</p>", unsafe_allow_html=True)

        # Inputs de login
       
        company = st.selectbox("Empresa:", options=companies,disabled=True)   # Usando selectbox para selecionar a empresa
        username = st.text_input("Usuário:", max_chars=10).strip()  # Remover espaços em branco
        password = st.text_input("Senha:", type="password", max_chars=6).strip()  # Remover espaços em branco

        # Botão de acesso
        if st.button("ACESSAR"):
            # Verificar se as credenciais estão corretas
            user_data = df[(df['LK_GRUPO'] == company) & 
                            (df['username'] == username) & 
                            (df['password'] == password)]
            
            # # Debug: imprimir os dados que estão sendo verificados
            # st.write("Verificando:", company, username, password)
            # st.write("Dados encontrados:", user_data)

            if not user_data.empty:  # Se a consulta retornar dados, o login é bem-sucedido
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Login bem-sucedido!")
            else:
                st.error("Login falhou. Por favor, tente novamente.")

# Função para o menu principal
def menu_page():
    st.title("Menu Principal")
    st.write(f"Bem-vindo, {st.session_state.username}!")
    st.write("Aqui está o conteúdo do menu principal.")
    if st.button("Sair"):
        st.session_state.authenticated = False

# Verificar autenticação
if st.session_state.authenticated:
    class MultiApp:
        def __init__(self):
            self.apps = []

        def add_app(self, title, function):
            self.apps.append({
                "title": title,
                "function": function
            })

        def run(self):
            # Criar o menu principal na barra lateral
            with st.sidebar:
                # Exibir a imagem na barra lateral
                st.image("Controller.png", use_container_width=True)

                # Menu principal # ----------------------------------- Menu Principal ----------------
                selected_page = option_menu(
                    menu_title="Controller_Virtual",  # Título do menu
                    options=["MENU","PRODUCAO"],  # Opções do menu
                    icons=["house", "file-earmark-text", "gear","cash-coin","bi-bar-chart-steps"],  # Ícones correspondentes às opções https://icons.getbootstrap.com/
                    menu_icon="none",  # Ícone do menu (não será visível devido à imagem)
                    default_index=0,  # Índice da opção selecionada por padrão
                    styles={
                        "container": {"padding": "0!important", "background-color": "#f0f0f0"},
                        "icon": {"color": "black", "font-size": "20px"},
                        "nav-link": {
                            "font-size": "16px",
                            "text-align": "left",
                            "margin": "0px",
                            "--hover-color": "#eee",
                        },
                        "nav-link-selected": {"background-color": "grey"},
                        "menu-title": {"font-size": "20px", "color": "black", "text-align": "center"}  # Ajustar o tamanho da fonte e cor do título do menu
                    },
                )

            # Exibir conteúdo de acordo com a opção selecionada
            if selected_page:
                    
                st.markdown(f"<h1 style='font-size: 20px;'>{selected_page}</h1>", unsafe_allow_html=True)
                if selected_page =="MENU":
                    #st.image("Controller.png", use_column_width=True)
                    #st.write("Conteúdo da Página 3")
                    # Abrir a imagem
                    img = Image.open("Controller_virtual-PR.png").convert("RGBA")

                    # Ajustar transparência
                    alpha = 100  # Valor entre 0 (transparente) e 255 (opaco)
                    new_data = [(r, g, b, alpha) for r, g, b, a in img.getdata()]
                    img.putdata(new_data)

                    # Salvar a imagem temporária ou usar diretamente
                    img.save("Controller_virtual-PR.png")
                    # Redimensionar a imagem
                    img_resized = img.resize((700, 700))  # Largura e altura específicas
           
                    # Salvar ou usar diretamente
                    img_resized.save("Controller_virtual_resized.png")
                    st.image("Controller_virtual_resized.png")
                    #st.image("Controller_virtual.png", use_container_width=True)
                    
    ###### CSS para definir a imagem de fundo [INICIO]

                # Função para ler a imagem e convertê-la para base64
                    def get_base64_image(image_path):
                        with open(image_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode()
                        return encoded_string

                    # Caminho da imagem
                    image_path = "Auditor.png"
                    # Codificação da imagem em base64
                    base64_image = get_base64_image(image_path)

                    # CSS para definir a imagem de fundo com transparência
                    st.markdown(
                        f"""
                        <style>
                        .stApp {{
                            background: linear-gradient(rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9)), url('data:image/png;base64,{base64_image}') no-repeat center center fixed;
                            background-size: cover;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
    ###### CSS para definir a imagem de fundo [Fim]

    ###### Conteudo Submenu [INICIO] - ordemfabricacao

                # Adicionar subpáginas se uma página estiver selecionada
                if selected_page == "PRODUCAO":
                    
                    with st.sidebar:
                        subpage = option_menu(
                            menu_title="Subpáginas PRODUCAO",  # Título do submenu
                            options=["INICIO","Necessidade"],  # Opções do submenu
                            icons=["none","caret-right-fill", "caret-right-fill","caret-right-fill"],  # Sem ícones para o submenu
                            menu_icon="cast",  # Ícone do submenu (não será visível)
                            default_index=0,  # Índice da opção selecionada por padrão
                            styles={
                                "container": {"padding": "0!important", "background-color": "#f0f0f0"},
                                "icon": {"color": "black", "font-size": "12px"},
                                "nav-link": {
                                    "font-size": "12px",
                                    "text-align": "left",
                                    "margin": "0px",
                                    "--hover-color": "#eee",
                                },
                                "nav-link-selected": {"background-color": "grey"},
                                "menu-title": {"font-size": "14px", "color": "black", "text-align": "center"}  # Ajustar o tamanho da fonte e cor do título do menu
                            },
                            
                        )
                    # Conteúdo do submenu Inicio
                    if subpage == "INICIO":

                        st.write("Selecione as tarefas de sua preferencia") # Alterar as instruções
                        st.markdown("""
                        Esse campo é destinado a instruções sobre a utilização do Paineil Lista Adex.
                       
                        """)

    ###### CSS para definir a imagem de fundo - ordemfabricacao                   

                # Função para ler a imagem e convertê-la para base64
                    def get_base64_image(image_path):
                        with open(image_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode()
                        return encoded_string

                    # Caminho da imagem
                    image_path = "Auditor.png"
                    # Codificação da imagem em base64
                    base64_image = get_base64_image(image_path)

                    # CSS para definir a imagem de fundo com transparência
                    st.markdown(
                        f"""
                        <style>
                        .stApp {{
                            background: linear-gradient(rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9)), url('data:image/png;base64,{base64_image}') no-repeat center center fixed;
                            background-size: cover;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
    ######  Definir Subpasta do Menu - ordemfabricacao                              
                    # Conteúdo do submenu
                    if subpage == "Necessidade":
                        app_necessidade_materiais.subpage()
                        #st.write("Conteúdo da Subpágina 1.1")

   
                    # elif subpage == "Grf":
                    #     formulaBC.subpage()
                    #     #st.write("Conteúdo da Subpágina 1.2")

################################################################# Conteudo Submenu [Fim] - GERENCIADOR

    # Criar um objeto da classe MultiApp
    app = MultiApp()

    # Chamar a função run com o objeto da classe
    app.run()

else:
    login_page()



