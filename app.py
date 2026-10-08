import base64
from datetime import datetime
import io
import json
import os
from docx import Document
import requests
import streamlit as st
from streamlit_calendar import calendar

# --- CONFIGURAÇÃO DA PÁGINA (MOBILE-FIRST) ---
st.set_page_config(
    page_title="Gestão Salão de Festas - Koch Cervejaria",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS MINIMALISTA E PROFISSIONAL PARA CELULAR E DESKTOP ---
st.markdown(
    """
    <style>
    .fc {
        max-width: 100% !important;
        font-size: 0.85rem !important;
    }
    .fc-toolbar {
        flex-direction: column !important;
        gap: 8px !important;
        align-items: center !important;
    }
    .fc-toolbar-title {
        font-size: 1.1rem !important;
        font-weight: bold;
    }
    .fc-daygrid-day-frame {
        min-height: 75px !important;
    }
    .fc-event {
        font-size: 0.72rem !important;
        padding: 2px 4px !important;
        border-radius: 4px !important;
    }
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- ARQUITETURA E PERSISTÊNCIA VIA GITHUB ---
ARQUIVO_DADOS = "reservas.json"

try:
  GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
  GITHUB_REPO = st.secrets["GITHUB_REPO"]
  HEADERS = {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }
except Exception:
  st.error("⚠️ Erro crítico: As credenciais GITHUB_TOKEN e GITHUB_REPO não foram configuradas nos Secrets do Streamlit.")
  st.stop()


def carregar_dados_nuvem():
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_DADOS}"
  try:
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
      dados_resp = response.json()
      conteudo_bytes = base64.b64decode(dados_resp["content"])
      return json.loads(conteudo_bytes.decode("utf-8")), dados_resp["sha"]
  except Exception:
    pass
  return [], None


def salvar_dados_nuvem(reservas):
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_DADOS}"
  _, sha = carregar_dados_nuvem()
  
  novo_conteudo = json.dumps(reservas, ensure_ascii=False, indent=4)
  conteudo_base64 = base64.b64encode(novo_conteudo.encode("utf-8")).decode("utf-8")

  dados = {
      "message": "Atualização automatizada via Sistema de Gestão de Salão",
      "content": conteudo_base64,
  }
  if sha:
    dados["sha"] = sha

  response = requests.put(url, headers=HEADERS, json=dados)
  if response.status_code not in [200, 201]:
    st.error(f"Erro ao sincronizar com o GitHub: {response.status_code}")
    return False
  return True


# Função para formatar de AAAA-MM-DD para DD/MM/AAAA
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


# Função para gerar o arquivo Word preenchido dinamicamente
def gerar_documento_word(ev, data_formatada, barris, texto_som, texto_retroprojetor, texto_cuidador, texto_taxa_adicional, texto_barris_contrato):
  caminho_modelo = "modelo_contrato.docx"
  if not os.path.exists(caminho_modelo):
    return None

  doc = Document(caminho_modelo)

  contexto = {
      "{{cliente}}": str(ev.get("cliente", "")),
      "{{documento}}": str(ev.get("documento", "Não informado")),
      "{{telefone}}": str(ev.get("telefone", "")),
      "{{data}}": str(data_formatada),
      "{{turno}}": str(ev.get("turno", "")),
      "{{qtd_pessoas}}": str(ev.get("qtd_pessoas", 0)),
      "{{tipo_evento}}": str(ev.get("tipo_evento", "Festividade")),
      "{{valor_locacao}}": f"R$ {float(ev.get('valor_locacao', 0)):,.2f}",
      "{{valor_sinal}}": f"R$ {float(ev.get('valor_sinal', 0)):,.2f}",
      "{{status_sinal}}": "Pago" if ev.get("sinal_pago") else "Pendente",
      "{{valor_caucao}}": f"R$ {float(ev.get('valor_caucao', 0)):,.2f}",
      "{{opcionais}}": f"{texto_som}{texto_retroprojetor}{texto_cuidador}{texto_taxa_adicional}",
      "{{chopps}}": texto_barris_contrato,
      "{{observacoes}}": str(ev.get("observacoes", "Nenhuma observação específica registrada."))
  }

  for p in doc.paragraphs:
    for chave, valor in contexto.items():
      if chave in p.text:
        for run in p.runs:
          if chave in run.text:
            run.text = run.text.replace(chave, valor)
        if chave in p.text:
          p.text = p.text.replace(chave, valor)

  for tabela in doc.tables:
    for linha in tabela.rows:
      for celula in linha.cells:
        for chave, valor in contexto.items():
          if chave in celula.text:
            celula.text = celula.text.replace(chave, valor)

  arquivo_io = io.BytesIO()
  doc.save(arquivo_io)
  arquivo_io.seek(0)
  return arquivo_io


# Carregar dados em memória
reservas, _ = carregar_dados_nuvem()

ESTILOS_CHOPP = [
    "Pilsen", "IPA", "Stout", "Bohemian Pilsener", 
    "Premium Golden", "APA", "Vinho", "Red Ale"
]

# --- MENU LATERAL (NAVEGAÇÃO E FILTROS) ---
with st.sidebar:
  st.title("🍺 Koch Gestão")
  st.caption("Controle Profissional de Locações")
  st.divider()

  menu = st.radio(
      "Navegação",
      ["📊 Dashboard & Métricas", "📅 Calendário Geral", "➕ Nova Locação", "📋 Lista & Gestão", "✅ Checklist do Dia"]
  )

  st.divider()
  st.subheader("⚙️ Filtro Temporal")
  filtro_mes = st.selectbox(
      "Mês de Referência",
      ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
  )

# --- APLICAR FILTRO DE MÊS ---
eventos_filtrados = reservas
if filtro_mes != "Todos":
  eventos_filtrados = [e for e in eventos_filtrados if e.get("date", "").split("-")[1] == filtro_mes]


# ==========================================
# 1. DASHBOARD & MÉTRICAS FINANCEIRAS
# ==========================================
if menu == "📊 Dashboard & Métricas":
  st.title("📊 Painel de Controle Consolidado")
  st.markdown("Visão executiva em tempo real do faturamento e ocupação.")

  total_locacoes = len(eventos_filtrados)
  confirmados = sum(1 for e in eventos_filtrados if e.get("status") == "Confirmado")
  pendentes = sum(1 for e in eventos_filtrados if e.get("status") == "Pendente")
  
  faturamento_projetado = sum(float(e.get("valor_locacao", 0)) for e in eventos_filtrados if e.get("status") != "Cancelado")
  sinais_recebidos = sum(float(e.get("valor_sinal", 0) or 0) for e in eventos_filtrados if float(e.get("valor_sinal", 0) or 0) > 0 and e.get("status") != "Cancelado")
  total_chopp_litros = 0
  for e in eventos_filtrados:
    if e.get("status") != "Cancelado":
      barris = e.get("barris", [])
      if not barris and e.get("qtd_chopp"):
        total_chopp_litros += int(e.get("qtd_chopp", 0))
      else:
        for b in barris:
          total_chopp_litros += int(b.get("litros", 0))

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Total de Reservas", total_locacoes)
  c2.metric("Confirmados 🟢", confirmados)
  c3.metric("Em Negociação 🟡", pendentes)
  c4.metric("Volume Chopp (L)", f"{total_chopp_litros} L")

  st.divider()

  c5, c6 = st.columns(2)
  c5.metric("Faturamento Salão", f"R$ {faturamento_projetado:,.2f}")
  c6.metric("Sinais Recebidos (Soma)", f"R$ {sinais_recebidos:,.2f}")

  st.divider()
  st.subheader("📈 Histórico Recente de Locações")
  if eventos_filtrados:
    st.dataframe(
        [{
            "Data (DD/MM/AAAA)": formatar_data_br(e.get("date")),
            "Cliente": e.get("cliente"),
            "Turno": e.get("turno"),
            "Status": e.get("status"),
            "Locação (R$)": f"R$ {float(e.get('valor_locacao', 0)):,.2f}"
        } for e in sorted(eventos_filtrados, key=lambda x: x["date"])],
        use_container_width=True
    )
  else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


# ==========================================
# 2. CALENDÁRIO GERAL
# ==========================================
elif menu == "📅 Calendário Geral":
  st.title("📆 Calendário Interativo de Locações")
  st.markdown("🟢 **Verde**: Confirmado/Locado | 🟡 **Amarelo**: Em Negociação | 🔴 **Vermelho**: Cancelado")

  calendar_events = []
  for ev in eventos_filtrados:
    st_ev = ev.get("status", "Pendente")
    if st_ev == "Confirmado":
      cor, icone = "#28a745", "✅ [Locado]"
    elif st_ev == "Cancelado":
      cor, icone = "#dc3545", "❌ [Cancel.]"
    else:
      cor, icone = "#ffc107", "⏳ [Negoc.]"

    sinal_txt = "Sinal OK" if ev.get("sinal_pago") else "Sinal Pendente"
    
    barris = ev.get("barris", [])
    total_litros_ev = sum(int(b.get("litros", 0)) for b in barris)
    chopp_str = f" | 🍺 {total_litros_ev}L" if total_litros_ev > 0 else ""
    
    data_br_cal = formatar_data_br(ev.get("date"))
    titulo = f"{icone} {data_br_cal} - {ev.get('cliente')} ({sinal_txt}){chopp_str}"

    calendar_events.append({
        "title": titulo,
        "start": ev.get("date"),
        "allDay": True,
        "backgroundColor": cor,
        "borderColor": cor,
    })

  calendar_options = {
      "headerToolbar": {"left": "prev,next", "center": "title", "right": "today"},
      "initialView": "dayGridMonth",
      "locale": "pt-br",
  }

  calendar(events=calendar_events, options=calendar_options, key="calendario_principal")


# ==========================================
# 3. NOVA LOCAÇÃO
# ==========================================
elif menu == "➕ Nova Locação":
  st.title("📝 Registrar Nova Locação ou Negociação")
  st.markdown("Preencha os dados, opcionais de som, retroprojetor, monitor/cuidador, barris e valores.")

  with st.form("form_nova_locacao", clear_on_submit=True):
    col_u1, col_u2 = st.columns(2)
    with col_u1:
      cliente = st.text_input("Nome do Cliente / Interessado *")
      telefone = st.text_input("WhatsApp do Cliente (Ex: 42999999999)")
      documento = st.text_input("CPF ou CNPJ")
    with col_u2:
      tipo_evento = st.text_input("Tipo de Evento (Ex: Aniversário, Casamento)")
      
      st.markdown("**Data do Evento**")
      col_d1, col_d2, col_d3 = st.columns(3)
      hoje = datetime.now()
      with col_d1:
        dia_ev = st.selectbox("Dia", list(range(1, 32)), index=hoje.day - 1, key="d_dia")
      with col_d2:
        mes_ev = st.selectbox("Mês", list(range(1, 13)), index=hoje.month - 1, key="d_mes", format_func=lambda x: f"{x:02d}")
      with col_d3:
        ano_ev = st.selectbox("Ano", [hoje.year, hoje.year + 1, hoje.year + 2], index=0, key="d_ano")

      turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
      qtd_pessoas = st.number_input("Qtdade de Pessoas", min_value=1, value=50, step=1)

    st.divider()
    st.subheader("🔊 Opcionais e Serviços Adicionais")
    
    col_op1, col_op2, col_op3, col_op4 = st.columns(4)
    with col_op1:
      valor_som = st.number_input("Caixa de Som (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
    with col_op2:
      valor_retroprojetor = st.number_input("Retroprojetor (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
    with col_op3:
      taxa_cuidador_str = st.selectbox("Monitor / Cuidador?", ["Não", "Sim"])
      taxa_cuidador = True if taxa_cuidador_str == "Sim" else False
    with col_op4:
      valor_taxa_adicional = st.number_input("Taxa Adicional (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f")

    st.divider()
    st.subheader("🍺 Gestão de Múltiplos Barris de Chopp Koch")
    st.markdown("Defina o estilo, tamanho e o **valor específico** para cada barril:")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
      st.markdown("##### 🛢️ Barril 1")
      estilo_1 = st.selectbox("Estilo 1", ["Nenhum"] + ESTILOS_CHOPP, key="e1")
      litros_1 = st.selectbox("Tamanho 1", [0, 15, 30, 50], index=2, key="t1")
      valor_b1 = st.number_input("Valor do Barril 1 (R$)", min_value=0.0, value=300.0, step=10.0, format="%.2f", key="vb1")

      st.markdown("##### 🛢️ Barril 3")
      estilo_3 = st.selectbox("Estilo 3", ["Nenhum"] + ESTILOS_CHOPP, key="e3")
      litros_3 = st.selectbox("Tamanho 3", [0, 15, 30, 50], index=0, key="t3")
      valor_b3 = st.number_input("Valor do Barril 3 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb3")

    with col_b2:
      st.markdown("##### 🛢️ Barril 2")
      estilo_2 = st.selectbox("Estilo 2", ["Nenhum"] + ESTILOS_CHOPP, key="e2")
      litros_2 = st.selectbox("Tamanho 2", [0, 15, 30, 50], index=0, key="t2")
      valor_b2 = st.number_input("Valor do Barril 2 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb2")

      st.markdown("##### 🛢️ Barril 4")
      estilo_4 = st.selectbox("Estilo 4", ["Nenhum"] + ESTILOS_CHOPP, key="e4")
      litros_4 = st.selectbox("Tamanho 4", [0, 15, 30, 50], index=0, key="t4")
      valor_b4 = st.number_input("Valor do Barril 4 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb4")

    st.divider()
    st.subheader("💰 Comercial e Valores do Salão")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
      valor_locacao = st.number_input("Valor da Locação (R$)", min_value=0.0, value=1000.0, step=50.0, format="%.2f")
    with col_v2:
      valor_sinal = st.number_input("Valor do Sinal (R$)", min_value=0.0, value=500.0, step=50.0, format="%.2f")
    with col_v3:
      valor_caucao = st.number_input("Valor Caução (R$)", min_value=0.0, value=200.0, step=50.0, format="%.2f")

    col_v4, col_v5 = st.columns(2)
    with col_v4:
      status = st.selectbox("Status da Reserva", ["Pendente", "Confirmado", "Cancelado"])
    with col_v5:
      sinal_pago = st.checkbox("Sinal Já Foi Pago?")

    observacoes = st.text_area("Observações Específicas / Acordos")

    submitted = st.form_submit_button("💾 Salvar Nova Locação na Nuvem")
    if submitted:
      if not cliente.strip():
        st.warning("⚠️ O nome do cliente é obrigatório.")
      else:
        try:
          data_formatada_str = f"{ano_ev}-{int(mes_ev):02d}-{int(dia_ev):02d}"
          datetime.strptime(data_formatada_str, "%Y-%m-%d")
        except ValueError:
          st.error("⚠️ Data inválida. Verifique o dia e o mês selecionados.")
          st.stop()

        lista_barris = []
        for est, lit, val in [
            (estilo_1, litros_1, valor_b1),
            (estilo_2, litros_2, valor_b2),
            (estilo_3, litros_3, valor_b3),
            (estilo_4, litros_4, valor_b4),
        ]:
          if est != "Nenhum" and lit > 0:
            lista_barris.append({"estilo": est, "litros": int(lit), "valor_total": float(val)})

        novo_id = str(int(datetime.now().timestamp()))
        nova_reserva = {
            "id": novo_id,
            "cliente": cliente,
            "telefone": telefone,
            "documento": documento,
            "tipo_evento": tipo_evento,
            "date": data_formatada_str,
            "turno": turno,
            "qtd_pessoas": int(qtd_pessoas),
            "status": status,
            "sinal_pago": sinal_pago,
            "valor_locacao": float(valor_locacao),
            "valor_sinal": float(valor_sinal),
            "valor_caucao": float(valor_caucao),
            "valor_som": float(valor_som),
            "valor_retroprojetor": float(valor_retroprojetor),
            "taxa_cuidador": taxa_cuidador,
            "valor_taxa_adicional": float(valor_taxa_adicional),
            "barris": lista_barris,
            "observacoes": observacoes,
        }
        reservas.append(nova_reserva)
        if salvar_dados_nuvem(reservas):
          st.success("🎉 Locação registrada e salva com sucesso!")
          st.rerun()


# ==========================================
# 4. LISTA & GESTÃO
# ==========================================
elif menu == "📋 Lista & Gestão":
  st.title("📋 Gerenciamento de Locações")
  st.markdown("Consulte, edite status, abra o WhatsApp direto ou gere o contrato em Word.")

  if eventos_filtrados:
    col_b1, col_b2 = st.columns(2)
    with col_b1:
      filtro_status_lst = st.selectbox("Filtrar por Status", ["Todos", "Confirmado", "Pendente", "Cancelado"])
    with col_b2:
      busca_texto = st.text_input("🔍 Buscar por Cliente", "")

    lista_exibicao = eventos_filtrados
    if filtro_status_lst != "Todos":
      lista_exibicao = [e for e in lista_exibicao if e.get("status") == filtro_status_lst]
    if busca_texto.strip():
      lista_exibicao = [e for e in lista_exibicao if busca_texto.lower() in e.get("cliente", "").lower()]

    for ev in sorted(lista_exibicao, key=lambda x: x["date"]):
      ev_id = ev.get("id")
      st_ev = ev.get("status", "Pendente")
      emoji = "✅" if st_ev == "Confirmado" else ("❌" if st_ev == "Cancelado" else "⏳")
      data_formatada = formatar_data_br(ev.get("date"))

      with st.container(border=True):
        col_i1, col_i2 = st.columns([3, 1])
        with col_i1:
          st.markdown(f"**{emoji} Data: {data_formatada} - {ev.get('cliente')}**")
          st.caption(f"Turno: **{ev.get('turno')}** | Evento: {ev.get('tipo_evento', 'Geral')} | Qtdade de Pessoas: {ev.get('qtd_pessoas', 0)} | Status: **{st_ev}**")
          
          tel = ev.get("telefone", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
          if tel:
            st.markdown(f"[💬 Abrir Conversa no WhatsApp](https://wa.me/55{tel})")
          
          v_loc = float(ev.get("valor_locacao", 0))
          v_sinal_cadastrado = float(ev.get("valor_sinal", 0))
          sinal_pago_status = "Pago ✅" if ev.get("sinal_pago") else "Pendente ⏳"
          v_som = float(ev.get("valor_som", 0))
          v_retroprojetor = float(ev.get("valor_retroprojetor", 0))
          tem_cuidador = "Sim" if ev.get("taxa_cuidador", False) else "Não"
          v_taxa_adicional = float(ev.get("valor_taxa_adicional", 0))
          
          barris = ev.get("barris", [])
          if not barris and ev.get("qtd_chopp"):
            barris = [{"estilo": ev.get("estilo_chopp", "Pilsen"), "litros": ev.get("qtd_chopp"), "valor_total": int(ev.get("qtd_chopp", 0)) * float(ev.get("preco_litro_chopp", 15.0))}]
          
          desc_barris = ", ".join([f"{b['litros']}L {b['estilo']} (R$ {float(b.get('valor_total', 0)):,.2f})" for b in barris]) if barris else "Nenhum chopp"
          v_chopp_total = sum(float(b.get("valor_total", 0)) for b in barris)

          st.text(f"Locação: R$ {v_loc:,.2f} | Sinal: R$ {v_sinal_cadastrado:,.2f} ({sinal_pago_status})")
          st.text(f"Som: R$ {v_som:,.2f} | Retroprojetor: R$ {v_retroprojetor:,.2f} | Cuidador: {tem_cuidador} | Taxa Adicional: R$ {v_taxa_adicional:,.2f}")
          st.text(f"Chopp: {desc_barris} | Total Chopp: R$ {v_chopp_total:,.2f}")

        with col_i2:
          btn_edit = st.button("✏️ Editar", key=f"ed_{ev_id}", use_container_width=True)
          btn_contrato = st.button("📄 Contrato", key=f"ct_{ev_id}", use_container_width=True)
          btn_del = st.button("🗑️ Excluir", key=f"dl_{ev_id}", use_container_width=True)

        if btn_del:
          reservas = [r for r in reservas if r.get("id") != ev_id]
          if salvar_dados_nuvem(reservas):
            st.success("Reserva excluída com sucesso!")
            st.rerun()

        if btn_contrato:
          st.divider()
          st.markdown("### 📄 Geração de Contrato em Word (.docx)")
          
          texto_barris_contrato = "\n".join([f"- {b['litros']} litros de Chopp estilo {b['estilo']} - R$ {float(b.get('valor_total', 0)):,.2f}" for b in barris]) if barris else "Nenhum opcional de chopp."
          texto_som = f"- Aluguel de Caixa de Som: R$ {float(ev.get('valor_som', 0)):,.2f}\n" if float(ev.get('valor_som', 0)) > 0 else "- Caixa de Som: Não contratada\n"
          texto_retroprojetor = f"- Aluguel de Retroprojetor: R$ {float(ev.get('valor_retroprojetor', 0)):,.2f}\n" if float(ev.get('valor_retroprojetor', 0)) > 0 else "- Retroprojetor: Não contratado\n"
          
          cuid_txt_contrato = "INCLUSA" if ev.get('taxa_cuidador', False) else "Não contratada"
          texto_cuidador = f"- Taxa de Monitor/Cuidador durante a festa: {cuid_txt_contrato}\n"
          texto_taxa_adicional = f"- Taxa Adicional / Serviços Extras: R$ {float(ev.get('valor_taxa_adicional', 0)):,.2f}\n" if float(ev.get('valor_taxa_adicional', 0)) > 0 else ""

          arquivo_docx = gerar_documento_word(ev, data_formatada, barris, texto_som, texto_retroprojetor, texto_cuidador, texto_taxa_adicional, texto_barris_contrato)
          
          if arquivo_docx:
            nome_arquivo_download = f"Contrato_{ev.get('cliente').replace(' ', '_')}.docx"
            st.download_button(
                label="📥 Baixar Contrato em Word Preenchido",
                data=arquivo_docx,
                file_name=nome_arquivo_download,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"dl_docx_{ev_id}"
            )
          else:
            st.warning("⚠️ O arquivo `modelo_contrato.docx` não foi encontrado no GitHub. Certifique-se de enviá-lo para a raiz do repositório.")

        if btn_edit:
          st.session_state[f"edit_mode_{ev_id}"] = not st.session_state.get(f"edit_mode_{ev_id}", False)

        if st.session_state.get(f"edit_mode_{ev_id}", False):
          st.divider()
          st.markdown(f"**Editando Completo: {ev.get('cliente')}**")
          
          e_cli = st.text_input("Cliente", value=ev.get("cliente", ""), key=f"c_{ev_id}")
          e_tel = st.text_input("WhatsApp", value=ev.get("telefone", ""), key=f"t_{ev_id}")
          e_qtd_pes = st.number_input("Qtdade de Pessoas", min_value=1, value=int(ev.get("qtd_pessoas", 50)), step=1, key=f"qp_{ev_id}")
          
          try:
            partes_dt = ev.get("date", "2026-01-01").split("-")
            ano_atu, mes_atu, dia_atu = int(partes_dt[0]), int(partes_dt[1]), int(partes_dt[2])
          except:
            ano_atu, mes_atu, dia_atu = 2026, 1, 1

          st.markdown("**Editar Data (DD/MM/AAAA)**")
          c_ed1, c_ed2, c_ed3 = st.columns(3)
          with c_ed1:
            e_dia = st.selectbox("Dia", list(range(1, 32)), index=dia_atu - 1, key=f"ed_d_{ev_id}")
          with c_ed2:
            e_mes = st.selectbox("Mês", list(range(1, 13)), index=mes_atu - 1, key=f"ed_m_{ev_id}", format_func=lambda x: f"{x:02d}")
          with c_ed3:
            e_ano = st.selectbox("Ano", [2026, 2027, 2028], index=0, key=f"ed_a_{ev_id}")

          e_stat = st.selectbox("Status", ["Pendente", "Confirmado", "Cancelado"], index=["Pendente", "Confirmado", "Cancelado"].index(ev.get("status", "Pendente")), key=f"s_{ev_id}")
          
          col_ev1, col_ev2 = st.columns(2)
          with col_ev1:
            e_vloc = st.number_input("Valor Locação (R$)", value=float(ev.get("valor_locacao", 0)), step=50.0, key=f"vl_{ev_id}")
          with col_ev2:
            e_vsinal = st.number_input("Valor do Sinal (R$)", value=float(ev.get("valor_sinal", 0)), step=50.0, key=f"vs_{ev_id}")

          st.markdown("---")
          st.subheader("🔊 Opcionais (Som, Retroprojetor, Cuidador e Taxa Adicional)")
          col_op_ed1, col_op_ed2, col_op_ed3, col_op_ed4 = st.columns(4)
          with col_op_ed1:
            e_vsom = st.number_input("Caixa de Som (R$)", value=float(ev.get("valor_som", 0)), step=10.0, key=f"vsom_{ev_id}")
          with col_op_ed2:
            e_vretro = st.number_input("Retroprojetor (R$)", value=float(ev.get("valor_retroprojetor", 0)), step=10.0, key=f"vretro_{ev_id}")
          with col_op_ed3:
            idx_cuid = 0 if ev.get("taxa_cuidador", False) else 1
            e_tcuid_str = st.selectbox("Monitor / Cuidador?", ["Não", "Sim"], index=idx_cuid, key=f"tcuid_{ev_id}")
            e_tcuid = True if e_tcuid_str == "Sim" else False
          with col_op_ed4:
            e_vtaxa_adicional = st.number_input("Taxa Adicional (R$)", value=float(ev.get("valor_taxa_adicional", 0)), step=10.0, format="%.2f", key=f"vtaxa_{ev_id}")

          st.markdown("---")
          st.subheader("🍺 Barris de Chopp Cadastrados")
          
          barris_atuais = ev.get("barris", [])
          b1_data = barris_atuais[0] if len(barris_atuais) > 0 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}
          b2_data = barris_atuais[1] if len(barris_atuais) > 1 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}
          b3_data = barris_atuais[2] if len(barris_atuais) > 2 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}
          b4_data = barris_atuais[3] if len(barris_atuais) > 3 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}

          opt_estilos = ["Nenhum"] + ESTILOS_CHOPP
          opt_litros = [0, 15, 30, 50]

          def get_idx_safe(lst, val):
            try:
              return lst.index(val)
            except:
              return 0

          col_eb1, col_eb2 = st.columns(2)
          with col_eb1:
            st.markdown("##### 🛢️ Barril 1")
            e_est_1 = st.selectbox("Estilo 1", opt_estilos, index=get_idx_safe(opt_estilos, b1_data.get("estilo", "Nenhum")), key=f"ee1_{ev_id}")
            e_lit_1 = st.selectbox("Tamanho 1", opt_litros, index=get_idx_safe(opt_litros, b1_data.get("litros", 0)), key=f"et1_{ev_id}")
            e_val_1 = st.number_input("Valor Barril 1 (R$)", value=float(b1_data.get("valor_total", 0)), step=10.0, format="%.2f", key=f"evb1_{ev_id}")

            st.markdown("##### 🛢️ Barril 3")
            e_est_3 = st.selectbox("Estilo 3", opt_estilos, index=get_idx_safe(opt_estilos, b3_data.get("estilo", "Nenhum")), key=f"ee3_{ev_id}")
            e_lit_3 = st.selectbox("Tamanho 3", opt_litros, index=get_idx_safe(opt_litros, b3_data.get("litros", 0)), key=f"et3_{ev_id}")
            e_val_3 = st.number_input("Valor Barril 3 (R$)", value=float(b3_data.get("valor_total", 0)), step=10.0, format="%.2f", key=f"evb3_{ev_id}")

          with col_eb2:
            st.markdown("##### 🛢️ Barril 2")
            e_est_2 = st.selectbox("Estilo 2", opt_estilos, index=get_idx_safe(opt_estilos, b2_data.get("estilo", "Nenhum")), key=f"ee2_{ev_id}")
            e_lit_2 = st.selectbox("Tamanho 2", opt_litros, index=get_idx_safe(opt_litros, b2_data.get("litros", 0)), key=f"et2_{ev_id}")
            e_val_2 = st.number_input("Valor Barril 2 (R$)", value=float(b2_data.get("valor_total", 0)), step=10.0, format="%.2f", key=f"evb2_{ev_id}")

            st.markdown("##### 🛢️ Barril 4")
            e_est_4 = st.selectbox("Estilo 4", opt_estilos, index=get_idx_safe(opt_estilos, b4_data.get("estilo", "Nenhum")), key=f"ee4_{ev_id}")
            e_lit_4 = st.selectbox("Tamanho 4", opt_litros, index=get_idx_safe(opt_litros, b4_data.get("litros", 0)), key=f"et4_{ev_id}")
            e_val_4 = st.number_input("Valor Barril 4 (R$)", value=float(b4_data.get("valor_total", 0)), step=10.0, format="%.2f", key=f"evb4_{ev_id}")

          e_sinal_pago = st.checkbox("Sinal Pago?", value=bool(ev.get("sinal_pago", False)), key=f"sp_{ev_id}")

          if st.button("💾 Salvar Alterações na Nuvem", key=f"sv_{ev_id}"):
            nova_data_str = f"{e_ano}-{int(e_mes):02d}-{int(e_dia):02d}"
            
            novos_barris = []
            for est, lit, val in [
                (e_est_1, e_lit_1, e_val_1),
                (e_est_2, e_lit_2, e_val_2),
                (e_est_3, e_lit_3, e_val_3),
                (e_est_4, e_lit_4, e_val_4),
            ]:
              if est != "Nenhum" and lit > 0:
                novos_barris.append({"estilo": est, "litros": int(lit), "valor_total": float(val)})

            for item in reservas:
              if item.get("id") == ev_id:
                item["cliente"] = e_cli
                item["telefone"] = e_tel
                item["qtd_pessoas"] = int(e_qtd_pes)
                item["date"] = nova_data_str
                item["status"] = e_stat
                item["valor_locacao"] = float(e_vloc)
                item["valor_sinal"] = float(e_vsinal)
                item["valor_som"] = float(e_vsom)
                item["valor_retroprojetor"] = float(e_vretro)
                item["taxa_cuidador"] = e_tcuid
                item["valor_taxa_adicional"] = float(e_vtaxa_adicional)
                item["barris"] = novos_barris
                item["sinal_pago"] = e_sinal_pago
                break
            if salvar_dados_nuvem(reservas):
              st.session_state[f"edit_mode_{ev_id}"] = False
              st.success("Atualizado com sucesso!")
              st.rerun()
  else:
    st.info("Nenhuma locação cadastrada no momento.")


# ==========================================
# 5. CHECKLIST DO DIA
# ==========================================
elif menu == "✅ Checklist do Dia":
  st.title("✅ Checklist Operacional para Entrega do Salão")
  st.markdown("Selecione uma data para visualizar o resumo consolidado de tudo o que foi contratado.")

  hoje_dt = datetime.now()
  data_selecionada = st.date_input("Escolha a data do evento", value=hoje_dt)
  data_str_busca = data_selecionada.strftime("%Y-%m-%d")

  eventos_do_dia = [e for e in reservas if e.get("date") == data_str_busca and e.get("status") != "Cancelado"]

  st.divider()

  if eventos_do_dia:
    st.success(f"Encontrado(s) **{len(eventos_do_dia)}** evento(s) confirmado(s)/pendente(s) para o dia {formatar_data_br(data_str_busca)}:")

    for idx, ev in enumerate(eventos_do_dia, 1):
      with st.container(border=True):
        st.markdown(f"### 🎯 Evento {idx}: {ev.get('cliente')}")
        
        col_ck1, col_ck2 = st.columns(2)
        with col_ck1:
          st.markdown(f"**Turno:** {ev.get('turno')}")
          st.markdown(f"**Tipo de Evento:** {ev.get('tipo_evento', 'Festividade')}")
          st.markdown(f"**Qtdade de Pessoas:** {ev.get('qtd_pessoas', 0)}")
        with col_ck2:
          status_sinal_chk = "Pago ✅" if ev.get("sinal_pago") else "Pendente ⏳"
          st.markdown(f"**Status da Reserva:** {ev.get('status')}")
          st.markdown(f"**Sinal / Caução:** Sinal {status_sinal_chk} | Caução: R$ {float(ev.get('valor_caucao', 0)):,.2f}")

        st.markdown("---")
        st.markdown("#### 📦 Resumo dos Itens Contratados:")
        
        # Opcionais individuais
        tem_som = float(ev.get('valor_som', 0)) > 0
        tem_retro = float(ev.get('valor_retroprojetor', 0)) > 0
        tem_cuid = bool(ev.get('taxa_cuidador', False))
        tem_taxa_ext = float(ev.get('valor_taxa_adicional', 0)) > 0

        st.checkbox(f"🔊 Caixa de Som {'(Contratado)' if tem_som else '(Não contratado)'}", value=tem_som, key=f"chk_som_{ev.get('id')}_{idx}")
        st.checkbox(f"📽️ Retroprojetor {'(Contratado)' if tem_retro else '(Não contratado)'}", value=tem_retro, key=f"chk_retro_{ev.get('id')}_{idx}")
        st.checkbox(f"👤 Monitor / Cuidador {'(Incluso)' if tem_cuid else '(Não contratado)'}", value=tem_cuid, key=f"chk_cuid_{ev.get('id')}_{idx}")
        if tem_taxa_ext:
          st.checkbox(f"🏷️ Taxa Adicional / Extra (R$ {float(ev.get('valor_taxa_adicional', 0)):,.2f})", value=True, key=f"chk_taxa_{ev.get('id')}_{idx}")

        # Barris de Chopp
        st.markdown("##### 🍺 Barris de Chopp para Conferência:")
        barris_dia = ev.get("barris", [])
        if not barris_dia and ev.get("qtd_chopp"):
          barris_dia = [{"estilo": ev.get("estilo_chopp", "Pilsen"), "litros": ev.get("qtd_chopp"), "valor_total": int(ev.get("qtd_chopp", 0)) * float(ev.get("preco_litro_chopp", 15.0))}]

        if barris_dia:
          for b_idx, b in enumerate(barris_dia, 1):
            st.checkbox(f"🛢️ Barril {b_idx}: **{b.get('litros')} litros** de chopp estilo **{b.get('estilo')}**", value=True, key=f"chk_b_{ev.get('id')}_{idx}_{b_idx}")
        else:
          st.info("Nenhum barril de chopp contratado para este evento.")

        if ev.get("observacoes"):
          st.markdown(f"📝 **Observações Especiais:** {ev.get('observacoes')}")
  else:
    st.info(f"Nenhum evento agendado para o dia {formatar_data_br(data_str_busca)}.")
