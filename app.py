Atue como um Arquiteto de Software Sênior, Especialista em UI/UX Mobile-First e Desenvolvedor Full-Stack Python/Streamlit. 

CONTEXTO DO PROJETO ATUAL:
Atualmente possuo um sistema de gestão de locação de salões de festas construído em Streamlit e hospedado gratuitamente na nuvem, integrado de forma persistente com um banco de dados JSON no GitHub. O link atual em produção é: https://calendariosalaokoch.streamlit.app. 

OBJETIVO DA TAREFA:
Preciso que você reestruture, modernize e evolua este código Python/Streamlit para transformar o sistema em uma ferramenta de nível profissional, extremamente rápida, limpa, altamente otimizada para uso em dispositivos móveis (smartphones) e totalmente gratuita para operação. O foco central é a experiência de preenchimento rápido em celulares, clareza visual de disponibilidade e automação comercial.

REQUISITOS FUNCIONAIS E DE ARQUITETURA OBRIGATÓRIOS:

1. ARQUITETURA E PERSISTÊNCIA (Gratuita e Nuvem):
- Manter a arquitetura baseada em Streamlit Cloud integrada ao GitHub (leitura/escrita via API em um arquivo JSON persistente), garantindo link público único, sem custos e sem necessidade de instalação local pelos usuários.

2. UI/UX MOBILE-FIRST & DESIGN MINIMALISTA:
- Layout responsivo adaptado perfeitamente para telas de celulares verticais, eliminando necessidade de zoom ou rolagem horizontal excessiva.
- Sistema de cores universal e imediato no calendário e listagens:
  * 🟢 Verde: Disponível / Confirmado / Pago.
  * 🟡 Amarelo/Laranja: Em Negociação / Sinal Pendente.
  * 🔴 Vermelho: Locado / Cancelado.
- Elementos táteis grandes, botões fáceis de clicar com o polegar e formulários divididos em etapas lógicas para não cansar o preenchimento mobile.

3. CAMPOS DE CADASTRO E DADOS DA LOCAÇÃO (Expandidos):
- Dados do Cliente: Nome, Telefone/WhatsApp, Documento/CPF.
- Automação de Contato: Geração automática de um link direto integrando a API nativa do WhatsApp (ex: `https://wa.me/55...`), permitindo que, ao clicar no número ou ícone do cliente, o WhatsApp abra imediatamente conversando com ele.
- Detalhes do Evento: Tipo de evento, Turno (Manhã, Tarde, Noite, Dia Inteiro) ou Horários específicos de início/fim.
- Gestão de Múltiplas Unidades: Campo seletor de "Salão / Unidade" (ex: Salão Principal, Salão Master, Espaço Externo) para permitir o controle centralizado de mais de um espaço de festas.
- Opcionais Comerciais: Seção dedicada a opcional de Chopp (Volume em litros, Preço por litro e Estilo: Pilsen, IPA, Stout, Bohemian Pilsener, Premium Golden, APA, Vinho, Red Ale, Nenhum), aluguel de som, taxas extras.
- Financeiro Robusto: Valor da locação, registro de Sinal de 50% (com checkbox de controle de pagamento), Valor da Caução, Taxas e Histórico/Status de Pagamento (Parcial ou Total).
- Observações detalhadas.

4. PAINEL DE CONTROLE (DASHBOARD) E GESTÃO:
- Dashboard consolidado com métricas-chave em tempo real: Taxa de ocupação mensal, Faturamento projetado, volume total de chopp negociado no mês.
- Filtros globais dinâmicos por Mês, Status e Unidade/Salão.
- Ferramenta de busca rápida por nome do cliente.
- Mecanismo prático e isolado para edição rápida e exclusão segura de reservas.

5. FUNCIONALIDADES DE AUTOMAÇÃO E UTILIDADES:
- Geração automatizada de um "Esboço de Contrato de Locação" em texto formatado com base nas variáveis preenchidas da reserva, pronto para cópia rápida e envio via WhatsApp para o cliente.
- Formatação impecável de datas no padrão brasileiro (DD/MM/AAAA) em todas as exibições de texto e listagens.

ENTREGÁVEL ESPERADO:
Forneça o código Python completo (`app.py`), estruturado, modular, limpo, comentado e pronto para ser copiado e colado diretamente no repositório GitHub do projeto Streamlit, corrigindo qualquer erro prévio de sintaxe, variáveis ou formatação de datas.
