import requests
from flask import Flask, request, render_template_string, jsonify
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configuração do Flask
app = Flask(__name__)

# Configuração do OpenTelemetry
resource = Resource.create({"service.name": "chatbot-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configuração do exportador OTLP
otlp_exporter = OTLPSpanExporter(endpoint="http://<seu-collector-endpoint>:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrumentação do Flask
FlaskInstrumentor().instrument_app(app)

# Endpoint da API do Prometheus
PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"

@app.route("/", methods=["GET"])
def welcome():
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chatbot de Observabilidade</title>
    </head>
    <body>
        <h1>Bem-vindo ao Chatbot de Observabilidade!</h1>
        <form action="/ask" method="POST">
            <label for="question">Digite sua pergunta:</label>
            <input type="text" id="question" name="question" required>
            <button type="submit">Enviar</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route("/ask", methods=["POST"])
def ask_question_web():
    try:
        # Captura da pergunta do usuário
        user_input = request.form.get("question", "").lower()

        # Identifica a métrica solicitada
        if "uso de memória" in user_input:
            query = 'process_resident_memory_bytes'
            metric_name = "Uso de Memória"
        elif "cpu usado" in user_input:
            query = 'process_cpu_seconds_total'
            metric_name = "Tempo Total de CPU"
        elif "objetos coletados" in user_input:
            query = 'python_gc_objects_collected_total'
            metric_name = "Objetos Coletados pelo GC"
        else:
            return "Desculpe, não entendi a pergunta. Tente algo como 'Qual é o uso de memória atual?'."

        # Consulta ao Prometheus
        response = requests.get(PROMETHEUS_URL, params={"query": query})
        if response.status_code != 200:
            return "Erro ao acessar métricas do Prometheus."

        data = response.json()
        if "data" in data and "result" in data["data"] and len(data["data"]["result"]) > 0:
            value = data["data"]["result"][0]["value"][1]
            return f"{metric_name}: {value}"
        else:
            return f"Não foi possível encontrar dados para {metric_name}."

    except Exception as e:
        return f"Ocorreu um erro: {str(e)}"

if __name__ == "__main__":
    from prometheus_client import start_http_server

# Iniciar servidor de métricas na porta 8000
    start_http_server(8000)

    app.run(host="0.0.0.0", port=5000)