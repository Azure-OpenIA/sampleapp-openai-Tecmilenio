import json
import os
import logging
import requests
import openai
from flask import Flask, Response, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)

# ACS Integration Settings
AZURE_FORMRECOGNIZER_RESOURCE_GROUP=""
AZURE_FORMRECOGNIZER_SERVICE=""
AZURE_FORMRECOGNIZER_SKU_NAME=""
AZURE_LOCATION="eastus"
AZURE_OPENAI_KEY="ce5f6ba157a241169b5c85d5b5137b67"
AZURE_OPENAI_MAX_TOKENS=1000
AZURE_OPENAI_MODEL="StarMindAI"
AZURE_OPENAI_MODEL_NAME="gpt-35-turbo"
AZURE_OPENAI_PREVIEW_API_VERSION="2023-06-01-preview"
AZURE_OPENAI_RESOURCE="starmind"
AZURE_OPENAI_RESOURCE_GROUP="starmind"
AZURE_OPENAI_SKU_NAME="S0"
AZURE_OPENAI_STOP_SEQUENCE=""
AZURE_OPENAI_STREAM="true"
AZURE_OPENAI_SYSTEM_MESSAGE=""""Serás un asistente virtual que ayudará a estudiantes a responder sus dudas sobre elección de carrera, brindarás información clara y variada.
Darás el siguiente saludo inicial "Hola, comprendo que puedas necesitar ayuda o información, estoy aquí para asistirte, dime ¿Cómo puedo ayudarte hoy?".
Tus respuestas serán empáticas con el usuario de extensión corta y concisa.
Usarás emogi's basadas en tus respuestas o en las preguntas que el usuario realice. 
Darás contexto de la pregunta inicial del usuario.
Utilizarás un lenguaje profesional sin excederte en tecnicismos.
Con tus respuestas apoyarás y empatizarás con la decisión del usuario sin interferir en su proceso de selección.
Tratarás de que el usuario se sienta bien y continúe interactuando contigo.
Al finalizar tu respuesta será "Espero haberte ayudado, ¿Puedo ayudarte en algo más?"""
AZURE_OPENAI_TEMPERATURE=1
AZURE_OPENAI_TOP_P=0
AZURE_RESOURCE_GROUP=""
AZURE_SEARCH_CONTENT_COLUMNS=""
AZURE_SEARCH_ENABLE_IN_DOMAIN=""
AZURE_SEARCH_FILENAME_COLUMN=""
AZURE_SEARCH_INDEX="index1"
AZURE_SEARCH_KEY="bhyduy5TD27iA3r0wqrMCRXbN6wzdJ2B7VmiExaS1BAzSeA3MHjt"
AZURE_SEARCH_CONTENT_COLUMNS="content"
AZURE_SEARCH_ENABLE_IN_DOMAIN="true"
AZURE_SEARCH_FILENAME_COLUMN="filepath"
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG=""
AZURE_SEARCH_SERVICE="searchcareers"
AZURE_SEARCH_SERVICE_RESOURCE_GROUP="testingLab"
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG="default"
AZURE_SEARCH_SKU_NAME="standard"
AZURE_SEARCH_TITLE_COLUMN="title"
AZURE_SEARCH_TOP_K=5
AZURE_SEARCH_URL_COLUMN="url"
AZURE_SEARCH_USE_SEMANTIC_SEARCH="false"

SHOULD_STREAM = True if AZURE_OPENAI_STREAM.lower() == "true" else False

def is_chat_model():
    if 'gpt-4' in AZURE_OPENAI_MODEL_NAME.lower() or AZURE_OPENAI_MODEL_NAME.lower() in ['gpt-35-turbo-4k', 'gpt-35-turbo-16k']:
        return True
    return False

def should_use_data():
    if AZURE_SEARCH_SERVICE and AZURE_SEARCH_INDEX and AZURE_SEARCH_KEY:
        return True
    return False

def prepare_body_headers_with_data(request):
    request_messages = request.json["messages"]

    body = {
        "messages": request_messages,
        "temperature": float(AZURE_OPENAI_TEMPERATURE),
        "max_tokens": int(AZURE_OPENAI_MAX_TOKENS),
        "top_p": float(AZURE_OPENAI_TOP_P),
        "stop": AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else None,
        "stream": SHOULD_STREAM,
        "dataSources": [
            {
                "type": "AzureCognitiveSearch",
                "parameters": {
                    "endpoint": f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
                    "key": AZURE_SEARCH_KEY,
                    "indexName": AZURE_SEARCH_INDEX,
                    "fieldsMapping": {
                        "contentField": AZURE_SEARCH_CONTENT_COLUMNS.split("|") if AZURE_SEARCH_CONTENT_COLUMNS else [],
                        "titleField": AZURE_SEARCH_TITLE_COLUMN if AZURE_SEARCH_TITLE_COLUMN else None,
                        "urlField": AZURE_SEARCH_URL_COLUMN if AZURE_SEARCH_URL_COLUMN else None,
                        "filepathField": AZURE_SEARCH_FILENAME_COLUMN if AZURE_SEARCH_FILENAME_COLUMN else None
                    },
                    "inScope": True if AZURE_SEARCH_ENABLE_IN_DOMAIN.lower() == "true" else False,
                    "topNDocuments": AZURE_SEARCH_TOP_K,
                    "queryType": "semantic" if AZURE_SEARCH_USE_SEMANTIC_SEARCH.lower() == "true" else "simple",
                    "semanticConfiguration": AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG if AZURE_SEARCH_USE_SEMANTIC_SEARCH.lower() == "true" and AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG else "",
                    "roleInformation": AZURE_OPENAI_SYSTEM_MESSAGE
                }
            }
        ]
    }

    chatgpt_url = f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/openai/deployments/{AZURE_OPENAI_MODEL}"
    if is_chat_model():
        chatgpt_url += "/chat/completions?api-version=2023-03-15-preview"
    else:
        chatgpt_url += "/completions?api-version=2023-03-15-preview"

    headers = {
        'Content-Type': 'application/json',
        'api-key': AZURE_OPENAI_KEY,
        'chatgpt_url': chatgpt_url,
        'chatgpt_key': AZURE_OPENAI_KEY,
        "x-ms-useragent": "GitHubSampleWebApp/PublicAPI/1.0.0"
    }

    return body, headers


def stream_with_data(body, headers, endpoint):
    s = requests.Session()
    response = {
        "id": "",
        "model": "",
        "created": 0,
        "object": "",
        "choices": [{
            "messages": []
        }]
    }
    try:
        with s.post(endpoint, json=body, headers=headers, stream=True) as r:
            for line in r.iter_lines(chunk_size=10):
                if line:
                    lineJson = json.loads(line.lstrip(b'data:').decode('utf-8'))
                    if 'error' in lineJson:
                        yield json.dumps(lineJson).replace("\n", "\\n") + "\n"
                    response["id"] = lineJson["id"]
                    response["model"] = lineJson["model"]
                    response["created"] = lineJson["created"]
                    response["object"] = lineJson["object"]

                    role = lineJson["choices"][0]["messages"][0]["delta"].get("role")
                    if role == "tool":
                        response["choices"][0]["messages"].append(lineJson["choices"][0]["messages"][0]["delta"])
                    elif role == "assistant": 
                        response["choices"][0]["messages"].append({
                            "role": "assistant",
                            "content": ""
                        })
                    else:
                        deltaText = lineJson["choices"][0]["messages"][0]["delta"]["content"]
                        if deltaText != "[DONE]":
                            response["choices"][0]["messages"][1]["content"] += deltaText

                    yield json.dumps(response).replace("\n", "\\n") + "\n"
    except Exception as e:
        yield json.dumps({"error": str(e)}).replace("\n", "\\n") + "\n"


def conversation_with_data(request):
    body, headers = prepare_body_headers_with_data(request)
    endpoint = f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/openai/deployments/{AZURE_OPENAI_MODEL}/extensions/chat/completions?api-version={AZURE_OPENAI_PREVIEW_API_VERSION}"
    
    if not SHOULD_STREAM:
        r = requests.post(endpoint, headers=headers, json=body)
        status_code = r.status_code
        r = r.json()

        return Response(json.dumps(r).replace("\n", "\\n"), status=status_code)
    else:
        if request.method == "POST":
            return Response(stream_with_data(body, headers, endpoint), mimetype='text/event-stream')
        else:
            return Response(None, mimetype='text/event-stream')

def stream_without_data(response):
    responseText = ""
    for line in response:
        deltaText = line["choices"][0]["delta"].get('content')
        if deltaText and deltaText != "[DONE]":
            responseText += deltaText

        response_obj = {
            "id": line["id"],
            "model": line["model"],
            "created": line["created"],
            "object": line["object"],
            "choices": [{
                "messages": [{
                    "role": "assistant",
                    "content": responseText
                }]
            }]
        }
        yield json.dumps(response_obj).replace("\n", "\\n") + "\n"


def conversation_without_data(request):
    openai.api_type = "azure"
    openai.api_base = f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/"
    openai.api_version = "2023-03-15-preview"
    openai.api_key = AZURE_OPENAI_KEY

    request_messages = request.json["messages"]
    messages = [
        {
            "role": "system",
            "content": AZURE_OPENAI_SYSTEM_MESSAGE
        }
    ]

    for message in request_messages:
        messages.append({
            "role": message["role"] ,
            "content": message["content"]
        })

    response = openai.ChatCompletion.create(
        engine=AZURE_OPENAI_MODEL,
        messages = messages,
        temperature=float(AZURE_OPENAI_TEMPERATURE),
        max_tokens=int(AZURE_OPENAI_MAX_TOKENS),
        top_p=float(AZURE_OPENAI_TOP_P),
        stop=AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else None,
        stream=SHOULD_STREAM
    )

    if not SHOULD_STREAM:
        response_obj = {
            "id": response,
            "model": response.model,
            "created": response.created,
            "object": response.object,
            "choices": [{
                "messages": [{
                    "role": "assistant",
                    "content": response.choices[0].message.content
                }]
            }]
        }

        return jsonify(response_obj), 200
    else:
        if request.method == "POST":
            return Response(stream_without_data(response), mimetype='text/event-stream')
        else:
            return Response(None, mimetype='text/event-stream')

@app.route("/conversation", methods=["GET", "POST"])
def conversation():
    try:
        use_data = should_use_data()
        if use_data:
            return conversation_with_data(request)
        else:
            return conversation_without_data(request)
    except Exception as e:
        logging.exception("Exception in /conversation")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()