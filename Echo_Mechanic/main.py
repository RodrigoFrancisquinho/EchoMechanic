import os
import sqlite3
import hashlib
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from fpdf import FPDF
from fastapi.responses import Response
import json
import shutil
import uuid

# Ensure uploads directory exists
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app = FastAPI()

from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse 

# Mount static files to serve JS/CSS from root
app.mount("/static", StaticFiles(directory="."), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Serve specific files for root paths if needed (optional, but good for direct access)
@app.get("/user_profile.js")
async def get_js():
    return FileResponse("user_profile.js")

# --- CONFIGURAÇÃO DA IA ---
# Certifique-se de que a chave está correta. Se o erro persistir, gere uma nova no Google AI Studio.
GOOGLE_API_KEY = "AIzaSyD3LRw96_E1MerbkxAy1k5HrhWEQ6k5SnA" 
genai.configure(api_key=GOOGLE_API_KEY)

# --- SELEÇÃO ROBUSTA DE MODELO ---
def get_best_model():
    print("\n--- A SELECIONAR MELHOR MODELO (QUOTA & ESTABILIDADE) ---")
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                print(f"Disponível: {m.name}")
    except Exception as e:
        print(f"Erro crítico ao listar modelos: {e}")
        # Em caso de erro total, tentamos o mais provável às cegas
        print("--> Fallback de emergência para gemini-1.5-flash")
        return genai.GenerativeModel('gemini-1.5-flash')

    # Lista de Prioridade (Quota Alta -> Quota Baixa/Preview)
    # A API retorna nomes como 'models/gemini-1.5-flash'
    priority_order = [
        'models/gemini-2.0-flash-lite', # High efficiency, lower cost/quota usage
        'models/gemini-flash-lite-latest',
        'models/gemini-1.5-flash',      # Stable, High Quota Tier
        'models/gemini-1.5-flash-001',  
        'models/gemini-1.5-flash-002',
        'models/gemini-1.5-flash-8b',
        'models/gemini-2.0-flash-exp',  # Preview, Lower Quota
        'models/gemini-2.0-flash',      # Sometimes alias for experimental
    ]

    selected_name = 'gemini-1.5-flash' # Fallback default

    found = False
    for candidate in priority_order:
        if candidate in available_models:
            selected_name = candidate
            found = True
            break
    
    # Se nenhum da lista prioritária existir, tenta encontrar qualquer "flash"
    if not found:
        for m in available_models:
            if 'flash' in m:
                selected_name = m
                break

    print(f"--> MODELO SELECIONADO: {selected_name}")
    print("----------------------------------------------------------\n")
    return genai.GenerativeModel(selected_name)

# Inicializa o modelo usando a função inteligente
model = get_best_model()

# --- BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, nome TEXT, role TEXT, empresa TEXT, notificacoes_alertas INTEGER DEFAULT 1, notificacoes_relatorios INTEGER DEFAULT 0, preferencia_ia TEXT DEFAULT 'simples')''')
    c.execute('''CREATE TABLE IF NOT EXISTS maquinas (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, nome TEXT, marca TEXT, modelo TEXT, categoria TEXT, data_instalacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, maquina_nome TEXT, data_analise TEXT, diagnostico TEXT, confianca TEXT, detalhes_json TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, role TEXT, content TEXT, timestamp TEXT, session_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, title TEXT, created_at TEXT)''')
    # Add columns if they don't exist (for existing databases)
    try:
        c.execute("ALTER TABLE users ADD COLUMN notificacoes_alertas INTEGER DEFAULT 1")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN notificacoes_relatorios INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN preferencia_ia TEXT DEFAULT 'simples'")
    except: pass
    try:
        c.execute("ALTER TABLE chat_messages ADD COLUMN session_id INTEGER")
    except: pass
    try:
        c.execute("ALTER TABLE historico ADD COLUMN audio_path TEXT")
    except: pass
    conn.commit()
    conn.close()

init_db()

# --- MODELOS ---
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: str
    role: str
    empresa: str = "Default"

class MachineRequest(BaseModel):
    user_email: str
    nome: str
    marca: str
    modelo: str
    categoria: str
    data_instalacao: str

class UserUpdateRequest(BaseModel):
    email_atual: str
    novo_nome: str
    novas_preferencias: str
    novas_notificacoes: dict

class PasswordChangeRequest(BaseModel):
    email: str
    nova_password: str

class UserDeleteRequest(BaseModel):
    email: str

class ChatRequest(BaseModel):
    message: str
    email: str
    session_id: int = None

class SessionRequest(BaseModel):
    email: str
    title: str = None

class SessionRenameRequest(BaseModel):
    email: str
    title: str

class PasswordChangeRequest(BaseModel):
    email: str
    old_password: str
    nova_password: str

class PasswordResetRequest(BaseModel):
    email: str
    new_password: str
    token: str

# --- ENDPOINTS ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("landing.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: landing.html nao encontrado"
        
@app.get("/forgot-password", response_class=HTMLResponse)
async def read_forgot_password():
    try:
        with open("forgot_password.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: forgot_password.html nao encontrado"

@app.get("/reset-password", response_class=HTMLResponse)
async def read_reset_password():
    try:
        with open("reset_password.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: reset_password.html nao encontrado"

@app.get("/auth", response_class=HTMLResponse)
async def read_auth():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: index.html nao encontrado"

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard():
    try:
        with open("dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: dashboard.html nao encontrado"

@app.get("/nova-analise", response_class=HTMLResponse)
async def read_nova_analise():
    try:
        with open("nova_analise.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: nova_analise.html nao encontrado"

@app.get("/historico", response_class=HTMLResponse)
async def read_historico():
    try:
        with open("historico.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: historico.html nao encontrado"

@app.get("/definicoes", response_class=HTMLResponse)
async def read_definicoes():
    try:
        with open("definicoes.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: definicoes.html nao encontrado"

@app.get("/chat", response_class=HTMLResponse)
async def read_chat():
    try:
        with open("chat.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: chat.html nao encontrado"

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing():
    try:
        with open("pricing.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: pricing.html nao encontrado"

@app.get("/pricing.html", response_class=HTMLResponse)
async def read_pricing_html():
    try:
        with open("pricing.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: pricing.html nao encontrado"

@app.get("/checkout.html", response_class=HTMLResponse)
async def read_checkout_html():
    try:
        with open("checkout.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: checkout.html nao encontrado"

@app.get("/success.html", response_class=HTMLResponse)
async def read_success_html():
    try:
        with open("success.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: success.html nao encontrado"

@app.post("/api/register")
@app.post("/api/register")
async def register(user: RegisterRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Lógica de Perfil Inteligente
        output_preference = 'simples'
        if user.role.lower() == 'tecnico':
            output_preference = 'technical' # ou 'tecnico' mas o prompt usa 'technical'
        else:
            output_preference = 'simple'
            
        # Hash simples para demo
        hashed_pw = hashlib.sha256(user.password.encode()).hexdigest()
        # Atualizado INSERT para incluir preferencia_ia
        c.execute("INSERT INTO users (email, password, nome, role, empresa, preferencia_ia) VALUES (?, ?, ?, ?, ?, ?)", 
                  (user.email, hashed_pw, user.nome, user.role, user.empresa, output_preference))
        conn.commit()
        return {"status": "success", "message": "Conta criada"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email ja existe")
    finally:
        conn.close()

@app.post("/api/login")
async def login(user: LoginRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(user.password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (user.email, hashed_pw))
    result = c.fetchone()
    conn.close()

    if result:
        return {"status": "success", "user": result[3]} # Retorna o nome
    else:
        raise HTTPException(status_code=401, detail="Credenciais invalidas")

@app.post("/api/user/change-password")
async def change_password(req: PasswordChangeRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # 1. Verificar password antiga
    hashed_old = hashlib.sha256(req.old_password.encode()).hexdigest()
    c.execute("SELECT id FROM users WHERE email=? AND password=?", (req.email, hashed_old))
    user = c.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Password atual incorreta")
    
    # 2. Atualizar para nova password
    hashed_new = hashlib.sha256(req.nova_password.encode()).hexdigest()
    c.execute("UPDATE users SET password=? WHERE email=?", (hashed_new, req.email))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Password atualizada"}

@app.post("/api/auth/request-reset")
async def request_reset(req: SessionRequest): # Reusing SessionRequest {email}
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (req.email,))
    user = c.fetchone()
    conn.close()
    
    if user:
        # SIMULATION
        import uuid
        token = str(uuid.uuid4())
        print(f"\n--- LINK DE RECUPERAÇÃO: http://127.0.0.1:8001/reset-password?token={token}&email={req.email} ---\n")
    
    return {"status": "success", "message": "Se o email existir, enviámos um link."}

@app.post("/api/auth/reset-password")
async def reset_password_endpoint(req: PasswordResetRequest):
    # In MVP we ignore token validation
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    hashed_new = hashlib.sha256(req.new_password.encode()).hexdigest()
    c.execute("UPDATE users SET password=? WHERE email=?", (hashed_new, req.email))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Password definida com sucesso"}


@app.post("/api/analyze")
async def analyze_audio(file: UploadFile = File(...), mode: str = Form("simple"), email: str = Form(...)):
    print(f"DEBUG: Recebido áudio de {email}. Tamanho: {file.size}")
    import datetime
    
    try:
        # --- 0. GRAVAR FICHEIRO NO DISCO ---
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else "mp3"
        filename = f"analise_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file_ext}"
        
        # Ensure assets/audio_history exists
        audio_history_dir = os.path.join("assets", "audio_history")
        if not os.path.exists(audio_history_dir):
            os.makedirs(audio_history_dir)
            
        filepath = os.path.join(audio_history_dir, filename)
        
        # Guardar conteúdo
        audio_content = await file.read()
        with open(filepath, "wb") as f:
            f.write(audio_content)
        
        # Caminho relativo para a DB (acessível via /assets/...)
        db_audio_path = f"/assets/audio_history/{filename}"

        # --- 1. BUSCAR PREFERÊNCIA DO UTILIZADOR ---
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT preferencia_ia FROM users WHERE email=?", (email,))
        row = c.fetchone()
        conn.close()
        
        user_pref = row[0] if row else 'simples'
        print(f"DEBUG: Preferência do utilizador {email}: {user_pref}")
        
        style_instruction = ""
        if user_pref == 'technical':
            style_instruction = "Sê extremamente técnico. Usa termos de engenharia, cita a norma ISO 18436. Fala de frequências e componentes específicos."
        else:
            style_instruction = "Explica de forma executiva, focada em custos, tempo de paragem e gravidade. Evita jargão excessivo. Sê claro para um gestor."

        # Prompt Cético (Mantemos a lógica inteligente) + Estilo
        prompt = f"""
        Atua como um Engenheiro de Vibrações ISO 18436.
        Analise o áudio com ceticismo.
        
        ESTILO DE RESPOSTA: {style_instruction}
        
        PASSO 1: VALIDAR
        - Se for voz, silêncio ou batidas na mesa -> DIAGNÓSTICO: "Fonte Inválida"
        
        PASSO 2: DIAGNOSTICAR
        - Se for ruído mecânico real, identifica a falha (Rolamento, Desalinhamento, etc).
        
        Responde neste formato JSON:
        {{
            "diagnosis": "...", 
            "confidence": "...", 
            "description": "...", 
            "estimated_cost": "Estimativa em Euros (ex: '50€ - 150€'). Se Normal: '0€'",
            "repair_time": "Tempo de paragem (ex: '2h - 4h'). Se Normal: '0h'",
            "steps": ["..."]
        }}
        """
        
        # A MAGIA ESTÁ AQUI: generation_config={"response_mime_type": "application/json"}
        response = model.generate_content(
            [prompt, {"mime_type": "audio/mp3", "data": audio_content}],
            generation_config={"response_mime_type": "application/json"}
        )
        
        print(f"DEBUG IA RAW: {response.text}") # Para vermos no terminal se falhar
        
        # Agora o texto é GARANTIDAMENTE JSON, não precisamos de limpar ```json
        data = json.loads(response.text)
        
        # --- GRAVAR NA BASE DE DADOS ---
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            # Convertemos o dicionário data para string JSON para guardar na coluna detalhes_json
            detalhes_str = json.dumps(data)
            
            c.execute("""
                INSERT INTO historico (user_email, maquina_nome, data_analise, diagnostico, confianca, detalhes_json, audio_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (email, "Nova Análise (Áudio)", agora, data.get("diagnosis"), data.get("confidence"), detalhes_str, db_audio_path))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"ERRO DB: {db_err}")
        return {
            "fault": data.get("diagnosis", "Falha Desconhecida"),
            "probability": data.get("confidence", "0%"),
            "description": data.get("description", "Sem descrição."),
            "estimated_cost": data.get("estimated_cost", "N/A"),
            "repair_time": data.get("repair_time", "N/A"),
            "checklist": data.get("steps", [])
        }
    except Exception as e:
        print(f"ERRO GERAL: {e}")
        return {
            "fault": "Erro Técnico",
            "probability": "0%",
            "description": f"Ocorreu um erro: {str(e)}",
            "checklist": ["Tentar novamente"]
        }

@app.get("/api/machines")
async def get_machines(email: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM maquinas WHERE user_email=?", (email,))
    columns = [desc[0] for desc in c.description]
    machines = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return machines

@app.post("/api/machines/add")
async def add_machine(machine: MachineRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO maquinas (user_email, nome, marca, modelo, categoria, data_instalacao) VALUES (?, ?, ?, ?, ?, ?)", 
                  (machine.user_email, machine.nome, machine.marca, machine.modelo, machine.categoria, machine.data_instalacao))
        conn.commit()
        return {"status": "success", "message": "Máquina adicionada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/activity")
async def get_activity(email: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    import datetime
    # Calc 24h ago
    # Note: dates are stored as YYYY-MM-DD HH:MM string
    # String comparison works for ISO-like dates
    # But we need the current time minus 24h string
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    
    c.execute("""
        SELECT maquina_nome, diagnostico, data_analise 
        FROM historico 
        WHERE user_email=? AND data_analise >= ? 
        ORDER BY data_analise DESC
    """, (email, cutoff))
    
    rows = c.fetchall()
    conn.close()
    
    return [
        {"maquina_nome": r[0], "diagnostico": r[1], "data_analise": r[2]}
        for r in rows
    ]

@app.get("/api/history")
async def get_history(email: str):
    from urllib.parse import unquote
    email = unquote(email)
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Query simplificada sem filtros
    c.execute("SELECT * FROM historico WHERE user_email=? ORDER BY id DESC", (email,))
    
    columns = [desc[0] for desc in c.description]
    history = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return history

@app.get("/adicionar-maquina", response_class=HTMLResponse)
async def read_add_machine():
    try:
        with open("adicionar_maquina.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: adicionar_maquina.html nao encontrado"

@app.get("/api/user/profile")
async def get_user_profile(email: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT nome, email, role, notificacoes_alertas, notificacoes_relatorios, preferencia_ia FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "nome": row[0],
            "email": row[1],
            "role": row[2],
            "notificacoes": {
                "alertas": bool(row[3]),
                "relatorios": bool(row[4])
            },
            "preferencia_ia": row[5]
        }
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/user/update")
async def update_user(data: UserUpdateRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    alertas = 1 if data.novas_notificacoes.get("alertas") else 0
    relatorios = 1 if data.novas_notificacoes.get("relatorios") else 0
    
    try:
        c.execute("""
            UPDATE users 
            SET nome=?, preferencia_ia=?, notificacoes_alertas=?, notificacoes_relatorios=? 
            WHERE email=?
        """, (data.novo_nome, data.novas_preferencias, alertas, relatorios, data.email_atual))
        conn.commit()
        return {"status": "success", "message": "Perfil atualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/user/change-password")
async def change_password(data: PasswordChangeRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(data.nova_password.encode()).hexdigest()
    
    c.execute("UPDATE users SET password=? WHERE email=?", (hashed_pw, data.email))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Password alterada"}

@app.delete("/api/user/delete")
async def delete_user(email: str = Body(..., embed=True)):
    # Note: Using Body(..., embed=True) expects JSON {"email": "..."} which matches typical POST/DELETE JSON bodies
    # Example raw body: {"email": "user@example.com"}
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Delete user
        c.execute("DELETE FROM users WHERE email=?", (email,))
        # Delete associated machines
        c.execute("DELETE FROM maquinas WHERE user_email=?", (email,))
        # Delete history
        c.execute("DELETE FROM historico WHERE user_email=?", (email,))
        
        conn.commit()
        return {"status": "success", "message": "Conta eliminada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- CHATBOT ENDPOINTS ---

# --- CHATBOT ENDPOINTS ---

@app.post("/api/chat/sessions")
async def create_session(request: SessionRequest):
    import datetime
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = request.title if request.title else "Nova Conversa"
    c.execute("INSERT INTO chat_sessions (user_email, title, created_at) VALUES (?, ?, ?)", (request.email, title, created_at))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": session_id, "title": title, "created_at": created_at}

@app.get("/api/chat/sessions")
async def get_sessions(email: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, title, created_at FROM chat_sessions WHERE user_email=? ORDER BY id DESC", (email,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]

@app.put("/api/chat/sessions/{session_id}")
async def rename_session(session_id: int, request: SessionRenameRequest):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE chat_sessions SET title=? WHERE id=? AND user_email=?", (request.title, session_id, request.email))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found or forbidden")
    conn.commit()
    conn.close()
    return {"status": "success", "title": request.title}

@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(session_id: int, email: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Verify ownership and existence
    c.execute("SELECT id FROM chat_sessions WHERE id=? AND user_email=?", (session_id, email))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found or forbidden")
    
    # Delete messages first
    c.execute("DELETE FROM chat_messages WHERE session_id=?", (session_id,))
    # Delete session
    c.execute("DELETE FROM chat_sessions WHERE id=?", (session_id,))
    
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/chat/history")
async def get_chat_history(email: str, session_id: int = None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if session_id:
        c.execute("SELECT role, content, timestamp FROM chat_messages WHERE user_email=? AND session_id=? ORDER BY id ASC", (email, session_id))
    else:
        # Fallback for old messages or if no session specified (though frontend should send it)
        # We try to return messages with NULL session or specific session
        c.execute("SELECT role, content, timestamp FROM chat_messages WHERE user_email=? AND (session_id IS NULL OR session_id=?) ORDER BY id ASC", (email, session_id))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

@app.post("/api/chat/send")
async def send_chat_message(request: ChatRequest):
    import datetime
    
    conn = None
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # 1. Fetch recent analysis context
        c.execute("SELECT maquina_nome, data_analise, diagnostico, detalhes_json FROM historico WHERE user_email=? ORDER BY id DESC LIMIT 3", (request.email,))
        history_rows = c.fetchall()
        
        context_str = "Histórico recente de análises do utilizador:\n"
        if not history_rows:
            context_str += "Nenhuma análise recente encontrada."
        else:
            for row in history_rows:
                # Handle potential None values safely
                m_name = row[0] if row[0] else "Desconhecido"
                m_date = row[1] if row[1] else "N/A"
                m_diag = row[2] if row[2] else "N/A"
                context_str += f"- Máquina: {m_name}, Data: {m_date}, Diagnóstico: {m_diag}\n"
        
        # 2. Get Chat History (Memory)
        chat_memory_str = ""
        if request.session_id:
            # Get last 10 messages
            c.execute("SELECT role, content FROM chat_messages WHERE session_id=? ORDER BY id ASC", (request.session_id,))
            messages = c.fetchall()
            # Take only last 10 to fit context window efficiently
            recent_messages = messages[-10:] 
            
            if recent_messages:
                chat_memory_str = "\nHISTÓRICO DA CONVERSA:\n"
                for role, content in recent_messages:
                    # Map role to simpler terms if needed, but 'user'/'assistant' is standard
                    role_name = "Utilizador" if role == "user" else "Samantha"
                    content_safe = content if content else ""
                    chat_memory_str += f"{role_name}: {content_safe}\n"

        # 3. Generate Title if New Session
        if request.session_id:
            c.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id=?", (request.session_id,))
            count_row = c.fetchone()
            count = count_row[0] if count_row else 0
            
            if count == 0:
                pass
                # DESATIVADO TEMPORARIAMENTE PARA POUPAR QUOTA (ERRO 429)
                # try:
                #     # Simple heuristic or AI call
                #     title_prompt = f"Gera um título muito curto (2 a 4 palavras) para uma conversa técnica que começa com: '{request.message}'"
                #     title_resp = model.generate_content(title_prompt)
                #     try:
                #         new_title = title_resp.text.strip().replace('"', '').replace("'", "").replace('*', '').replace('#', '')
                #     except ValueError:
                #         new_title = "Nova Conversa Técnica"
                #         
                #     c.execute("UPDATE chat_sessions SET title=? WHERE id=?", (new_title, request.session_id))
                #     conn.commit()
                # except Exception as e:
                #     print(f"Title Gen Error: {e}")
                #     pass 

        # 4. Save User Message
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO chat_messages (user_email, role, content, timestamp, session_id) VALUES (?, ?, ?, ?, ?)", 
                  (request.email, "user", request.message, timestamp, request.session_id))
        conn.commit()
        
        # 5. Call Gemini
        system_instruction = f"""
        És a Samantha, a assistente inteligente da EchoMechanic. És uma especialista em manutenção industrial, mas também és amigável e educada.
        
        O TEU PERFIL:
        - Podes responder a cumprimentos (Olá, Bom dia) e conversas casuais naturalmente.
        - Quando o assunto for técnico, sê precisa e profissional.
        - Falas português de Portugal.
        
        CONTEXTO TÉCNICO RECENTE (Análises):
        {context_str}
        
        {chat_memory_str}
        
        INSTRUÇÕES:
        - Usa o histórico da conversa para manter o contexto.
        - Sê útil e resolve o problema.
        """
        
        full_prompt = f"{system_instruction}\n\nUtilizador: {request.message}"
        
        try:
            response = model.generate_content(full_prompt)
            # Safe text access
            try:
                ai_response = response.text
            except ValueError:
                # Fallback if safety filters block the response
                ai_response = "Desculpa, não consigo processar esse pedido por questões de segurança ou política de conteúdo. Tenta reformular a tua questão técnica."
        except Exception as api_err:
            print(f"ERRO GEMINI CRÍTICO: {api_err}")
            ai_response = "Estou com dificuldades técnicas temporárias em aceder ao meu cérebro digital. Por favor, tenta novamente em instantes."
            
        # 6. Save AI Response
        timestamp_ai = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO chat_messages (user_email, role, content, timestamp, session_id) VALUES (?, ?, ?, ?, ?)", 
                  (request.email, "assistant", ai_response, timestamp_ai, request.session_id))
        conn.commit()
        
        return {"role": "assistant", "content": ai_response, "timestamp": timestamp_ai}
        
    except Exception as e:
        import traceback
        print("❌ ERRO CRÍTICO NO CHATBOT:")
        print(f"Tipo de Erro: {type(e)}")
        print(f"Mensagem: {e}")
        traceback.print_exc()  # Imprime a linha exata onde falhou
        
        # Fecha a conexão se estiver aberta para não bloquear a BD
        try:
            if conn:
                conn.close()
        except:
            pass
            
        return JSONResponse(content={
            "role": "assistant", 
            "content": "Estou com dificuldades técnicas. O erro interno foi registado na consola do servidor."
        }, status_code=200) # Retorna 200 para o frontend não crashar


# --- HELPER PARA LIMPAR TEXTO (REMOVE EMOJIS) ---
def clean_text(text):
    if not text:
        return ""
    # Converte para string se não for
    text = str(text)
    # Truque: Codifica para latin-1 (o que o FPDF suporta) e ignora/substitui o que não consegue (emojis)
    return text.encode('latin-1', 'replace').decode('latin-1')

@app.get("/api/report/pdf/{analysis_id}")
async def generate_pdf(analysis_id: int):
    try:
        # 1. Buscar dados à DB
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM historico WHERE id = ?", (analysis_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"error": "Análise não encontrada"}
        
        # 2. Configurar PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Barra de Marca
        pdf.set_fill_color(6, 182, 212) # Cyan da marca
        pdf.rect(0, 0, 210, 15, 'F')
        
        # Título
        pdf.set_y(5)
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(255, 255, 255) # Branco para o título sobre a barra
        pdf.cell(0, 10, clean_text("Relatório Técnico - EchoMechanic AI"), ln=True, align="C")
        
        pdf.set_text_color(0, 0, 0) # Reset para o resto do documento
        pdf.ln(10)
        
        # Dados da Máquina
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean_text("1. Identificação do Equipamento"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, clean_text(f"Máquina: {row['maquina_nome']}"), ln=True)
        pdf.cell(0, 8, clean_text(f"Data da Análise: {row['data_analise']}"), ln=True)
        pdf.cell(0, 8, clean_text(f"ID do Registo: #{row['id']}"), ln=True)
        pdf.ln(5)
        
        # Diagnóstico
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean_text("2. Diagnóstico da IA"), ln=True)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(200, 0, 0) # Vermelho escuro
        pdf.cell(0, 8, clean_text(f"Problema: {row['diagnostico']}"), ln=True)
        pdf.set_text_color(0, 0, 0) # Reset cor
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, clean_text(f"Confiança: {row['confianca']}"), ln=True)
        # Detalhes (Parse do JSON se existir)
        try:
            details = json.loads(row['detalhes_json'])
            desc = details.get("description", "Sem descrição")
            steps = details.get("steps", [])
            cost = details.get("estimated_cost", "Não disponível")
            time = details.get("repair_time", "Não disponível")
        except:
            desc = "Detalhes não disponíveis"
            steps = []
            cost = "Não disponível"
            time = "Não disponível"
            
        pdf.multi_cell(0, 8, clean_text(f"Descrição Técnica: {desc}"))
        pdf.cell(0, 8, clean_text(f"Custo Estimado: {cost}"), ln=True)
        pdf.cell(0, 8, clean_text(f"Tempo de Reparação: {time}"), ln=True)
        pdf.ln(5)
        
        # Plano de Ação
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean_text("3. Plano de Manutenção Recomendado"), ln=True)
        pdf.set_font("Arial", "", 11)
        
        for step in steps:
            pdf.cell(10) # Indentação
            # O clean_text aqui remove os emojis dos bullets se existirem
            pdf.multi_cell(0, 8, clean_text(f"- {step}"))
            
        # Rodapé
        pdf.ln(20)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 10, clean_text("Documento gerado automaticamente por EchoMechanic AI"), align="C")
        
        # 3. Output
        # Importante: bytes deve ser retornado corretamente
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        headers = {
            'Content-Disposition': f'attachment; filename="relatorio_analise_{analysis_id}.pdf"'
        }
        return Response(content=pdf_bytes, media_type='application/pdf', headers=headers)

    except Exception as e:
        print(f"ERRO PDF: {e}")
        return {"error": f"Erro ao gerar PDF: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)