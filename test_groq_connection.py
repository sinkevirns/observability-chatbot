from groq import Groq

# Insira sua chave da API aqui
API_KEY = "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"

if not API_KEY:
    raise ValueError("A chave da API não foi inserida. Por favor, insira sua chave.")

try:
    # Conectando ao Groq com a chave fornecida
    client = Groq(api_key=API_KEY)
    print("Conexão com o Groq estabelecida com sucesso!")
except Exception as e:
    print(f"Erro ao conectar ao Groq: {e}")
