import requests
from flask import Flask, request, render_template_string, jsonify
from prometheus_client import start_http_server
from groq import Groq

# Configuração do Flask
app = Flask(__name__)

GROQ_API_KEY = "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"

# Configuração do Groq API
client = Groq(api_key=GROQ_API_KEY)

MIXTRAL_MODEL = "mixtral-8x7b-32768"

# Endpoint da API do Prometheus
PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"  # Ajuste conforme o ambiente

# Mapeamento dinâmico de termos para queries Prometheus
METRIC_KEYWORDS = {
    "cpu": "process_cpu_seconds_total",
    "memória": "process_resident_memory_bytes",
    "gc coletados": "python_gc_objects_collected_total",
    "gc não coletáveis": "python_gc_objects_uncollectable_total",
    "gc coleções": "python_gc_collections_total",
    "info python": "python_info",
    "memória virtual": "process_virtual_memory_bytes",
    "memória residente": "process_resident_memory_bytes",
    "início do processo": "process_start_time_seconds",
    "fds abertos": "process_open_fds",
    "fds máximos": "process_max_fds",
    "uptime": "up",
    "duração scrape": "scrape_duration_seconds",
    "amostras scrape": "scrape_samples_scraped",
    "amostras pós relabel": "scrape_samples_post_metric_relabeling",
    "séries adicionadas": "scrape_series_added",
}

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
        # Captura da pergunta do usuário
        user_input = request.json.get("question", "").strip().lower()

        # Identificar query baseada em palavras-chave
        query = None
        for keyword, prometheus_query in METRIC_KEYWORDS.items():
            if keyword in user_input:
                query = prometheus_query
                break

        # Processar métricas do Prometheus se houver uma query
        if query:
            response = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=5)
            if response.status_code != 200:
                return jsonify({"answer": "Erro ao acessar métricas do Prometheus."})

            data = response.json()
            if "data" in data and "result" in data["data"] and len(data["data"]["result"]) > 0:
                value = data["data"]["result"][0]["value"][1]
                return jsonify({"answer": f"Resultado para '{query}': {value}"})
            else:
                return jsonify({"answer": f"Não foi possível encontrar dados para a métrica '{query}'."})

        # Processar perguntas genéricas usando Groq
        completion = client.chat.completions.create(
            model=MIXTRAL_MODEL,
            messages=[{"role": "user", "content": user_input}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )
        return jsonify({"answer": completion.choices[0].message.content.strip()})

    except requests.exceptions.ConnectionError:
        return jsonify({"answer": "Erro: Não foi possível se conectar ao Prometheus. Verifique o endereço ou se o serviço está ativo."})
    except Exception as e:
        return jsonify({"answer": f"Erro ao processar a consulta: {str(e)}"})


if __name__ == "__main__":
    # Iniciar servidor de métricas na porta 8000
    start_http_server(8000)

    # Iniciar a aplicação Flask
    app.run(host="0.0.0.0", port=5000)