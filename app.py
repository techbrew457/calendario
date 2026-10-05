import base64
import json
import requests
import streamlit as st
from streamlit_calendar import calendar

# Configuração da página otimizada para celular
st.set_page_config(
    page_title="Agenda - Salão de Festas", page_icon="📅", layout="centered"
)

# Configurações do GitHub
try:
  GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
  GITHUB_REPO = st.secrets["GITHUB_REPO"]
except:
  st.error("Configure os Secrets do GitHub no painel do Streamlit Cloud!")
  st.stop()

ARQUIVO_CAMINHO = "reservas.json"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

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

  # Se der erro, vamos imprimir o motivo exato na tela para sabermos o que aconteceu
  if response.status_code not in [200, 201]:
    st.error(
        f"Erro do GitHub ({response.status_code}):"
        f" {response.json().get('message', 'Erro desconhecido')}"
    )
    return False

  return True


def salvar_no_github(reservas):
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_CAMINHO}"
  _, sha = carregar_reservas()

  novo_conteudo = json.dumps(reservas, ensure_ascii=False, indent=4)
  conteudo_base64 = base64.b64encode(novo_conteudo.encode("utf-8")).decode(
      "utf-8"
  )

  dados = {
      "message": "Atualização rápida via celular",
      "content": conteudo_base64,
  }
  if sha:
    dados["sha"] = sha

  response = requests.put(url, headers=HEADERS, json=dados)
  return response.status_code in [200, 201]


eventos, _ = carregar_reservas()

st.title("🎉 Salão de Festas")
st.markdown("📱 **Painel de Agendamento Rápido**")

# --- BARRA LATERAL: LOGIN ---
st.sidebar.header("Painel de Controle")
senha_digitada = st.sidebar.text_input("Senha Admin", type="password")
SENHA_MESTRA = "admin123"
autorizado = senha_digitada == SENHA_MESTRA

if autorizado:
  st.sidebar.success("Modo Edição Ativado ✅")
else:
  st.sidebar.info("Modo Visualização 👁️ (Digite a senha para gerenciar)")

# --- LEGENDA DE CORES ---
st.markdown("""
**Status:** <span style="color:red">■</span> **Locado** | <span style="color:orange">■</span> **Negociação** | <span style="color:gray">■</span> **Indisponível**
""", unsafe_allow_html=True)

st.divider()

# --- FILTROS RÁPIDOS ---
filtro_status = st.selectbox(
    "Filtrar visualização:", ["Todos", "Locado", "Em Negociação", "Indisponível"]
)
eventos_filtrados = (
    eventos
    if filtro_status == "Todos"
    else [e for e in eventos if e.get("status") == filtro_status]
)

# --- ÁREA ADMINISTRATIVA OTIMIZADA PARA CELULAR ---
if autorizado:
  st.divider()
  st.subheader("⚙ Gerenciamento")

  acao = st.radio("Escolha:", ["➕ Novo Evento", "✏️ Editar / Excluir"], horizontal=True)

  # 1. ADICIONAR NOVO (Layout Vertical ideal para toque no celular)
  if acao == "➕ Novo Evento":
    with st.form("form_celular", clear_on_submit=True):
      st.markdown("### Preenchimento Rápido")

      nome_cliente = st.text_input("Nome do Cliente *")
      telefone = st.text_input("WhatsApp / Telefone")
      data_evento = st.date_input("Data do Evento *")

      tipo_evento = st.selectbox(
          "Tipo de Evento",
          [
              "Aniversário",
              "Casamento",
              "Confraternização",
              "Formatura",
              "Outros",
          ],
      )

      status = st.selectbox(
          "Status", ["Locado", "Em Negociação", "Indisponível"]
      )
      turno = st.selectbox(
          "Turno", ["Dia Inteiro (08h às 22h)", "Tarde/Noite", "Noite"]
      )

      qtd_pessoas = st.slider(
          "Quantidade Estimada de Pessoas", 10, 300, 100, step=10
      )

      st.markdown("---")
      sinal_pago = st.checkbox("💵 Sinal de 50% já foi pago?")

      col_chop1, col_chop2 = st.columns(2)
      with col_chop1:
        qtd_chopp = st.number_input(
            "Litros de Chopp", min_value=0, value=0, step=30
        )
      with col_chop2:
        estilo_chopp = st.selectbox(
            "Estilo", ["Nenhum", "Pilsen", "IPA", "Weiss", "Mixed"]
        )

      observacoes = st.text_area("Observações (Opcional)")

      salvar = st.form_submit_button(
          "💾 Salvar na Agenda", use_container_width=True
      )

      if salvar:
        if nome_cliente:
          cor = (
              "#FF4B4B"
              if status == "Locado"
              else ("#FFA500" if status == "Em Negociação" else "#808080")
          )
          sinal_txt = "Sinal OK" if sinal_pago else "Sinal Pendente"
          chopp_txt = (
              f" | 🍺 {qtd_chopp}L ({estilo_chopp})"
              if qtd_chopp > 0 and estilo_chopp != "Nenhum"
              else ""
          )

          novo_evento = {
              "id": str(len(eventos) + 1),
              "title": f"[{status}] {nome_cliente} - {tipo_evento} ({sinal_txt}){chopp_txt}",
              "date": str(data_evento),
              "backgroundColor": cor,
              "borderColor": cor,
              "textColor": "#ffffff",
              "cliente": nome_cliente,
              "telefone": telefone,
              "tipo_evento": tipo_evento,
              "status": status,
              "turno": turno,
              "qtd_pessoas": qtd_pessoas,
              "sinal_pago": sinal_pago,
              "qtd_chopp": qtd_chopp,
              "estilo_chopp": estilo_chopp if estilo_chopp != "Nenhum" else "",
              "observacoes": observacoes,
          }
          eventos.append(novo_evento)

          if salvar_no_github(eventos):
            st.success("Salvo com sucesso!")
            st.rerun()
          else:
            st.error("Erro ao salvar no GitHub.")
        else:
          st.error("Informe o nome do cliente.")

  # 2. EDITAR OU EXCLUIR
  else:
    if not eventos:
      st.info("Nenhum evento para alterar.")
    else:
      opcoes = {
          f"{e['date']} - {e.get('cliente')} ({e.get('status')})": e
          for e in eventos
      }
      selecionado = st.selectbox("Selecione o evento:", list(opcoes.keys()))

      if selecionado:
        ev = opcoes[selecionado]
        with st.form("form_edicao"):
          novo_nome = st.text_input("Nome", value=ev.get("cliente", ""))
          novo_tel = st.text_input("Telefone", value=ev.get("telefone", ""))
          novo_status = st.selectbox(
              "Status",
              ["Locado", "Em Negociação", "Indisponível"],
              index=["Locado", "Em Negociação", "Indisponível"].index(
                  ev.get("status", "Locado")
              )
              if ev.get("status") in ["Locado", "Em Negociação", "Indisponível"]
              else 0,
          )
          novo_sinal = st.checkbox(
              "Sinal Pago?", value=bool(ev.get("sinal_pago", False))
          )
          novas_obs = st.text_area(
              "Observações", value=ev.get("observacoes", "")
          )

          col1, col2 = st.columns(2)
          btn_salvar = col1.form_submit_button(
              "Atualizar", use_container_width=True
          )
          btn_del = col2.form_submit_button(
              "Excluir", use_container_width=True
          )

          if btn_salvar:
            cor = (
                "#FF4B4B"
                if novo_status == "Locado"
                else (
                    "#FFA500" if novo_status == "Em Negociação" else "#808080"
                )
            )
            sinal_txt = "Sinal OK" if novo_sinal else "Sinal Pendente"

            for e in eventos:
              if e.get("id") == ev.get("id") or e.get("title") == ev.get("title"):
                e["cliente"] = novo_nome
                e["telefone"] = novo_tel
                e["status"] = novo_status
                e["sinal_pago"] = novo_sinal
                e["observacoes"] = novas_obs
                e["title"] = (
                    f"[{novo_status}] {novo_nome} -"
                    f" {e.get('tipo_evento','')} ({sinal_txt})"
                )
                e["backgroundColor"] = cor
                e["borderColor"] = cor
                break

            if salvar_no_github(eventos):
              st.success("Atualizado!")
              st.rerun()

          if btn_del:
            eventos = [
                e
                for e in eventos
                if not (
                    e.get("id") == ev.get("id")
                    or e.get("title") == ev.get("title")
                )
            ]
            if salvar_no_github(eventos):
              st.warning("Excluído!")
              st.rerun()

st.divider()

# --- CALENDÁRIO VISUAL ---
st.subheader("📅 Calendário")
calendar(
    events=eventos_filtrados,
    options={
        "editable": False,
        "selectable": True,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth",
        },
        "locale": "pt-br",
    },
    key="cal_mobile",
)
# --- LISTA RÁPIDA ABAIXO (PERFEITA PARA CONSULTA NO CELULAR) ---
st.divider()
st.subheader("📋 Detalhes dos Eventos")
if eventos_filtrados:
  for ev in sorted(eventos_filtrados, key=lambda x: x["date"]):
    sinal_status = (
        "✅ Sinal Pago" if ev.get("sinal_pago") else "⏳ Sinal Pendente"
    )
    with st.expander(f"📌 {ev.get('date')} — {ev.get('cliente')}"):
      st.write(f"**Tipo:** {ev.get('tipo_evento')}")
      st.write(f"**Status:** {ev.get('status')} | **Financeiro:** {sinal_status}")
      st.write(f"**Turno:** {ev.get('turno')} ({ev.get('qtd_pessoas')} pessoas)")
      if ev.get("telefone"):
        st.write(f"**Contato:** {ev.get('telefone')}")
        tel_limpo = (
            ev.get("telefone")
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        st.markdown(f"[💬 Chamar no WhatsApp](https://wa.me/55{tel_limpo})")
      if ev.get("qtd_chopp", 0) > 0:
        st.write(
            f"**Chopp:** {ev.get('qtd_chopp')}L ({ev.get('estilo_chopp')})"
        )
      if ev.get("observacoes"):
        st.write(f"**Obs:** {ev.get('observacoes')}")
else:
  st.info("Nenhum evento encontrado.")
