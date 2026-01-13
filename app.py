import streamlit as st
import pandas as pd
import sqlite3
import random
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="PeegFlow ERP", layout="wide", page_icon="🔹")

# Paleta PeegFlow
CORES = {
    'Azul': '#4169E1', 'Vermelho': '#D50000', 'Amarelo': '#FFD700', 
    'Cinza': '#E0E0E0', 'Verde': '#2E7D32', 'Roxo': '#6A1B9A',
    'Fundo': '#F0F2F6'
}

# --- CAMADA DE DADOS ---

def init_db():
    """Cria a estrutura do banco se não existir"""
    conn = sqlite3.connect('peegflow.db')
    c = conn.cursor()
    
    # Tabelas
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY, usuario TEXT, senha TEXT, nome TEXT, cargo TEXT, perfil TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY, nome TEXT, cpf_cnpj TEXT, setor TEXT, 
                    porte TEXT, filiais INTEGER, endereco TEXT, email TEXT, data_cadastro DATE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS contratos (
                    id INTEGER PRIMARY KEY, cliente_id INTEGER, tipo TEXT, valor_total REAL, 
                    qtd_parcelas INTEGER, inicio DATE, fim DATE, status TEXT,
                    FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS projetos (
                    id INTEGER PRIMARY KEY, contrato_id INTEGER, nome TEXT, 
                    inicio DATE, fim DATE, status TEXT, responsavel TEXT,
                    FOREIGN KEY(contrato_id) REFERENCES contratos(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tarefas (
                    id INTEGER PRIMARY KEY, projeto_id INTEGER, descricao TEXT, tipo TEXT,
                    data_limite DATE, responsavel TEXT, status TEXT, data_conclusao DATE,
                    FOREIGN KEY(projeto_id) REFERENCES projetos(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY, contrato_id INTEGER, tipo TEXT, categoria TEXT, 
                    valor REAL, data_vencimento DATE, status TEXT,
                    FOREIGN KEY(contrato_id) REFERENCES contratos(id))''')
    
    # Cria admin padrão se vazio
    c.execute("SELECT count(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios (usuario, senha, nome, cargo, perfil) VALUES (?,?,?,?,?)",
                  ("admin", "123", "Carlos Gestor", "CEO", "admin"))
        
    conn.commit()
    conn.close()

def gerar_demo_robusta():
    """Popula o banco com 20 clientes, histórico financeiro e tarefas"""
    conn = sqlite3.connect('peegflow.db')
    c = conn.cursor()
    
    # Evita duplicidade se já rodou
    c.execute("SELECT count(*) FROM clientes")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Equipe
    equipe = [
        ("ana", "123", "Ana Silva", "Consultora Pleno", "user"),
        ("bruno", "123", "Bruno Souza", "Consultor Jr", "user"),
        ("roberto", "123", "Roberto TI", "Tech Lead", "user"),
        ("julia", "123", "Julia Financeiro", "Analista", "user")
    ]
    c.executemany("INSERT INTO usuarios (usuario, senha, nome, cargo, perfil) VALUES (?,?,?,?,?)", equipe)

    # 2. Clientes (20)
    nomes = ["Inova", "Agro", "Tech", "Log", "Construtora", "Hospital", "Escola", "Varejo", "Consultoria", "Indústria"]
    sufixos = ["Solutions", "Corp", "Brasil", "S.A.", "Global", "Systems", "Partners", "Ltda"]
    setores = ["Tecnologia", "Agronegócio", "Saúde", "Educação", "Varejo", "Indústria"]
    
    hoje = datetime.now()
    
    for i in range(20):
        nome = f"{random.choice(nomes)} {random.choice(sufixos)} {i+1}"
        cnpj = f"{random.randint(10,99)}.456.789/0001-{random.randint(10,99)}"
        setor = random.choice(setores)
        c.execute("INSERT INTO clientes (nome, cpf_cnpj, setor, porte, filiais, endereco, email, data_cadastro) VALUES (?,?,?,?,?,?,?,?)", 
                  (nome, cnpj, setor, random.choice(["Médio", "Grande"]), random.randint(1,5), "Av. Central, 1000", f"contato@cli{i}.com", (hoje-timedelta(days=random.randint(100,400))).date()))
        cli_id = i + 1
        
        # 3. Contratos e Projetos (70% de chance)
        if random.random() > 0.3:
            tipo = random.choice(["Estratégia", "Financeira", "TI", "RH"])
            valor = random.choice([30000, 60000, 120000])
            inicio = hoje - timedelta(days=random.randint(30, 180))
            meses = 6
            fim = inicio + relativedelta(months=meses)
            status_ct = "Ativo" if fim > hoje else "Encerrado"
            
            c.execute("INSERT INTO contratos (cliente_id, tipo, valor_total, qtd_parcelas, inicio, fim, status) VALUES (?,?,?,?,?,?,?)",
                      (cli_id, tipo, valor, meses, inicio.date(), fim.date(), status_ct))
            ct_id = c.lastrowid
            
            # Financeiro (Parcelas)
            val_parc = valor/meses
            for m in range(meses):
                venc = inicio + relativedelta(months=m)
                stt_fin = "Pago" if venc < hoje else "Aberto"
                c.execute("INSERT INTO financeiro (contrato_id, tipo, categoria, valor, data_vencimento, status) VALUES (?,?,?,?,?,?)",
                          (ct_id, "Receita", f"Parcela {m+1}/{meses}", val_parc, venc.date(), stt_fin))
            
            # Projeto
            resp = random.choice(["Ana Silva", "Bruno Souza", "Roberto TI"])
            status_pj = "Em Andamento" if status_ct == "Ativo" else "Concluído"
            c.execute("INSERT INTO projetos (contrato_id, nome, inicio, fim, status, responsavel) VALUES (?,?,?,?,?,?)",
                      (ct_id, f"Projeto {nome}", inicio.date(), fim.date(), status_pj, resp))
            pj_id = c.lastrowid
            
            # Tarefas
            tasks = ["Kickoff", "Diagnóstico", "Desenvolvimento", "Treinamento", "Entrega Final"]
            for t_desc in tasks:
                d_lim = inicio + timedelta(days=random.randint(10, 150))
                stt_task = "Concluída" if d_lim < hoje and random.random() > 0.2 else "Pendente"
                d_conc = d_lim if stt_task == "Concluída" else None
                c.execute("INSERT INTO tarefas (projeto_id, descricao, tipo, data_limite, responsavel, status, data_conclusao) VALUES (?,?,?,?,?,?,?)",
                          (pj_id, t_desc, "Etapa", d_lim.date(), resp, stt_task, d_conc))

    # 4. Despesas Recorrentes (Últimos 6 meses)
    cats = [("Salários", 40000), ("Aluguel", 5000), ("Impostos", 8000), ("Software", 2000)]
    for m in range(-5, 2):
        dt_ref = hoje + relativedelta(months=m)
        dt_venc = dt_ref.replace(day=10)
        stt = "Pago" if dt_venc < hoje else "Aberto"
        for cat, val in cats:
            val_var = val * random.uniform(0.95, 1.05)
            c.execute("INSERT INTO financeiro (tipo, categoria, valor, data_vencimento, status) VALUES (?,?,?,?,?)",
                      ("Despesa", cat, val_var, dt_venc.date(), stt))

    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect('peegflow.db')
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        data = c.fetchall()
        cols = [description[0] for description in c.description]
        df = pd.DataFrame(data, columns=cols)
        conn.close()
        return df
    conn.commit()
    conn.close()

# --- AUTOMAÇÃO E LÓGICA ---

def criar_financeiro_contrato(ct_id, valor, parcelas, inicio):
    """Gera Contas a Receber automaticamente"""
    conn = sqlite3.connect('peegflow.db')
    c = conn.cursor()
    val_p = valor / parcelas
    dt_ini = pd.to_datetime(inicio)
    
    for i in range(parcelas):
        venc = dt_ini + relativedelta(months=i)
        c.execute("INSERT INTO financeiro (contrato_id, tipo, categoria, valor, data_vencimento, status) VALUES (?,?,?,?,?,?)",
                  (ct_id, "Receita", f"Mensalidade {i+1}/{parcelas}", val_p, venc.date(), "Aberto"))
    conn.commit()
    conn.close()

# --- TELAS / MÓDULOS ---

def login_page():
    st.markdown(f"""
    <div style='text-align: center; padding: 20px;'>
        <h1 style='color: {CORES['Azul']}'>PeegFlow ERP</h1>
        <p>Sistema Integrado de Gestão & Projetos</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        with st.container(border=True):
            st.markdown("### Acesso ao Sistema")
            with st.form("login"):
                user = st.text_input("Usuário")
                pwd = st.text_input("Senha", type="password")
                
                st.markdown("---")
                # SELETOR DE DEMO
                usar_demo = st.checkbox("📌 Carregar Dados de Demonstração (Demo Mode)", value=False)
                
                if st.form_submit_button("Entrar", type="primary"):
                    # Inicializa DB básico
                    init_db()
                    
                    # Se pediu demo, roda o gerador
                    if usar_demo:
                        gerar_demo_robusta()
                    
                    # Verifica credenciais
                    df = run_query("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (user, pwd), fetch=True)
                    if not df.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = df.iloc[0]['nome']
                        st.session_state['role'] = df.iloc[0]['perfil']
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
            
            st.caption("Credenciais Padrão: `admin` / `123`")

def dashboard_view():
    st.title("📊 Dashboard Executivo")
    st.markdown("Visão consolidada de performance.")
    
    # 1. Filtros Globais
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
        dt_ini = c1.date_input("De", datetime.now() - timedelta(days=90))
        dt_fim = c2.date_input("Até", datetime.now() + timedelta(days=30))
        visao = c3.selectbox("Visualização de Gráficos", ["Financeiro", "Eficiência Equipe", "CRM Clientes"])
        
        if c4.button("🔄 Atualizar KPIs"):
            st.rerun()

    # 2. KPIs (Top)
    df_fin = run_query("SELECT * FROM financeiro", fetch=True)
    df_proj = run_query("SELECT * FROM projetos", fetch=True)
    
    # Filtragem básica para KPIs acumulados
    receita = df_fin[df_fin['tipo']=='Receita']['valor'].sum()
    despesa = df_fin[df_fin['tipo']=='Despesa']['valor'].sum()
    saldo = receita - despesa
    ativos = len(df_proj[df_proj['status']=='Em Andamento'])
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Saldo Geral", f"R$ {saldo:,.2f}", delta="Acumulado Caixa")
    k2.metric("Projetos Ativos", ativos, delta="Em execução")
    k3.metric("Faturamento", f"R$ {receita:,.2f}", delta="Total")
    k4.metric("Despesas", f"R$ {despesa:,.2f}", delta_color="inverse")

    st.markdown("---")

    # 3. Gráficos Dinâmicos
    df_fin['data_vencimento'] = pd.to_datetime(df_fin['data_vencimento'])
    mask = (df_fin['data_vencimento'].dt.date >= dt_ini) & (df_fin['data_vencimento'].dt.date <= dt_fim)
    df_filt = df_fin.loc[mask]

    if visao == "Financeiro":
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            # Fluxo de Caixa no Tempo
            df_time = df_filt.groupby([pd.Grouper(key='data_vencimento', freq='M'), 'tipo'])['valor'].sum().reset_index()
            fig = px.bar(df_time, x='data_vencimento', y='valor', color='tipo', barmode='group',
                         title="Fluxo de Caixa Mensal",
                         color_discrete_map={'Receita': CORES['Azul'], 'Despesa': CORES['Vermelho']})
            st.plotly_chart(fig, use_container_width=True)
        with col_g2:
            # Custos
            df_desp = df_filt[df_filt['tipo']=='Despesa']
            if not df_desp.empty:
                fig2 = px.pie(df_desp, values='valor', names='categoria', title="Share de Despesas", hole=0.4,
                              color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sem despesas no período.")

    elif visao == "Eficiência Equipe":
        df_tasks = run_query("SELECT * FROM tarefas", fetch=True)
        # Ranking
        df_rank = df_tasks[df_tasks['status']=='Concluída'].groupby('responsavel').count().reset_index()
        
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(df_rank, x='responsavel', y='id', title="Tarefas Concluídas por Consultor",
                         labels={'id': 'Entregas'}, color='id', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Top Performers 🏆")
            st.dataframe(df_rank.sort_values('id', ascending=False), use_container_width=True, hide_index=True)

    elif visao == "CRM Clientes":
        df_cli = run_query("SELECT * FROM clientes", fetch=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(df_cli, names='setor', title="Carteira por Setor")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.metric("Total de Clientes", len(df_cli))
            st.dataframe(df_cli[['nome', 'setor', 'porte']], use_container_width=True, hide_index=True)

def crm_view():
    st.title("🤝 CRM & Contratos")
    tab1, tab2, tab3 = st.tabs(["Base de Clientes", "Novo Cadastro", "Gerar Contrato"])
    
    with tab1:
        df = run_query("SELECT id, nome, cpf_cnpj, setor, email FROM clientes", fetch=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with tab2:
        with st.form("new_cli"):
            st.subheader("Cadastro de Cliente")
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome/Razão Social")
            doc = c2.text_input("CNPJ/CPF")
            c3, c4 = st.columns(2)
            setor = c3.selectbox("Setor", ["Tecnologia", "Varejo", "Indústria", "Serviços"])
            porte = c4.selectbox("Porte", ["Pequeno", "Médio", "Grande"])
            end = st.text_input("Endereço")
            email = st.text_input("Email")
            
            if st.form_submit_button("Salvar Cliente"):
                run_query("INSERT INTO clientes (nome, cpf_cnpj, setor, porte, filiais, endereco, email, data_cadastro) VALUES (?,?,?,?,?,?,?,?)",
                          (nm, doc, setor, porte, 1, end, email, datetime.now().date()))
                st.success("Cliente Cadastrado!")
                st.rerun()

    with tab3:
        st.info("ℹ️ Este formulário cria o contrato e gera o financeiro automaticamente.")
        clientes = run_query("SELECT id, nome FROM clientes", fetch=True)
        if not clientes.empty:
            opts = clientes.set_index('id')['nome'].to_dict()
            with st.form("new_ct"):
                cli_id = st.selectbox("Cliente", options=opts.keys(), format_func=lambda x: opts[x])
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("Tipo", ["Consultoria TI", "Financeira", "Estratégica"])
                val = c2.number_input("Valor Total (R$)", min_value=1000.0)
                c3, c4 = st.columns(2)
                parc = c3.number_input("Parcelas", min_value=1, value=6)
                ini = c4.date_input("Início")
                
                if st.form_submit_button("Firmar Contrato"):
                    fim = pd.to_datetime(ini) + relativedelta(months=parc)
                    run_query("INSERT INTO contratos (cliente_id, tipo, valor_total, qtd_parcelas, inicio, fim, status) VALUES (?,?,?,?,?,?,?)",
                              (cli_id, tipo, val, parc, ini, fim.date(), "Ativo"))
                    res = run_query("SELECT last_insert_rowid()", fetch=True)
                    ct_id = res.iloc[0][0]
                    
                    criar_financeiro_contrato(ct_id, val, parc, ini)
                    st.success("Contrato Gerado e Parcelas lançadas!")
        else:
            st.warning("Cadastre clientes primeiro.")

def projetos_view():
    st.title("📅 Projetos & Tarefas (Operacional)")
    
    # Seção 1: Criar Novo Projeto (Vinculado)
    with st.expander("➕ Iniciar Novo Projeto"):
        cts = run_query("SELECT ct.id, c.nome, ct.tipo FROM contratos ct JOIN clientes c ON ct.cliente_id = c.id WHERE ct.status='Ativo'", fetch=True)
        if not cts.empty:
            cts['label'] = cts['nome'] + " - " + cts['tipo']
            opts = cts.set_index('id')['label'].to_dict()
            
            with st.form("new_pj"):
                ct_sel = st.selectbox("Contrato Base", options=opts.keys(), format_func=lambda x: opts[x])
                nm_pj = st.text_input("Nome do Projeto", value="Implantação Consultoria")
                resp = st.selectbox("Líder", ["Ana Silva", "Bruno Souza", "Roberto TI", "Carlos Gestor"])
                c1, c2 = st.columns(2)
                ini = c1.date_input("Início")
                fim = c2.date_input("Entrega")
                
                st.markdown("**Tarefas Iniciais (Separar por vírgula):**")
                tasks = st.text_area("", "Reunião Kickoff, Diagnóstico, Planejamento")
                
                if st.form_submit_button("Criar Projeto"):
                    run_query("INSERT INTO projetos (contrato_id, nome, inicio, fim, status, responsavel) VALUES (?,?,?,?,?,?)",
                              (ct_sel, nm_pj, ini, fim, "Em Andamento", resp))
                    res = run_query("SELECT last_insert_rowid()", fetch=True)
                    pj_id = res.iloc[0][0]
                    
                    if tasks:
                        for t in tasks.split(','):
                            run_query("INSERT INTO tarefas (projeto_id, descricao, tipo, data_limite, responsavel, status) VALUES (?,?,?,?,?,?)",
                                      (pj_id, t.strip(), "Inicial", ini, resp, "Pendente"))
                    st.success("Projeto Criado!")
                    st.rerun()
        else:
            st.warning("Sem contratos ativos.")

    st.markdown("---")
    
# Seção 2: Gerenciamento (Editável)
    pjs = run_query("SELECT p.id, p.nome, c.nome as cli, p.inicio, p.fim, p.status, p.responsavel FROM projetos p JOIN contratos ct ON p.contrato_id = ct.id JOIN clientes c ON ct.cliente_id = c.id", fetch=True)
    
    if not pjs.empty:
        # --- 1. CRONOGRAMA VISUAL (GANTT) ---
        st.subheader("Visão Geral do Cronograma")
        
        # Converter datas para datetime para o Plotly não dar erro
        pjs['inicio'] = pd.to_datetime(pjs['inicio'])
        pjs['fim'] = pd.to_datetime(pjs['fim'])
        
        # Gráfico de Gantt
        fig = px.timeline(pjs, x_start="inicio", x_end="fim", y="nome", color="status",
                          hover_data=["cli", "responsavel"],
                          title="Linha do Tempo dos Projetos",
                          color_discrete_map={"Em Andamento": CORES['Azul'], "Concluído": CORES['Verde']})
        
        # Ordenar cronograma para o mais recente ficar no topo (opcional)
        fig.update_yaxes(autorange="reversed") 
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")

        # --- 2. SELEÇÃO DE PROJETO (MENU SUSPENSO) ---
        st.subheader("Gerenciar Tarefas do Projeto")
        
        # Cria um dicionário para formatar o nome no menu: "ID - Nome Projeto - Cliente"
        # Isso facilita a busca pelo usuário
        opcoes_proj = {row['id']: f"{row['nome']} - {row['cli']}" for i, row in pjs.iterrows()}
        
        sel_pj = st.selectbox(
            "Selecione o Projeto para editar:", 
            options=opcoes_proj.keys(), 
            format_func=lambda x: opcoes_proj[x]
        )
        
        # --- 3. EDITOR DE TAREFAS ---
        if sel_pj:
            st.markdown(f"**Editando:** {opcoes_proj[sel_pj]}")
            df_t = run_query("SELECT id, descricao, data_limite, responsavel, status FROM tarefas WHERE projeto_id=?", (sel_pj,), fetch=True)
            
            if not df_t.empty:
                # CORREÇÃO CRÍTICA: Converte data para datetime antes do editor
                df_t['data_limite'] = pd.to_datetime(df_t['data_limite'])

                # Editor de Dados (CRUD Tabela)
                edited = st.data_editor(
                    df_t,
                    column_config={
                        "id": None,
                        "status": st.column_config.SelectboxColumn("Status", options=["Pendente", "Em Andamento", "Concluída"]),
                        "data_limite": st.column_config.DateColumn("Prazo"),
                        "responsavel": st.column_config.SelectboxColumn("Responsável", options=["Ana Silva", "Bruno Souza", "Roberto TI", "Carlos Gestor"])
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="editor_task"
                )
                
                col_btn, col_info = st.columns([1, 4])
                with col_btn:
                    if st.button("💾 Salvar Alterações"):
                        for i, row in edited.iterrows():
                            d_conc = datetime.now().date() if row['status'] == 'Concluída' else None
                            # Verifica se a data é NaT (Not a Time) ou válida antes de salvar
                            nova_data = row['data_limite'].date() if pd.notnull(row['data_limite']) else None
                            
                            run_query("UPDATE tarefas SET status=?, data_limite=?, responsavel=?, data_conclusao=? WHERE id=?",
                                      (row['status'], nova_data, row['responsavel'], d_conc, row['id']))
                        st.success("Salvo!")
                        time.sleep(0.5)
                        st.rerun()
            else:
                st.info("Este projeto ainda não tem tarefas cadastradas.")
            
            # --- 4. ADICIONAR TAREFA RÁPIDA ---
            with st.expander("➕ Adicionar Nova Tarefa", expanded=False):
                with st.form("fast_task"):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    desc = c1.text_input("Descrição da Tarefa")
                    who = c2.selectbox("Responsável", ["Ana Silva", "Bruno Souza", "Roberto TI", "Carlos Gestor"])
                    prazo = c3.date_input("Prazo Limite")
                    
                    if st.form_submit_button("Adicionar Tarefa"):
                        run_query("INSERT INTO tarefas (projeto_id, descricao, tipo, data_limite, responsavel, status) VALUES (?,?,?,?,?,?)",
                                  (sel_pj, desc, "Extra", prazo, who, "Pendente"))
                        st.success("Tarefa Adicionada!")
                        st.rerun()

def financeiro_view():
    st.title("💰 Gestão Financeira")
    
    # Filtros
    c1, c2, c3 = st.columns(3)
    mes = c1.selectbox("Mês", range(1,13), index=datetime.now().month-1)
    ano = c2.number_input("Ano", value=datetime.now().year)
    view = c3.selectbox("Filtro", ["Todos", "Receita", "Despesa"])
    
    # Query Dinâmica
    sql = "SELECT id, tipo, categoria, valor, data_vencimento, status FROM financeiro WHERE strftime('%m', data_vencimento) = ? AND strftime('%Y', data_vencimento) = ?"
    args = [f"{mes:02d}", str(ano)]
    if view != "Todos":
        sql += " AND tipo = ?"
        args.append(view)
        
    df = run_query(sql, tuple(args), fetch=True)
    
    # KPIs Mensais
    r = df[df['tipo']=='Receita']['valor'].sum()
    d = df[df['tipo']=='Despesa']['valor'].sum()
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Entradas (Mês)", f"R$ {r:,.2f}")
    k2.metric("Saídas (Mês)", f"R$ {d:,.2f}")
    k3.metric("Resultado (Mês)", f"R$ {r-d:,.2f}", delta_color="normal")
    
    st.divider()
    
    if not df.empty:
        st.subheader("Lançamentos (Clique para editar)")
        
        # CORREÇÃO CRÍTICA: Converter data string para datetime
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])

        edited_fin = st.data_editor(
            df,
            column_config={
                "id": None,
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "status": st.column_config.SelectboxColumn("Status", options=["Aberto", "Pago", "Atrasado"], required=True),
                "data_vencimento": st.column_config.DateColumn("Vencimento")
            },
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("💾 Atualizar Financeiro"):
            for i, row in edited_fin.iterrows():
                run_query("UPDATE financeiro SET status=?, valor=?, data_vencimento=? WHERE id=?",
                          (row['status'], row['valor'], pd.to_datetime(row['data_vencimento']).date(), row['id']))
            st.success("Atualizado!")
            time.sleep(0.5)
            st.rerun()
            
    # Lançamento Avulso
    with st.expander("Novo Lançamento Avulso (Ex: Conta Luz)"):
        with st.form("avulso"):
            c1, c2, c3 = st.columns(3)
            tp = c1.selectbox("Tipo", ["Despesa", "Receita"])
            cat = c2.text_input("Categoria")
            val = c3.number_input("Valor")
            dt = st.date_input("Vencimento")
            if st.form_submit_button("Lançar"):
                run_query("INSERT INTO financeiro (tipo, categoria, valor, data_vencimento, status) VALUES (?,?,?,?,?)",
                          (tp, cat, val, dt, "Aberto"))
                st.rerun()

# --- ORQUESTRADOR ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_page()
else:
    # Sidebar de Navegação
    with st.sidebar:
        st.markdown(f"## PeegFlow")
        st.caption(f"Olá, {st.session_state['user_name']}")
        st.markdown("---")
        
        if st.session_state['role'] == 'admin':
            menu = st.radio("Navegação", ["Dashboard", "CRM & Contratos", "Projetos", "Financeiro"])
        else:
            menu = st.radio("Navegação", ["Projetos"])
            
        st.markdown("---")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    # Roteamento
    if menu == "Dashboard": dashboard_view()
    elif menu == "CRM & Contratos": crm_view()
    elif menu == "Projetos": projetos_view()
    elif menu == "Financeiro": financeiro_view()