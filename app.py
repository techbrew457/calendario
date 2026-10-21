import json
import requests
import streamlit as st
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Salão de Festas Koch - Gestão",
    page_icon="🍻",
    layout="wide"
)

# ==========================================
# CONFIGURAÇÃO DO GITHUB
# ==========================================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = "techbrew457/calendario"
GITHUB_FILE_PATH = "reservas.json"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

# ==========================================
# FUNÇÕES DE INTEGRAÇÃO COM GITHUB
# ==========================================
def carregar_reservas_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers)
        if response.status_code == 200:
            content = response.json()
            import base64
            file_content = base64.b64decode(content["content"]).decode("utf-8")
            dados = json.loads(file_content)
            # Armazena o sha necessário para atualizações futuras
            st.session_state["github_sha"] = content["sha"]
            return dados
        else:
            st.error("⚠️ Não foi possível carregar as reservas do GitHub.")
            return []
    except Exception as e:
        st.error(f"Erro ao conectar com GitHub: {e}")
        return []

def salvar_reservas_github(reservas):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    } if GITHUB_TOKEN else {}
    
    import base64
    content_str = json.dumps(reservas, indent=4, ensure_ascii=False)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": "Atualização automática de reservas via App Koch",
        "content": content_b64
    }
    
    if "github_sha" in st.session_state:
        payload["sha"] = st.session_state["github_sha"]
        
    try:
        response = requests.put(GITHUB_API_URL, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            new_data = response.json()
            st.session_state["github_sha"] = new_data["content"]["sha"]
            return True
        else:
            st.error(f"Erro ao salvar no GitHub ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar alterações no GitHub: {e}")
        return False

# ==========================================
# INICIALIZAÇÃO DE ESTADO
# ==========================================
if "reservas" not in st.session_state:
    st.session_state["reservas"] = carregar_reservas_github()

# ==========================================
# BARRA LATERAL (FILTROS)
# ==========================================
st.sidebar.title("🍻 Salão Koch")
st.sidebar.subheader("Filtros de Exibição")

anos_disponiveis = [2025, 2026, 2027]
ano_sel = st.sidebar.selectbox("Ano", anos_disponiveis, index=1)

meses_dict = {
    "Todos": 0, "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
    "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, "Setembro": 9,
    "Outubro": 10, "Novembro": 11, "Dezembro": 12
}
mes_nome_sel = st.sidebar.selectbox("Mês", list(meses_dict.keys()))
mes_num_sel = meses_dict[mes_nome_sel]

# Filtragem das reservas com base no menu lateral
eventos_filtrados = []
for ev in st.session_state["reservas"]:
    try:
        dt = datetime.strptime(ev["data"], "%Y-%m-%d")
        if dt.year == ano_sel and (mes_num_sel == 0 or dt.month == mes_num_sel):
            eventos_filtrados.append(ev)
    except (ValueError, KeyError):
        continue

# ==========================================
# ABAS DA APLICAÇÃO
# ==========================================
aba_dash, aba_gestao, aba_novo = st.tabs([
    "📊 Dashboard & Métricas", 
    "📋 Lista & Gestão", 
    "➕ Nova Locação"
])

# ------------------------------------------
# ABA 1: DASHBOARD & MÉTRICAS
# ------------------------------------------
with aba_dash:
    st.header("📊 Resumo Financeiro e Eventos")
    
    # Cálculos dinâmicos
    total_eventos = len(eventos_filtrados)
    
    # Soma de Sinais Recebidos (Soma qualquer valor > 0 para eventos não cancelados)
    sinais_recebidos = sum(
        float(e.get("valor_sinal", 0) or 0) 
        for e in eventos_filtrados 
        if float(e.get("valor_sinal", 0) or 0) > 0 and e.get("status") != "Cancelado"
    )
    
    total_locacoes = sum(
        float(e.get("valor_locacao", 0) or 0) 
        for e in eventos_filtrados 
        if e.get("status") != "Cancelado"
    )
    
    saldo_a_receber = total_locacoes - sinais_recebidos

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Reservas", total_eventos)
    col2.metric("Sinais Recebidos", f"R$ {sinais_recebidos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Faturamento Previsto", f"R$ {total_locacoes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col4.metric("Saldo Restante", f"R$ {saldo_a_receber:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")
    st.subheader("Próximos Eventos no Período Selecionado")
    if eventos_filtrados:
        for ev in eventos_filtrados:
            st.info(f"📅 **{ev['data']}** | 👤 **Cliente:** {ev['cliente']} | 💵 Locação: R$ {float(ev.get('valor_locacao', 0)):.2f} | 💰 Sinal: R$ {float(ev.get('valor_sinal', 0)):.2f} | Status: {ev.get('status', 'Confirmado')}")
    else:
        st.write("Nenhum evento localizado para o filtro selecionado.")

# ------------------------------------------
# ABA 2: LISTA & GESTÃO (EDIÇÃO E ALTERAÇÕES)
# ------------------------------------------
with aba_gestao:
    st.header("📋 Gerenciar e Editar Reservas")
    
    if not st.session_state["reservas"]:
        st.write("Nenhuma reserva cadastrada.")
    else:
        # Opções para selecionar a reserva que deseja editar
        lista_opcoes = {f"{e['data']} - {e['cliente']} (ID: {e['id']})": e['id'] for e in st.session_state["reservas"]}
        reserva_selecionada_label = st.selectbox("Selecione uma reserva para editar:", list(lista_opcoes.keys()))
        id_reserva_selecionada = lista_opcoes[reserva_selecionada_label]
        
        # Localiza o objeto da reserva no estado
        reserva_atual = next((e for e in st.session_state["reservas"] if e["id"] == id_reserva_selecionada), None)
        
        if reserva_atual:
            # Extrai ano, mês e dia atuais da reserva
            try:
                dt_reserva = datetime.strptime(reserva_atual["data"], "%Y-%m-%d")
                ano_def, mes_def, dia_def = dt_reserva.year, dt_reserva.month, dt_reserva.day
            except ValueError:
                ano_def, mes_def, dia_def = 2026, 10, 1

            with st.form("form_edicao_reserva"):
                st.subheader(f"Editando: {reserva_atual['cliente']}")
                
                cliente = st.text_input("Nome do Cliente", value=reserva_atual.get("cliente", ""))
                
                col_dia, col_mes, col_ano = st.columns(3)
                dia_ev = col_dia.number_input("Dia", min_value=1, max_value=31, value=dia_def)
                mes_ev = col_mes.number_input("Mês", min_value=1, max_value=12, value=mes_def)
                ano_ev = col_ano.number_input("Ano", min_value=2025, max_value=2030, value=ano_def)
                
                col_val1, col_val2 = st.columns(2)
                valor_locacao = col_val1.number_input("Valor da Locação (R$)", value=float(reserva_atual.get("valor_locacao", 0.0)), step=50.0)
                valor_sinal = col_val2.number_input("Valor do Sinal Pago (R$)", value=float(reserva_atual.get("valor_sinal", 0.0)), step=50.0)
                
                status_opcoes = ["Confirmado", "Pendente", "Cancelado"]
                index_status = status_opcoes.index(reserva_atual.get("status", "Confirmado")) if reserva_atual.get("status") in status_opcoes else 0
                status = st.selectbox("Status do Evento", status_opcoes, index=index_status)
                
                submitted_edicao = st.form_submit_button("💾 Salvar Alterações na Nuvem")
                
                if submitted_edicao:
                    if not cliente.strip():
                        st.warning("⚠️ O nome do cliente é obrigatório.")
                    else:
                        try:
                            # Monta e valida a nova data formatada
                            data_formatada_str = f"{int(ano_ev)}-{int(mes_ev):02d}-{int(dia_ev):02d}"
                            datetime.strptime(data_formatada_str, "%Y-%m-%d")
                        except ValueError:
                            st.error("⚠️ Data inválida. Verifique o dia e o mês selecionados.")
                            st.stop()

                        # 1. Atualiza a reserva correspondente na lista
                        for evento in st.session_state["reservas"]:
                            if evento["id"] == id_reserva_selecionada:
                                evento["cliente"] = cliente.strip()
                                evento["data"] = data_formatada_str  # <--- Nova data salva corretamente!
                                evento["valor_locacao"] = float(valor_locacao)
                                evento["valor_sinal"] = float(valor_sinal)
                                evento["status"] = status
                                break

                        # 2. Grava a lista atualizada no GitHub
                        if salvar_reservas_github(st.session_state["reservas"]):
                            st.success("✅ Reserva e data atualizadas com sucesso na nuvem!")
                            st.rerun()  # Recarrega o app para exibir as alterações na hora

# ------------------------------------------
# ABA 3: NOVA LOCAÇÃO (CADASTRO)
# ------------------------------------------
with aba_novo:
    st.header("➕ Cadastrar Nova Locação")
    
    import uuid
    
    with st.form("form_nova_reserva"):
        cliente_novo = st.text_input("Nome do Cliente")
        
        col_d, col_m, col_a = st.columns(3)
        dia_n = col_d.number_input("Dia", min_value=1, max_value=31, value=1)
        mes_n = col_m.number_input("Mês", min_value=1, max_value=12, value=10)
        ano_n = col_a.number_input("Ano", min_value=2025, max_value=2030, value=2026)
        
        col_v1, col_v2 = st.columns(2)
        v_loc = col_v1.number_input("Valor da Locação (R$)", min_value=0.0, value=0.0, step=50.0)
        v_sin = col_v2.number_input("Valor do Sinal (R$)", min_value=0.0, value=0.0, step=50.0)
        
        status_novo = st.selectbox("Status Inicial", ["Confirmado", "Pendente"])
        
        submitted_novo = st.form_submit_button("💾 Salvar Nova Locação na Nuvem")
        
        if submitted_novo:
            if not cliente_novo.strip():
                st.warning("⚠️ O nome do cliente é obrigatório.")
            else:
                try:
                    data_nova_str = f"{int(ano_n)}-{int(mes_n):02d}-{int(dia_n):02d}"
                    datetime.strptime(data_nova_str, "%Y-%m-%d")
                except ValueError:
                    st.error("⚠️ Data inválida. Verifique o dia e o mês selecionados.")
                    st.stop()

                nova_reserva = {
                    "id": str(uuid.uuid4())[:8],
                    "cliente": cliente_novo.strip(),
                    "data": data_nova_str,
                    "valor_locacao": float(v_loc),
                    "valor_sinal": float(v_sin),
                    "status": status_novo
                }
                
                st.session_state["reservas"].append(nova_reserva)
                
                if salvar_reservas_github(st.session_state["reservas"]):
                    st.success("✅ Nova locação cadastrada e salva na nuvem!")
                    st.rerun()
