from flask import Flask, request, render_template_string, jsonify, session
from flask_session import Session
import requests
from prometheus_client import start_http_server
from groq import Groq
import re
from dotenv import load_dotenv
import os

# Configuração do Flask
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = 'super_secret_key'
Session(app)

# Configuração do Groq API
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MIXTRAL_MODEL = "mixtral-8x7b-32768"

# Endpoint da API do Prometheus
PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"
LOKI_URL = "http://loki:3100/loki/api/v1/query"
TEMPO_URL = "http://tempo:3200/api/traces"

# Funções auxiliares para consultas
def query_loki(log_query):
    """Consulta logs no Loki."""
    response = requests.get(LOKI_URL, params={"query": log_query}, timeout=5)
    if response.status_code == 200:
        return response.json()
    return {"error": "Erro ao consultar Loki."}

def query_tempo(trace_id):
    """Consulta traces no Tempo."""
    response = requests.get(f"{TEMPO_URL}/{trace_id}", timeout=5)
    if response.status_code == 200:
        return response.json()
    return {"error": "Erro ao consultar Tempo."}

def query_prometheus(metric_name):
    """Consulta métricas no Prometheus."""
    response = requests.get(PROMETHEUS_URL, params={"query": metric_name}, timeout=5)
    if response.status_code == 200:
        return response.json()
    return {"error": "Erro ao consultar Prometheus."}

def list_metrics():
    """Lista todas as métricas disponíveis no Prometheus através do Grafana."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/label/__name__/values", timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                return data["data"]  # Lista de métricas
        return []
    except Exception as e:
        return {"error": f"Erro ao listar métricas: {str(e)}"}

# Rotas Flask
@app.route("/", methods=["GET"])
def welcome():
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chatbot Observability</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f9;
                color: #333;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .container {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                width: 100%;
                max-width: 400px;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            .chat-window {
                border: 1px solid #ddd;
                border-radius: 5px;
                background: #f9f9f9;
                padding: 1rem;
                height: 300px;
                overflow-y: auto;
                font-size: 0.95rem;
            }
            .message {
                margin-bottom: 1rem;
            }
            .user-message {
                text-align: right;
                color: #4CAF50;
                font-weight: bold;
            }
            .bot-message {
                text-align: left;
                color: #555;
            }
            form {
                display: flex;
                gap: 0.5rem;
            }
            input[type="text"] {
                flex: 1;
                padding: 0.8rem;
                font-size: 1rem;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            button {
                padding: 0.8rem;
                font-size: 1rem;
                font-weight: bold;
                color: white;
                background: #4CAF50;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: background 0.3s;
            }
            button:hover {
                background: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Chatbot Observability</h1>
            <div class="chat-window" id="chatWindow"></div>
            <form id="chatForm">
                <input type="text" id="question" name="question" placeholder="Digite aqui..." required>
                <button type="submit">Enviar</button>
            </form>
        </div>
        <script>
            const form = document.getElementById('chatForm');
            const chatWindow = document.getElementById('chatWindow');

            form.addEventListener('submit', function(event) {
                event.preventDefault(); // Impede o envio tradicional do formulário
                const question = document.getElementById('question').value;

                // Adiciona a pergunta do usuário no chat
                const userMessage = document.createElement('div');
                userMessage.className = 'message user-message';
                userMessage.textContent = question;
                chatWindow.appendChild(userMessage);

                // Faz a requisição ao servidor
                fetch('/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question }),
                })
                .then(response => response.json())
                .then(data => {
                    // Adiciona a resposta do chatbot no chat
                    const botMessage = document.createElement('div');
                    botMessage.className = 'message bot-message';
                    botMessage.textContent = data.answer;
                    chatWindow.appendChild(botMessage);

                    // Rola automaticamente para o final do chat
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                })
                .catch(error => {
                    const botMessage = document.createElement('div');
                    botMessage.className = 'message bot-message';
                    botMessage.textContent = "Erro ao processar a pergunta. Tente novamente.";
                    chatWindow.appendChild(botMessage);

                    console.error('Erro:', error);
                });

                // Limpa o campo de entrada
                document.getElementById('question').value = '';
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Retorna a lista de métricas disponíveis."""
    metrics = list_metrics()
    if isinstance(metrics, list):
        return jsonify({"metrics": metrics})
    return jsonify(metrics)

@app.route("/ask", methods=["POST"])
def ask_question():
    try:
        user_input = request.json.get("question", "").strip().lower()

        available_metrics = list_metrics()
        if isinstance(available_metrics, list) and any(user_input in metric for metric in available_metrics):
            query = next(metric for metric in available_metrics if user_input in metric)
            metric_description = f"Métrica correspondente encontrada: {query}"

        if 'conversation' not in session:
            session['conversation'] = []

        session['conversation'].append({"role": "user", "content": user_input})

        # Contexto para o modelo Groq
        context = """
        Você é uma IA especializada em responder perguntas sobre métricas do Prometheus e Loki.
        Sua função é interpretar o que o usuário pergunta, gerar as consultas necessárias para Prometheus ou Loki e fornecer respostas detalhadas com base nos resultados.
        Se a consulta exigir um período específico (como 5 minutos, 1 hora, etc.), tente identificar o intervalo necessário. Caso contrário, considere usar o valor total acumulado.
        """

        # Variáveis para consulta
        query = None
        metric_description = None
        is_loki_query = False  # Flag para identificar se a consulta é sobre o Loki

        time_pattern = r"(\d+)\s*(segundos|minutos|horas|dias)"
        match = re.search(time_pattern, user_input)
        time_interval = None
        if match:
            value, unit = match.groups()
            unit_abbreviation = {
                "segundos": "s",
                "minutos": "m",
                "horas": "h",
                "dias": "d",
            }
            time_interval = f"{value}{unit_abbreviation[unit]}"

        # Identificar a consulta baseada nas palavras-chave
        if "cpu" in user_input:
            if time_interval:
                query = f"rate(process_cpu_seconds_total[{time_interval}])"
                metric_description = f"uso médio de CPU nos últimos {match.group(0)}"
            elif "loki" in user_input:
                is_loki_query = True  # A consulta é para Loki
                query = 'process_cpu_seconds_total{job="loki"}' # Ajuste conforme seu nome de job
                metric_description = "uso de CPU do Loki"
            else:
                query = "sum(process_cpu_seconds_total)"
                metric_description = "tempo total de uso de CPU"

        elif "memória" in user_input:
            query = "process_resident_memory_bytes"
            metric_description = "uso atual de memória residente"
        
        elif "disco" in user_input:
            query = "node_filesystem_avail_bytes"
            metric_description = "espaço disponível em disco"
        
        elif "rede" in user_input:
            query = "rate(node_network_receive_bytes_total)"
            metric_description = "taxa de recebimento de dados na rede"

        # Caso haja uma consulta válida
        if query:
            if is_loki_query:
                # Consultar Loki, se a flag for verdadeira
                loki_response = requests.get(
                    LOKI_URL, params={"query": query}, timeout=5
                )

                if loki_response.status_code != 200:
                    return jsonify(
                        {"answer": f"Erro ao acessar métricas do Loki. Status code: {loki_response.status_code}. Detalhes: {loki_response.text}"}
                    )

                try:
                    loki_data = loki_response.json()
                    if "data" in loki_data and "result" in loki_data["data"]:
                        results = loki_data["data"]["result"]
                        if results:
                            # Formatar os dados para enviar ao Groq
                            metric_values = [
                                {
                                    "metric": item["metric"],
                                    "value": item["value"][1],
                                }
                                for item in results
                            ]
                            groq_input = f"""
                            {context}

                            O usuário perguntou: "{user_input}"

                            Dados Loki obtidos para a métrica "{metric_description}":
                            {metric_values}

                            Gere uma resposta detalhada com base nesses dados.
                            """

                            # Consultar o modelo Groq para gerar a resposta
                            groq_response = client.chat.completions.create(
                                model=MIXTRAL_MODEL,
                                messages=[{"role": "system", "content": groq_input}],
                                temperature=1,
                                max_tokens=1024,
                                top_p=1,
                            )

                            return jsonify({"answer": groq_response.choices[0].message.content.strip()})

                        else:
                            return jsonify(
                                {"answer": f"Não há dados disponíveis para a métrica '{metric_description}' no momento."}
                            )
                    else:
                        return jsonify({"answer": "Erro ao processar a resposta do Loki: dados ausentes."})
                except Exception as e:
                    return jsonify({"answer": f"Erro ao processar os dados do Loki: {str(e)}"})

            else:
                # Consultar Prometheus se não for uma consulta Loki
                prometheus_response = requests.get(
                    PROMETHEUS_URL, params={"query": query}, timeout=5
                )

                if prometheus_response.status_code != 200:
                    return jsonify(
                        {"answer": f"Erro ao acessar métricas do Prometheus. Status code: {prometheus_response.status_code}. Detalhes: {prometheus_response.text}"}
                    )   

                try:
                    prometheus_data = prometheus_response.json()
                    if "data" in prometheus_data and "result" in prometheus_data["data"]:
                        results = prometheus_data["data"]["result"]
                        if results:
                            # Formatar os dados para enviar ao Groq
                            metric_values = [
                                {
                                    "metric": item["metric"],
                                    "value": item["value"][1],
                                }
                                for item in results
                            ]
                            groq_input = f"""
                            {context}

                            O usuário perguntou: "{user_input}"

                            Dados Prometheus obtidos para a métrica "{metric_description}":
                            {metric_values}

                            Gere uma resposta detalhada com base nesses dados.
                            """

                            # Consultar o modelo Groq para gerar a resposta
                            groq_response = client.chat.completions.create(
                                model=MIXTRAL_MODEL,
                                messages=[{"role": "system", "content": groq_input}],
                                temperature=1,
                                max_tokens=1024,
                                top_p=1,
                            )

                            return jsonify({"answer": groq_response.choices[0].message.content.strip()})

                        else:
                            return jsonify(
                                {"answer": f"Não há dados disponíveis para a métrica '{metric_description}' no momento."}
                            )
                    else:
                        return jsonify({"answer": "Erro ao processar a resposta do Prometheus: dados ausentes."})
                except Exception as e:
                    return jsonify({"answer": f"Erro ao processar os dados do Prometheus: {str(e)}"})

        # Caso não seja uma pergunta relacionada a métricas
        groq_response = client.chat.completions.create(
            model=MIXTRAL_MODEL,
            messages=session['conversation'],
            temperature=1,
            max_tokens=1024,
            top_p=1,
        )

        answer = groq_response.choices[0].message.content.strip()
        session['conversation'].append({"role": "assistant", "content": answer})

        return jsonify({"answer": groq_response.choices[0].message.content.strip()})

    except requests.exceptions.ConnectionError:
        return jsonify({"answer": "Erro: Não foi possível se conectar aos serviços."})
    except Exception as e:
        return jsonify({"answer": f"Erro ao processar a consulta: {str(e)}"})

if __name__ == "__main__":
    # Iniciar servidor de métricas na porta 8000
    start_http_server(8000)

    # Iniciar a aplicação Flask
    app.run(host="0.0.0.0", port=5000)