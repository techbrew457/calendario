import base64
from datetime import datetime, time
import json
import os
import requests
import streamlit as st
from streamlit_calendar import calendar

# Configuração da página para ocupar a tela inteira (ótimo para celular)
st.set_page_config(
    page_title="Reservas Espaço - Koch Cervejaria", page_icon="🍺", layout="wide"
)

# --- CSS PERSONALIZADO PARA OTIMIZAR O CALENDÁRIO NO CELULAR ---
st.markdown(
    """
    <style>
    /* Força o calendário a ocupar 100% da largura e se adaptar a telas pequenas */
    .fc {
        max-width: 100% !important;
        font-size: 0.8rem !important;
    }
    
    /* Ajusta o cabeçalho do calendário para não quebrar em telas estreitas */
    .fc-toolbar {
        flex-direction: column !important;
        gap: 10px !important;
        align-items: center !important;
    }
    
    .fc-toolbar-title {
        font-size: 1.1rem !important;
    }

    /* Deixa os dias do mês com uma altura confortável para toque no celular */
    .fc-daygrid-day-frame {
        min-height: 70px !important;
    }

    /* Ajusta o texto dos eventos dentro dos quadradinhos */
    .fc-event {
        font-size: 0.7rem !important;
        padding: 1px 3px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Arquivo JSON para salvar as reservas permanentemente no GitHub
ARQUIVO_DADOS = "reservas.json"

# Configurações do GitHub obtidas dos Streamlit Secrets
try:
  GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
  GITHUB_REPO = st.secrets["GITHUB_REPO"]
  ARQUIVO_CAMINHO = ARQUIVO_DADOS
  HEADERS = {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }
except Exception as e:
  st.error(
      "Erro: As credenciais do GitHub (GITHUB_TOKEN e GITHUB_REPO) não foram"
      " encontradas nos Secrets do Streamlit."
  )
  st.stop()


def carregar_reservas():
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_CAMINHO}"
  response = requests.get(url, headers=HEADERS)
  if response.status_code == 200:
    dados_resp = response.json()
    conteudo_base64 = dados_resp["content"]
    conteudo_bytes = base64.b64decode(conteudo_base64)
    return json.loads(conteudo_bytes.decode("utf-8")), dados_resp["sha"]
  return [], None


def salvar_no_github(reservas):
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_CAMINHO}"
  _, sha = carregar_reservas()

  novo_conteudo = json.dumps(reservas, ensure_ascii=False, indent=4)
  conteudo_base64 = base64.b64encode(novo_conteudo.encode("utf-8")).decode(
      "utf-8"
  )

  dados = {
      "message": "Atualização de reservas via app do salão",
      "content": conteudo_base64,
  }
  if sha:
    dados["sha"] = sha

  response = requests.put(url, headers=HEADERS, json=dados)
  if response.status_code not in [200, 201]:
    st.error(
        f"Erro ao salvar no GitHub ({response.status_code}):"
        f" {response.json().get('message', 'Erro desconhecido')}"
    )
    return False
  return True


# Função auxiliar para formatar a data de AAAA-MM-DD para DD/MM/AAAA
def formatar_data_br(data_str):
  try:
    if not data_str:
      return ""
    partes = data_str.split("-")
    if len(partes) == 3:
      return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return data_str
  except Exception:
    return data_str


# Carrega as reservas da nuvem
reservas, _ = carregar_reservas()

# --- MENU LATERAL: LOGO, TÍTULO E NAVEGAÇÃO ---
with st.sidebar:
  if os.path.exists("logo.png"):
    st.image("logo.png", use_container_width=True)
  
  st.title("Reservas Espaço")
  st.divider()
  
  menu = st.radio(
      "Navegação", ["📅 Painel / Calendário", "➕ Nova Locação"]
  )

  st.divider()
  st.subheader("🔍 Filtros Globais")
  filtro_mes = st.selectbox(
      "Filtrar por Mês",
      [
          "Todos",
          "01",
          "02",
          "03",
          "04",
          "05",
          "06",
          "07",
          "08",
          "09",
          "10",
          "11",
          "12",
      ],
  )

st.title("🍻 Reservas Espaço - Koch Cervejaria")

# Lista oficial atualizada de estilos de chopp da cervejaria
ESTILOS_CHOPP = [
    "Pilsen",
    "IPA",
    "Stout",
    "Bohemian Pilsener",
    "Premium Golden",
    "APA",
    "Vinho",
    "Red Ale",
    "Nenhum",
]

# Filtragem de eventos por mês
eventos_filtrados = reservas
if filtro_mes != "Todos":
  eventos_filtrados = [
      e for e in reservas if e.get("date", "").split("-")[1] == filtro_mes
  ]

if menu == "➕ Nova Locação":
  st.subheader("📝 Registrar Nova Locação / Negociação")
  with st.form("form_cadastro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
      cliente = st.text_input("Nome do Cliente / Interessado")
      telefone = st.text_input("Telefone / WhatsApp (Ex: 42999999999)")
      tipo_evento = st.text_input("Tipo de Evento (Ex: Aniversário, Confraternização...)")
      data_evento = st.date_input("Data da Locação")
    with col2:
      turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
      qtd_pessoas = st.number_input(
          "Headcount (Qtd de Pessoas)", min_value=1, value=50, step=1
      )
      status = st.selectbox(
          "Status da Locação", ["Confirmado", "Pendente", "Cancelado"]
      )
      sinal_pago = st.checkbox("50% de Sinal Pago?")

    st.divider()
    st.subheader("💰 Valores e Custos")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
      valor_locacao = st.number_input(
          "Valor da Locação (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f"
      )
    with col_v2:
      sugerido_sinal = valor_locacao / 2.0
      valor_sinal = st.number_input(
          "Valor do Sinal - 50% (R$)", min_value=0.0, value=sugerido_sinal, step=50.0, format="%.2f"
      )
    with col_v3:
      valor_caucao = st.number_input(
          "Valor da Caução (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f"
      )

    col_v4, col_v5 = st.columns(2)
    with col_v4:
      taxa_extra = st.number_input(
          "Taxa Extra (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f"
      )
    with col_v5:
      aluguel_som = st.number_input(
          "Aluguel de Som (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f"
      )

    st.divider()
    st.subheader("🍺 Opcionais de Chopp & Observações")
    col3, col4, col5 = st.columns(3)
    with col3:
      qtd_chopp = st.number_input(
          "Volume de Chopp (Litros)", min_value=0, value=0, step=10
      )
    with col4:
      preco_litro_chopp = st.number_input(
          "Preço do Litro (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f"
      )
    with col5:
      estilo_chopp = st.selectbox("Estilo do Chopp", ESTILOS_CHOPP)

    observacoes = st.text_area("Observações Gerais (Ex: Segunda opção para o dia)")

    submitted = st.form_submit_button("Salvar Locação no Sistema")
    if submitted:
      if not cliente.strip():
        st.warning("Por favor, preencha o nome do cliente.")
      else:
        novo_id = str(int(datetime.now().timestamp()))

        nova_reserva = {
            "id": novo_id,
            "cliente": cliente,
            "telefone": telefone,
            "tipo_evento": tipo_evento,
            "date": str(data_evento),
            "turno": turno,
            "qtd_pessoas": int(qtd_pessoas),
            "status": status,
            "sinal_pago": sinal_pago,
            "valor_locacao": float(valor_locacao),
            "valor_sinal": float(valor_sinal),
            "valor_caucao": float(valor_caucao),
            "taxa_extra": float(taxa_extra),
            "aluguel_som": float(aluguel_som),
            "qtd_chopp": int(qtd_chopp),
            "preco_litro_chopp": float(preco_litro_chopp),
            "estilo_chopp": estilo_chopp,
            "observacoes": observacoes,
        }
        reservas.append(nova_reserva)
        if salvar_no_github(reservas):
          st.success("Nova negociação/locação salva com sucesso na nuvem!")
          st.rerun()

elif menu == "📅 Painel / Calendário":
  # --- MONTAGEM DO CALENDÁRIO COM SUPORTE A MÚLTIPLOS EVENTOS POR DIA ---
  calendar_events = []
  for ev in eventos_filtrados:
    status_ev = ev.get("status", "Pendente")
    
    if status_ev == "Confirmado":
      icone_status = "✅ [Locado]"
      cor_fundo = "#28a745"  # Verde
    elif status_ev == "Cancelado":
      icone_status = "❌ [Cancelado]"
      cor_fundo = "#dc3545"  # Vermelho
    else:
      icone_status = "⏳ [Em Negociação]"
      cor_fundo = "#ffc107"  # Amarelo/Laranja

    sinal_txt
