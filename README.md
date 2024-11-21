# Projeto de Observabilidade com Chatbot Utilizando OpenTelemetry, Prometheus e Grafana

## Introdução

Este projeto consiste na criação de uma aplicação simples de observabilidade que integra um chatbot com funcionalidades para:

- Monitorar métricas e traces utilizando OpenTelemetry.
- Expor essas métricas no Prometheus.
- Visualizar os dados e criar dashboards no Grafana.
- Permitir interatividade com o chatbot para consultar informações de monitoramento.

Foram utilizados Docker e Docker Compose para orquestrar os serviços e facilitar o processo de execução.

---

## Estrutura do Projeto
O projeto foi organizado em uma estrutura básica de diretórios com os seguintes serviços:

1. Chatbot: Serviço Flask que expõe uma API e integra OpenTelemetry.
2. Prometheus: Ferramenta para coleta de métricas.
3. Grafana: Ferramenta para visualização e análise dos dados coletados.

---

## Passo a Passo

1. Configuração do Chatbot
O chatbot foi construído usando o framework Flask e instrumentado com OpenTelemetry para coletar traces e métricas de desempenho.

Código do Chatbot
O arquivo app.py contém a lógica do chatbot, incluindo integração com OpenTelemetry e Prometheus. Aqui está a versão final do código:

[app.py](chatbot/app.py)

Arquivo requirements.txt
Contém todas as dependências necessárias para o chatbot:

[requirements.txt](chatbot/requirements.txt)

Dockerfile do Chatbot
O Dockerfile foi configurado para criar uma imagem do chatbot:

[Dockerfile](chatbot/Dockerfile)

---

2. Configuração do Prometheus
O Prometheus foi configurado para coletar métricas do chatbot.

Arquivo prometheus.yml
Configura o Prometheus para coletar métricas na porta 8000 do chatbot:

[prometheus.yml](prometheus/prometheus.yml)

---

3. Configuração do Grafana
O Grafana foi adicionado para visualizar as métricas coletadas pelo Prometheus.

- Configuração Básica:
- URL de conexão com o Prometheus: http://prometheus:9090.
- Criação de dashboards com gráficos para CPU e memória.

---

4. Docker Compose
O docker-compose.yml orquestra os três serviços: chatbot, Prometheus e Grafana.

[docker-compose.yml](docker-compose.yml)

---

## Execução
Para iniciar os serviços, execute os seguintes comandos:

1. Iniciar os Containers:

```docker-compose up --build```

2. Verificar os Serviços:

- Chatbot: Acesse http://localhost:5000.
- Prometheus: Acesse http://localhost:9090.
- Grafana: Acesse http://localhost:3000.

3. Enviar Perguntas ao Chatbot: Use o comando curl para testar o chatbot:

```curl -X POST http://localhost:5000/ask -H "Content-Type: application/json" -d '{"question": "Qual é o uso de memória atual?"}'```

---

## Integração entre Componentes
- Chatbot:

- Exibe métricas (CPU, Memória) como respostas interativas.
- Expostas na porta 8000 para o Prometheus.

## Prometheus:

- Coleta métricas do chatbot.
- Disponibiliza essas métricas para o Grafana.

## Grafana:

- Permite criar dashboards baseados nos dados coletados pelo Prometheus.

---

## Diagrama UML

[Diagrama UML](diagrama.puml)

- OpenTelemetry Collector atua como o agregador central de dados de monitoramento, enviando informações para os serviços apropriados.
- Grafana interage com todos os componentes de backend para construir painéis informativos e detalhados.
- Usuário Final recebe uma resposta do chatbot, enquanto os dados de monitoramento são processados em paralelo.

---

## Próximos Passos
1. Melhorar o Chatbot:

- Adicionar mais perguntas relacionadas às métricas.
- Implementar fluxos de interação mais sofisticados.
2. Customizar Dashboards:

- Criar visualizações detalhadas no Grafana.
3. Escalar o Sistema:

- Expandir os serviços monitorados.

