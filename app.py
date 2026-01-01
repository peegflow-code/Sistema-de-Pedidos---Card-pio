import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import qrcode
from io import BytesIO

# --- CONFIGURAÇÕES DO BANCO ---
def get_connection():
    conn = sqlite3.connect('sistema_comanda.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = get_connection().cursor()
    c.execute('CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY, name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY, company_id INTEGER, mesa TEXT, 
                  product_name TEXT, price REAL, status TEXT, timestamp TEXT)''')
    get_connection().commit()

init_db()

# --- FUNÇÕES AUXILIARES ---
def gerar_qr(cid, mesa):
    # 1. Removido o 'https://' duplicado
    # 2. Adicionado os parâmetros ?cid={cid}&mesa={mesa} ao final do link
    base_url = "https://sistema-de-comandas-3bvbpkpawaa5pkbfuptqef.streamlit.app/"
    url_final = f"{base_url}?cid={cid}&mesa={mesa}"
    
    qr = qrcode.make(url_final)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()
    
def gerar_layout_cupom(mesa, itens, total):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_cupom = f"""
    <div style="width: 280px; font-family: monospace; font-size: 12px; padding: 10px; background: white; color: black; border: 1px solid #ccc;">
        <div style="text-align: center;">
            <strong style="font-size: 14px;">DEMO RESTAURANTE</strong><br>
            --------------------------------<br>
            <strong>CONTA MESA: {mesa}</strong><br>
            {agora}<br>
            --------------------------------
        </div>
        <table style="width: 100%;">
            {''.join([f"<tr><td>{row['product_name']}</td><td style='text-align: right;'>{row['price']:.2f}</td></tr>" for _, row in itens.iterrows()])}
        </table>
        <div style="text-align: center;">
            --------------------------------<br>
            <strong style="font-size: 14px;">TOTAL: R$ {total:.2f}</strong><br>
            --------------------------------<br>
            Obrigado pela preferência!
        </div>
    </div>
    """
    return html_cupom

# --- ROTEAMENTO (CLIENTE VS GESTOR) ---
params = st.query_params

if "cid" in params:
    # --- MODO CLIENTE (QR CODE) ---
    cid = int(params["cid"])
    mesa = params["mesa"]
    st.title(f"🍴 Cardápio Digital")
    st.subheader(f"Mesa {mesa}")

    conn = get_connection()
    df_prods = pd.read_sql_query("SELECT * FROM products WHERE company_id=?", conn, params=(cid,))

    for _, row in df_prods.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{row['name']}**")
            col1.write(f"R$ {row['price']:.2f}")
            if col2.button("Pedir", key=f"btn_{row['id']}"):
                c = conn.cursor()
                c.execute('''INSERT INTO orders (company_id, mesa, product_name, price, status, timestamp) 
                             VALUES (?, ?, ?, ?, ?, ?)''', 
                          (cid, mesa, row['name'], row['price'], "Pendente", datetime.now().strftime("%H:%M")))
                conn.commit()
                st.success("Pedido enviado!")

    with st.expander("Ver Minha Comanda"):
        pedidos = pd.read_sql_query("SELECT product_name, price FROM orders WHERE company_id=? AND mesa=? AND status='Pendente'", 
                                   conn, params=(cid, mesa))
        if not pedidos.empty:
            st.dataframe(pedidos, hide_index=True)
            st.write(f"**Total: R$ {pedidos['price'].sum():.2f}**")

else:
    # --- MODO GESTOR ---
    st.sidebar.title("🏪 Gestão de Restaurante")
    menu = st.sidebar.radio("Navegação", ["Cozinha", "Gerenciar Cardápio", "Gerar QR Codes", "Config/Demo"])
    conn = get_connection()

    if menu == "Config/Demo":
        st.title("Configuração de Demo")
        if st.button("✨ Criar Dados de Exemplo"):
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO companies (id, name) VALUES (1, "Restaurante Local")')
            c.execute('DELETE FROM products WHERE company_id=1')
            c.execute('INSERT INTO products (company_id, name, price) VALUES (1, "Pizza Marguerita", 45.00), (1, "Cerveja Lata", 8.00), (1, "Suco Natural", 10.00)')
            conn.commit()
            st.success("Dados da Empresa ID 1 criados!")

    elif menu == "Cozinha":
        st.title("👨‍🍳 Pedidos e Fechamento")
        # Listar mesas que têm pedidos pendentes
        mesas_ativas = pd.read_sql_query("SELECT DISTINCT mesa FROM orders WHERE company_id=1 AND status='Pendente'", conn)
        
        if mesas_ativas.empty:
            st.info("Nenhuma mesa com pedidos ativos.")
        else:
            for _, m_row in mesas_ativas.iterrows():
                m_nome = m_row['mesa']
                with st.expander(f"Mesa {m_nome}", expanded=True):
                    itens_mesa = pd.read_sql_query("SELECT id, product_name, price, timestamp FROM orders WHERE mesa=? AND status='Pendente' AND company_id=1", conn, params=(m_nome,))
                    st.table(itens_mesa[['timestamp', 'product_name', 'price']])
                    
                    total_mesa = itens_mesa['price'].sum()
                    col1, col2 = st.columns(2)
                    
                    if col1.button(f"Imprimir Conta Mesa {m_nome}"):
                        cupom = gerar_layout_cupom(m_nome, itens_mesa, total_mesa)
                        st.markdown(cupom, unsafe_allow_html=True)
                        # Comando de impressão
                        st.components.v1.html("<script>window.print();</script>", height=0)
                    
                    if col2.button(f"Finalizar e Pagar Mesa {m_nome}", type="primary"):
                        c = conn.cursor()
                        c.execute("UPDATE orders SET status='Pago' WHERE mesa=? AND company_id=1", (m_nome,))
                        conn.commit()
                        st.rerun()

    elif menu == "Gerenciar Cardápio":
        st.title("📖 Cardápio")
        with st.form("novo_prod"):
            nome = st.text_input("Nome do Prato")
            preco = st.number_input("Preço", min_value=0.0)
            if st.form_submit_button("Adicionar"):
                conn.cursor().execute("INSERT INTO products (company_id, name, price) VALUES (1, ?, ?)", (nome, preco))
                conn.commit()
                st.rerun()
        df_p = pd.read_sql_query("SELECT * FROM products WHERE company_id=1", conn)
        st.dataframe(df_p, use_container_width=True)

    elif menu == "Gerar QR Codes":
        st.title("📱 Gerador de QR Code por Mesa")
        m_num = st.text_input("Número da Mesa", "1")
        if st.button("Gerar Código"):
            img = gerar_qr(1, m_num) # Usando ID 1 da demo
            st.image(img, caption=f"QR Code da Mesa {m_num}")
            st.download_button("Baixar PNG", img, file_name=f"qr_mesa_{m_num}.png")