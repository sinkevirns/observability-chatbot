import requests
from flask import Flask, request, render_template_string, jsonify
from prometheus_client import start_http_server
from groq import Groq

# Configuração do Flask
app = Flask(__name__)

# Configuração do Groq API
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

MIXTRAL_MODEL = "mixtral-8x7b-32768"

# Endpoint da API do Prometheus
PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"
LOKI_URL = "http://loki:3100/loki/api/v1/query"
TEMPO_URL = "http://tempo:3200/api/traces"

# Contexto para a LLM


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
                text-align: center;
            }
            h1 {
                font-size: 1.8rem;
                margin-bottom: 1rem;
                color: #333;
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            label {
                font-weight: bold;
                color: #555;
            }
            input[type="text"] {
                padding: 0.8rem;
                font-size: 1rem;
                border: 1px solid #ccc;
                border-radius: 5px;
                width: 100%;
                box-sizing: border-box;
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
            footer {
                margin-top: 1.5rem;
                font-size: 0.9rem;
                color: #777;
            }
            #response {
                margin-top: 1rem;
                padding: 1rem;
                background: #f9f9f9;
                border-radius: 5px;
                border: 1px solid #ddd;
                text-align: left;
                font-size: 0.95rem;
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Chatbot Observability</h1>
            <form id="chatForm">
                <label for="question">Faça sua pergunta:</label>
                <input type="text" id="question" name="question" placeholder="Digite aqui..." required>
                <button type="submit">Enviar</button>
            </form>
            <div id="response"></div>
            <footer>Powered by Flask, Prometheus & Groq</footer>
        </div>
        <script>
            const form = document.getElementById('chatForm');
            const responseDiv = document.getElementById('response');

            form.addEventListener('submit', function(event) {
                event.preventDefault(); // Impede o envio tradicional do formulário
                const question = document.getElementById('question').value;

                fetch('/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question }),
                })
                .then(response => response.json())
                .then(data => {
                    responseDiv.textContent = data.answer;
                })
                .catch(error => {
                    responseDiv.textContent = "Erro ao processar a pergunta. Tente novamente.";
                    console.error('Erro:', error);
                });
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route("/ask", methods=["POST"])
def ask_question():
    try:
        user_input = request.json.get("question", "").strip().lower()

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

        # Identificar a consulta baseada nas palavras-chave
        if "cpu" in user_input:
            if "loki" in user_input:
                is_loki_query = True  # A consulta é para Loki
                query = '{job="your_loki_job_name", metric="process_cpu_seconds_total"}'  # Ajuste conforme seu nome de job
                metric_description = "uso de CPU do Loki"
            elif "total" in user_input or "geral" in user_input:
                query = "sum(process_cpu_seconds_total)"
                metric_description = "tempo total de uso de CPU do Prometheus"
            elif "últimos 5 minutos" in user_input:
                query = "rate(process_cpu_seconds_total[5m])"
                metric_description = "uso médio de CPU do Prometheus nos últimos 5 minutos"
            else:
                query = "sum(process_cpu_seconds_total)"
                metric_description = "tempo total de uso de CPU do Prometheus"

        elif "memória" in user_input:
            query = "process_resident_memory_bytes"
            metric_description = "uso atual de memória residente"
        
        elif "disco" in user_input:
            query = "node_filesystem_avail_bytes"
            metric_description = "espaço disponível em disco"
        
        elif "rede" in user_input:
            query = "rate(node_network_receive_bytes_total[5m])"
            metric_description = "taxa de recebimento de dados na rede nos últimos 5 minutos"

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
            messages=[{"role": "system", "content": context}, {"role": "user", "content": user_input}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
        )
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