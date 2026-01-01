import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import qrcode
from io import BytesIO

# --- CONFIGURAÇÕES VISUAIS PEEGFLOW (DESIGN SYSTEM) ---
COLOR_PRIMARY = "#0056b3"
COLOR_ACCENT = "#dc3545"
COLOR_GOLD = "#ffc107"
BACKGROUND_LIGHT = "#f8f9fa"

st.set_page_config(
    page_title="PeegFlow | Intelligence",
    layout="wide",
    page_icon="logo.jpeg"
)

# --- CSS AVANÇADO ---
st.markdown(f"""
<style>
.stApp {{
    background-color: {BACKGROUND_LIGHT};
}}

.product-card {{
    background-color: white;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    border-bottom: 4px solid {COLOR_PRIMARY};
    margin-bottom: 20px;
}}

.stButton>button {{
    width: 100%;
    background-color: {COLOR_PRIMARY};
    color: white !important;
    border-radius: 10px;
    border: none;
    height: 45px;
    font-weight: bold;
    transition: 0.3s;
}}

.stButton>button:hover {{
    background-color: {COLOR_ACCENT};
    transform: translateY(-2px);
}}

[data-testid="stSidebar"] {{
    background-color: white;
    border-right: 1px solid #ddd;
}}

h1, h2, h3 {{
    font-family: 'Segoe UI', Roboto, sans-serif;
    color: {COLOR_PRIMARY} !important;
    font-weight: 800;
}}

.price-tag {{
    color: {COLOR_ACCENT};
    font-size: 1.2rem;
    font-weight: bold;
}}
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO DB ---
def get_connection():
    conn = sqlite3.connect("peegflow.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            name TEXT,
            price REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            mesa TEXT,
            product_name TEXT,
            price REAL,
            status TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()

init_db()
conn = get_connection()

# --- ROTEAMENTO ---
params = st.query_params

# =========================
# 🧑‍🍳 MODO CLIENTE (CARDÁPIO)
# =========================
if "cid" in params:

    st.markdown(

   col1, col2, col3 = st.columns([1,2,1])
   with col2:
    st.image("logo.jpeg", width=180)
    )

    st.markdown(
        f"<h2 style='text-align:center;'>PeegFlow <span style='color:{COLOR_ACCENT}'>Food</span></h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='text-align:center;'>Mesa {params['mesa']} | Experiência Digital</p>",
        unsafe_allow_html=True
    )

    st.divider()

    df_p = pd.read_sql_query(
        "SELECT * FROM products WHERE company_id=?",
        conn,
        params=(params["cid"],)
    )

    if df_p.empty:
        st.info("Aguardando ativação do cardápio pelo estabelecimento.")
    else:
        cols = st.columns(2)
        for i, row in df_p.iterrows():
            with cols[i % 2]:
                st.markdown(
                    f"""
                    <div class="product-card">
                        <h3>{row['name']}</h3>
                        <p class="price-tag">R$ {row['price']:.2f}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if st.button("Adicionar Pedido", key=f"btn_{row['id']}"):
                    conn.cursor().execute(
                        """
                        INSERT INTO orders
                        (company_id, mesa, product_name, price, status, timestamp)
                        VALUES (?,?,?,?,?,?)
                        """,
                        (
                            params["cid"],
                            params["mesa"],
                            row["name"],
                            row["price"],
                            "Pendente",
                            datetime.now().strftime("%H:%M"),
                        ),
                    )
                    conn.commit()
                    st.toast(
                        f"✅ {row['name']} enviado para a cozinha!",
                        icon="🚀"
                    )

# =========================
# 🧠 MODO GESTOR
# =========================
else:
    st.sidebar.image("logo.jpeg", width=160)

    st.sidebar.markdown(
        f"<h2 style='text-align:center; color:{COLOR_PRIMARY}'>PeegFlow</h2>",
        unsafe_allow_html=True
    )
    st.sidebar.markdown("---")

    menu = st.sidebar.radio(
        "FLUXO DE GESTÃO",
        [
            "📊 Monitor de Pedidos",
            "🍴 Gestão de Cardápio",
            "🖨️ QR Mesa",
            "⚙️ Setup PeegFlow",
        ],
    )

    if menu == "⚙️ Setup PeegFlow":
        st.title("⚙️ Configuração Inicial")
        st.info("Bem-vindo ao motor de inteligência PeegFlow.")

        if st.button("🚀 Inicializar Sistema Demo"):
            c = conn.cursor()
            c.execute("DELETE FROM products")
            c.execute("""
                INSERT INTO products (company_id, name, price)
                VALUES
                (1, 'Hambúrguer Gourmet', 35.90),
                (1, 'Batata Rústica', 18.00),
                (1, 'Shake de Morango', 12.00)
            """)
            conn.commit()
            st.success("Dados carregados com sucesso!")

    elif menu == "📊 Monitor de Pedidos":
        st.title("👨‍🍳 Painel de Fluxo")

        df_orders = pd.read_sql_query(
            "SELECT * FROM orders WHERE status='Pendente'",
            conn
        )

        if df_orders.empty:
            st.success("Fluxo limpo. Nenhum pedido pendente.")
        else:
            for mesa in df_orders["mesa"].unique():
                with st.expander(f"📍 Mesa {mesa}", expanded=True):
                    itens = df_orders[df_orders["mesa"] == mesa]
                    st.table(itens[["product_name", "price", "timestamp"]])
                    total = itens["price"].sum()
                    st.subheader(f"Total: R$ {total:.2f}")

                    if st.button(f"Finalizar Mesa {mesa}", type="primary"):
                        conn.cursor().execute(
                            "UPDATE orders SET status='Pago' WHERE mesa=?",
                            (mesa,),
                        )
                        conn.commit()
                        st.success(f"Mesa {mesa} finalizada!")
                        st.rerun()

    elif menu == "🍴 Gestão de Cardápio":
        st.title("📖 Cadastro de Produtos")

        with st.container(border=True):
            n = st.text_input("Nome do Prato/Bebida")
            p = st.number_input("Preço", min_value=0.0, step=1.0)

            if st.button("Salvar Produto"):
                conn.cursor().execute(
                    "INSERT INTO products (company_id, name, price) VALUES (1,?,?)",
                    (n, p),
                )
                conn.commit()
                st.success("Produto cadastrado!")

        st.divider()
        prods = pd.read_sql_query(
            "SELECT name AS Nome, price AS Preço FROM products",
            conn
        )
        st.dataframe(prods, use_container_width=True)

    elif menu == "🖨️ QR Mesa":
        st.title("📱 Gerador de QR Code")

        m_id = st.text_input("Identificador da Mesa", "01")

        if st.button("Gerar Código"):
            url = f"https://sistema-de-comandas-3bvbpkpawaa5pkbfuptqef.streamlit.app/?cid=1&mesa={m_id}"
            qr = qrcode.make(url)
            buf = BytesIO()
            qr.save(buf, format="PNG")

            st.image(buf.getvalue(), caption=f"Mesa {m_id}")
            st.markdown(f"**Link:** `{url}`")


