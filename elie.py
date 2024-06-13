import streamlit as st
import openai
from PyPDF2 import PdfReader
import docx
import os
import json
from hashlib import sha256
import wikipedia
from dotenv import load_dotenv
import base64

# Cargar archivo .env
load_dotenv()

# Configuración de Wikipedia
wikipedia.set_lang("es")  # Cambia el idioma a español, si lo necesitas

# Archivos para almacenar datos
USER_DATA_FILE = 'users.json'
SESSION_DATA_DIR = 'sessions'
PROMPTS_DATA_FILE = 'prompts.json'

# Crear directorios necesarios
if not os.path.exists(SESSION_DATA_DIR):
    os.makedirs(SESSION_DATA_DIR)

# Funciones de manejo de usuarios


def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_user_data(user_data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f)


def load_prompts_data():
    if os.path.exists(PROMPTS_DATA_FILE):
        with open(PROMPTS_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_prompts_data(prompts_data):
    with open(PROMPTS_DATA_FILE, 'w') as f:
        json.dump(prompts_data, f)


user_data = load_user_data()
prompts_data = load_prompts_data()


def load_session_data(username):
    session_file = os.path.join(SESSION_DATA_DIR, f'{username}_session.json')
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            return json.load(f)
    return {"chat_history": [], "files": [], "selected_prompts": [], "api_key": "", "profile_pic": "", "contact_info": "", "personal_info": {}}


def save_session_data(username, session_data):
    # Convert profile_pic bytes to base64 string if necessary
    if isinstance(session_data.get("profile_pic"), bytes):
        session_data["profile_pic"] = base64.b64encode(
            session_data["profile_pic"]).decode("utf-8")
    session_file = os.path.join(SESSION_DATA_DIR, f'{username}_session.json')
    with open(session_file, 'w') as f:
        json.dump(session_data, f)


def hash_password(password):
    return sha256(password.encode()).hexdigest()


def search_wikipedia(query):
    try:
        summary = wikipedia.summary(query, sentences=3)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"La consulta es ambigua, podría referirse a uno de los siguientes: {e.options}"
    except wikipedia.exceptions.PageError:
        return "No se encontró ninguna página que coincida con la consulta"


def truncate_text(text, max_tokens):
    tokens = text.split()  # Una forma muy simplista de contar tokens
    if len(tokens) > max_tokens:
        return ' '.join(tokens[:max_tokens]) + "..."
    return text


# Funciones para leer archivos
def read_text_file(file):
    return file.read().decode("utf-8")


def read_pdf_file(file):
    pdf_reader = PdfReader(file)
    content = ""
    for page in pdf_reader.pages:
        content += page.extract_text()
    print(content)  # Debug print to troubleshoot issues during extraction
    return content


def read_docx_file(file):
    doc = docx.Document(file)
    content = []
    for paragraph in doc.paragraphs:
        content.append(paragraph.text)
    return "\n".join(content)


# Configuración de la interfaz de Streamlit
st.set_page_config(page_title="Asistente Interactivo", page_icon=":robot_face:", layout="wide")

# Inicializar el estado de la sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.session_data = {"chat_history": [], "files": [], "selected_prompts": [], "api_key": "", "profile_pic": "", "contact_info": "", "personal_info": {}}
    st.session_state.enter_pressed = False

# Asegurarse de que las claves estén en session_data
keys_to_check = ["chat_history", "files", "selected_prompts", "api_key", "profile_pic", "contact_info", "personal_info"]
for key in keys_to_check:
    if key not in st.session_state.session_data:
        st.session_state.session_data[key] = ""

# Funciones de autenticación
def login_user(username, password):
    hashed_pwd = hash_password(password)
    if username in user_data and user_data[username] == hashed_pwd:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.session_data = load_session_data(username)

        # Asegurarse de que las claves estén en session_data
        for key in keys_to_check:
            if key not in st.session_state.session_data:
                st.session_state.session_data[key] = ""
        
        # Crear un archivo para prompts de usuario si no existe
        if username not in prompts_data:
            prompts_data[username] = {}
            save_prompts_data(prompts_data)

        st.success(f"Bienvenido {username}")
    else:
        st.error("Nombre de usuario o contraseña incorrectos")


def register_user(new_username, new_password):
    if new_username in user_data:
        st.error("El nombre de usuario ya está en uso")
    else:
        user_data[new_username] = hash_password(new_password)
        save_user_data(user_data)

        # Crear un archivo para prompts de usuario
        prompts_data[new_username] = {}
        save_prompts_data(prompts_data)

        st.success("Usuario registrado con éxito")


def update_profile_info(uploaded_profile_pic, contact_info, api_key, personal_info):
    if uploaded_profile_pic is not None:
        st.session_state.session_data['profile_pic'] = uploaded_profile_pic.getvalue()
    st.session_state.session_data['contact_info'] = contact_info
    st.session_state.session_data['api_key'] = api_key
    st.session_state.session_data['personal_info'] = personal_info
    save_session_data(st.session_state.username, st.session_state.session_data)
    st.success("Perfil actualizado")


if st.session_state.logged_in:
    if not st.session_state.session_data['api_key']:
        st.warning("Por favor, configure su API Key antes de continuar.")
        api_key = st.text_input("API Key", type="password")
        if st.button("Guardar API Key"):
            st.session_state.session_data['api_key'] = api_key
            save_session_data(st.session_state.username, st.session_state.session_data)
            st.experimental_rerun()
    else:
        # Display profile pic in the top-right corner
        profile_pic_url = ""
        if st.session_state.session_data['profile_pic']:
            profile_pic = st.session_state.session_data['profile_pic']
            profile_pic_url = os.path.join(SESSION_DATA_DIR, f"{st.session_state.username}_profile_pic.png")
            if isinstance(profile_pic, bytes):
                with open(profile_pic_url, "wb") as f:
                    f.write(profile_pic)
            else:
                with open(profile_pic_url, "wb") as f:
                    f.write(base64.b64decode(profile_pic))
            image_exists = os.path.exists(profile_pic_url)
        else:
            image_exists = False

        if image_exists:
            st.sidebar.image(profile_pic_url, width=50)

        selected_option = st.sidebar.radio("Menú de Usuario", ["Asistente", "Perfil", "Salir"])

        if selected_option == "Asistente":
            st.header(f"Bienvenido, {st.session_state.username}!")

            # Sidebar para configuración y archivos
            st.sidebar.title("Menú")

            with st.sidebar.expander("Ajustes"):
                # Configuración de temperatura y tokens
                temperature = st.slider("Ajuste de Temperatura", min_value=0.0, max_value=1.0, step=0.1, value=0.5)
                max_tokens = st.slider("Ajuste de Max Tokens", min_value=50, max_value=500, step=50, value=150)

            with st.sidebar.expander("Archivos"):
                st.markdown("### Archivos subidos")
                # Mostrar los archivos subidos previamente
                if st.session_state.session_data["files"]:
                    for idx, file in enumerate(st.session_state.session_data["files"]):
                        col_file, col_delete = st.columns([4, 1])
                        col_file.write(file["name"])
                        delete_button = col_delete.button("🗑️", key=f"delete_{idx}")
                        if delete_button:
                            st.session_state.session_data["files"].pop(idx)
                            save_session_data(st.session_state.username, st.session_state.session_data)
                            st.experimental_rerun()

                # Evitar duplicación de archivos
                uploaded_files = st.file_uploader("Sube tus archivos aquí", type=["txt", "pdf", "docx"], accept_multiple_files=True)
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        file_type = uploaded_file.type
                        try:
                            if file_type == "text/plain":
                                file_content = read_text_file(uploaded_file)
                            elif file_type == "application/pdf":
                                file_content = read_pdf_file(uploaded_file)
                            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                                file_content = read_docx_file(uploaded_file)
                            else:
                                st.error("Tipo de archivo no soportado: " + uploaded_file.name)
                                continue

                            # Trunca el contenido del archivo si es demasiado largo
                            truncated_content = truncate_text(file_content, 1000) 
                            if not any(f['name'] == uploaded_file.name for f in st.session_state.session_data["files"]):
                                st.session_state.session_data["files"].append({"name": uploaded_file.name, "type": file_type, "content": truncated_content})
                        except Exception as e:
                            st.error(f"Error leyendo el archivo {uploaded_file.name}: {e}")
                    save_session_data(st.session_state.username, st.session_state.session_data)

            with st.sidebar.expander("Prompts"):
                st.markdown("### Proveer Prompts al Asistente")
                prompt_title = st.text_input("Título del Prompt")
                prompt_content = st.text_area("Contenido del Prompt")
                if st.button("Guardar Prompt"):
                    if prompt_title and prompt_content:
                        user_prompts = prompts_data.get(st.session_state.username, {})
                        user_prompts[prompt_title] = prompt_content
                        prompts_data[st.session_state.username] = user_prompts
                        save_prompts_data(prompts_data)
                        st.success("Prompt guardado")
                    else:
                        st.warning("Por favor, complete tanto el título como el contenido del Prompt")

                st.markdown("### Prompts Guardados")
                user_prompts = prompts_data.get(st.session_state.username, {})

                for title, content in user_prompts.items():
                    col_prompt, col_select, col_delete = st.columns([4, 1, 1])
                    col_prompt.markdown(f"**{title}**")
                    if col_select.checkbox("", key=f"select_{title}", value=title in st.session_state.session_data["selected_prompts"]):
                        if title not in st.session_state.session_data["selected_prompts"]:
                            st.session_state.session_data["selected_prompts"].append(title)
                            save_session_data(st.session_state.username, st.session_state.session_data)
                    else:
                        if title in st.session_state.session_data["selected_prompts"]:
                            st.session_state.session_data["selected_prompts"].remove(title)
                            save_session_data(st.session_state.username, st.session_state.session_data)

                    if col_delete.button("🗑️", key=f"delete_prompt_{title}"):
                        del user_prompts[title]
                        prompts_data[st.session_state.username] = user_prompts
                        save_prompts_data(prompts_data)
                        st.experimental_rerun()

            # Columnas para entrada de usuario y chat
            col1, col2 = st.columns([1, 3])  # Distribuir ancho de columnas

            with col1:
                if st.button("Limpiar Chat"):
                    st.session_state.session_data["chat_history"] = []
                    save_session_data(st.session_state.username, st.session_state.session_data)

            with col2:
                # Interacción con el asistente
                user_input = st.text_input("Escribe tu pregunta:", key='chat_input')
                search_web = st.checkbox('Buscar en la web', key='search_web')
                libre_chat = st.checkbox('Libre Chat (Playground)', key='libre_chat')

                if search_web:
                    st.markdown("🟢 El asistente buscará información en Wikipedia además de usar el contenido de los archivos subidos.")

                if libre_chat:
                    st.markdown("🟢 Estás en modo Libre Chat con el asistente.")

                def send_message():
                    if st.session_state.chat_input:
                        messages = []
                        if st.session_state.libre_chat:
                            messages = [
                                {"role": "system", "content": "Eres un asistente amigable y servicial que puede conversar libremente con el usuario."},
                                {"role": "user", "content": st.session_state.chat_input}
                            ]
                        else:
                            if st.session_state.session_data["files"] or st.session_state.search_web:
                                try:
                                    all_file_contents = "\n".join([file["content"] for file in st.session_state.session_data["files"]]) if st.session_state.session_data["files"] else ""
                                    # Truncar el contenido combinado si es necesario
                                    truncated_all_file_contents = truncate_text(all_file_contents, 2000)
                                    messages = [
                                        {"role": "system", "content": "Eres un asistente amigable y servicial que responderá preguntas basándose específicamente en el contenido proporcionado."},
                                        {"role": "system", "content": f"Contenido de los archivos (truncado):\n{truncated_all_file_contents}"}
                                    ]
                                    if st.session_state.search_web:
                                        search_results = search_wikipedia(st.session_state.chat_input)
                                        messages.append({"role": "system", "content": f"Resultados de la búsqueda en Wikipedia:\n{search_results}"})
                                        st.session_state.search_results = search_results

                                    user_prompts = prompts_data.get(st.session_state.username, {})

                                    for prompt_title in st.session_state.session_data["selected_prompts"]:
                                        if prompt_title in user_prompts:
                                            messages.append({"role": "system", "content": user_prompts[prompt_title]})

                                    messages.append({"role": "user", "content": st.session_state.chat_input})
                                except Exception as e:
                                    st.error(f"Error: {e}")
                            else:
                                st.error("Primero sube uno o más archivos o permite la búsqueda en la web para preguntar sobre contenido externo.")

                        if messages:  # Ensure we have messages to send
                            try:
                                # Usar la clave API del usuario
                                openai.api_key = st.session_state.session_data['api_key']
                                response = openai.ChatCompletion.create(
                                    model="gpt-4",
                                    messages=messages,
                                    temperature=temperature,
                                    max_tokens=max_tokens
                                )
                                # Agregar la entrada del usuario y la respuesta del asistente al historial de chat
                                st.session_state.session_data["chat_history"].append({"role": "user", "content": st.session_state.chat_input})
                                st.session_state.session_data["chat_history"].append({"role": "assistant", "content": response.choices[0].message['content'].strip()})
                                # Guardar el historial de chat en la sesión
                                save_session_data(st.session_state.username, st.session_state.session_data)
                                # Limpiar el contenido de entrada
                                st.session_state.chat_input = ''
                            except Exception as e:
                                st.error(f"Error: {e}")

                # Añadir un botón para enviar el mensaje
                st.button("Enviar", on_click=send_message)

                # Mostrar el historial de chat
                st.markdown("### Historial de Chat")
                for chat in st.session_state.session_data["chat_history"]:
                    if chat["role"] == "user":
                        st.markdown(f"**Usuario:** {chat['content']}")
                    else:
                        st.markdown(f"**Asistente:** {chat['content']}")

        elif selected_option == "Perfil":
            st.header("Perfil de Usuario")

            # Opciones de perfil
            profile_options = ["Información Personal", "Archivos", "Prompts", "Foto de Perfil", "API Key"]
            selected_profile_option = st.selectbox("Selecciona una opción", profile_options, index=0)

            def personal_info_section():
                st.subheader("Información Personal")
                personal_info = st.session_state.session_data.get("personal_info", {})
                if isinstance(personal_info, str):  # Si por error se almacena como string
                    personal_info = {}
                first_name = st.text_input("Nombre", value=personal_info.get("first_name", ""))
                last_name = st.text_input("Apellido", value=personal_info.get("last_name", ""))
                email = st.text_input("Correo Electrónico", value=personal_info.get("email", ""))
                discord = st.text_input("Discord", value=personal_info.get("discord", ""))
                slack = st.text_input("Slack", value=personal_info.get("slack", ""))
                if st.button("Guardar Información Personal"):
                    st.session_state.session_data["personal_info"] = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "discord": discord,
                        "slack": slack
                    }
                    save_session_data(st.session_state.username, st.session_state.session_data)
                    st.success("Información Personal Actualizada")

            def files_section():
                st.subheader("Archivos Subidos")
                st.markdown("### Archivos subidos")
                # Mostrar los archivos subidos previamente
                if st.session_state.session_data["files"]:
                    for idx, file in enumerate(st.session_state.session_data["files"]):
                        col_file, col_delete = st.columns([4, 1])
                        col_file.write(file["name"])
                        delete_button = col_delete.button("🗑️", key=f"delete_{idx}_profile")
                        if delete_button:
                            st.session_state.session_data["files"].pop(idx)
                            save_session_data(st.session_state.username, st.session_state.session_data)
                            st.experimental_rerun()
                             # Carga de archivos múltiples
                uploaded_files = st.file_uploader("Sube tus archivos aquí", type=["txt", "pdf", "docx"], accept_multiple_files=True)
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        file_type = uploaded_file.type
                        try:
                            if file_type == "text/plain":
                                file_content = read_text_file(uploaded_file)
                            elif file_type == "application/pdf":
                                file_content = read_pdf_file(uploaded_file)
                            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                                file_content = read_docx_file(uploaded_file)
                            else:
                                st.error("Tipo de archivo no soportado: " + uploaded_file.name)
                                continue

                            # Trunca el contenido del archivo si es demasiado largo
                            truncated_content = truncate_text(file_content, 1000)
                            if not any(f['name'] == uploaded_file.name for f in st.session_state.session_data["files"]):
                                st.session_state.session_data["files"].append({"name": uploaded_file.name, "type": file_type, "content": truncated_content})
                        except Exception as e:
                            st.error(f"Error leyendo el archivo {uploaded_file.name}: {e}")
                    save_session_data(st.session_state.username, st.session_state.session_data)

            def prompts_section():
                st.subheader("Prompts Guardados")
                st.markdown("### Prompts Guardados")
                user_prompts = prompts_data.get(st.session_state.username, {})
                for title, content in user_prompts.items():
                    col_prompt, col_edit, col_delete = st.columns([4, 1, 1])
                    col_prompt.markdown(f"**{title}**")
                    if col_edit.button("✏️", key=f"edit_prompt_{title}"):
                        new_title = st.text_input("Editar título", value=title)
                        new_content = st.text_area("Editar contenido", value=content)
                        if st.button("Guardar Cambios", key=f"save_{title}"):
                            del user_prompts[title]  # Elimina el prompt antiguo
                            user_prompts[new_title] = new_content  # Añade el prompt actualizado
                            prompts_data[st.session_state.username] = user_prompts
                            save_prompts_data(prompts_data)
                            st.experimental_rerun()
                    if col_delete.button("🗑️", key=f"delete_prompt_{title}"):
                        del user_prompts[title]
                        prompts_data[st.session_state.username] = user_prompts
                        save_prompts_data(prompts_data)
                        st.experimental_rerun()

            def profile_pic_section():
                st.subheader("Foto de Perfil")
                uploaded_profile_pic = st.file_uploader("Sube tu foto de perfil", type=["jpg", "png"])
                if uploaded_profile_pic is not None:
                    # Guarda la foto de perfil en session_data
                    st.session_state.session_data['profile_pic'] = uploaded_profile_pic.getvalue()
                    save_session_data(st.session_state.username, st.session_state.session_data)
                    st.image(uploaded_profile_pic, width=50)
                elif st.session_state.session_data['profile_pic']:
                    profile_pic = st.session_state.session_data['profile_pic']
                    if isinstance(profile_pic, str):  # Decode from base64
                        profile_pic = base64.b64decode(profile_pic)
                    st.image(profile_pic, width=50)
                # Botón para eliminar la foto de perfil
                if st.button("Eliminar Foto de Perfil"):
                    st.session_state.session_data['profile_pic'] = ""
                    save_session_data(st.session_state.username, st.session_state.session_data)
                    st.experimental_rerun()

            def api_key_section():
                st.subheader("API Key")
                current_api_key = st.session_state.session_data['api_key']
                if current_api_key:
                    st.markdown(f"**API Key actual:** {current_api_key}")
                    # Opción para eliminar la API Key
                    if st.button("Eliminar API Key"):
                        st.session_state.session_data['api_key'] = ""
                        save_session_data(st.session_state.username, st.session_state.session_data)
                        st.success("API Key eliminada")
                        st.experimental_rerun()
                else:
                    st.warning("No tienes una API Key configurada.")
                new_api_key = st.text_input("Escribe tu nueva API Key", type="password")
                if st.button("Guardar API Key"):
                    st.session_state.session_data['api_key'] = new_api_key
                    save_session_data(st.session_state.username, st.session_state.session_data)
                    st.success("API Key guardada")
                    st.experimental_rerun()

            if selected_profile_option == "Información Personal":
                personal_info_section()
            elif selected_profile_option == "Archivos":
                files_section()
            elif selected_profile_option == "Prompts":
                prompts_section()
            elif selected_profile_option == "Foto de Perfil":
                profile_pic_section()
            elif selected_profile_option == "API Key":
                api_key_section()

            if st.button("Volver al Asistente"):
                st.session_state.selected_option = "Asistente"
                st.experimental_rerun()

        elif selected_option == "Salir":
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.session_data = {"chat_history": [], "files": [], "selected_prompts": [], "api_key": "", "profile_pic": "", "contact_info": "", "personal_info": {}}
            st.experimental_rerun()
else:
    st.warning("Por favor, inicie sesión para continuar.")

if not st.session_state.logged_in:
    tab_names = ["Iniciar sesión", "Registrarse"]
    tabs = st.tabs(tab_names)

    # Centrar el formulario de inicio de sesión y registro
    tab_content = [st.empty() for _ in range(2)]

    with tabs[0]:
        st.header("Iniciar sesión")
        with st.form("login_form"):
            tab_content[0].markdown("""
             <div style="display: flex; justify-content: center; align-items: center; height: 400px;">
             <div style="background-color: #666; padding: 30px; border-radius: 10px;">
             <h2 style="color: white;">Iniciar sesión</h2>
             """, unsafe_allow_html=True)
            username = st.text_input("Nombre de usuario", key="login_username")
            password = st.text_input("Contraseña", type="password", key="login_password")
            tab_content[0].markdown("</div></div>", unsafe_allow_html=True)
            login_button = st.form_submit_button("Iniciar sesión")
            if st.session_state.enter_pressed or login_button:
                login_user(username, password)

    with tabs[1]:
        st.header("Registrarse")
        with st.form("register_form"):
            tab_content[1].markdown("""
             <div style="display: flex; justify-content: center; align-items: center; height: 400px;">
             <div style="background-color: #666; padding: 30px; border-radius: 10px;">
             <h2 style="color: white;">Registrarse</h2>
             """, unsafe_allow_html=True)
            new_username = st.text_input("Crea un nombre de usuario", key="register_username")
            new_password = st.text_input("Crea una contraseña", type="password", key="register_password")
            tab_content[1].markdown("</div></div>", unsafe_allow_html=True)
            register_button = st.form_submit_button("Registrarse")
            if st.session_state.enter_pressed or register_button:
                register_user(new_username, new_password)

# Añadir estilo CSS para una apariencia personalizada y fondo de pantalla
background_image_path = os.path.join("imagen", "elie.avif")
background_image = base64.b64encode(open(background_image_path, "rb").read()).decode()

st.markdown(f"""
<style>
body {{
 background: url('data:image/avif;base64,{background_image}') no-repeat center center fixed;
 background-size: cover;
 color: #FFFFFF;
 font-family: Arial, sans-serif;
}}
/* Headers */
.stheader {{
 font-size: 2em;
 padding: 20px;
 margin-bottom: 10px;
}}
/* Sidebar styling */
.stSidebar {{
 background-color: #444444; /* Un fondo oscuro para la barra lateral */
 color: #FFFFFF;
}}
.stSidebar button {{
 background-color: #555555;
 color: #FFFFFF;
 padding: 10px;
 border-radius: 5px;
 margin: 10px;
 border: none;
 width: 200px;
}}
.stSidebar button:hover {{
 background-color: #666666;
}}
.stSidebar button:active {{
 background-color: #888888;
}}
.stSidebar button:focus {{
 outline: none;
}}
.stSidebar .css-yeqnw6 .stButton {{
 padding: 5px;
}}
/* Chat history box */
.chat-box {{
 border: 1px solid #888888;
 padding: 10px;
 border-radius: 10px;
 margin: 10px 0;
 background: #222222;
 color: #FFFFFF;
}}
/* Auth form styling */
.auth-title {{
 font-size: 1.5em;
 margin-bottom: 10px;
 color: #FFFFFF;
 text-align: center;
}}
form {{
 background-color: #444444; /* Form background */
 padding: 15px;
 border-radius: 10px;
 margin-top: 20px;
 width: 300px;
 margin: 0 auto; /* Centramos el form */
 position: absolute; /* Hacemos que el form flote en la pantalla */
 top: 50%;
 left: 50%;
 transform: translate(-50%, -50%); /* Lo centramos */
}}
form label {{
 color: #FFFFFF; /* Labels */
 font-weight: bold;
}}
form input[type="text"], form input[type="password"] {{
 background-color: #333333; /* Inputs */
 color: #FFFFFF;
 border: 1px solid #555555;
 border-radius: 5px;
 padding: 10px;
 margin-bottom: 10px;
 width: 100%;
}}
/* Botones */
button.st-eb {{
 background-color: #444444; /* Un color para los botones */
 color: #FFFFFF;
 border: 1px solid #555555;
 border-radius: 5px;
 padding: 10px;
 margin: 5px;
}}
button.st-eb:hover {{
 background-color: #666666;
}}
.button-container {{
 display: flex;
 justify-content: space-between;
}}
/* Footer styling */
.footer {{
 position: fixed;
 left: 0;
 bottom: 0;
 width: 100%;
 background-color: #000000;
 color: white;
 text-align: center;
 padding: 5px 0;
}}
</style>
<div class="footer">
<p>Hecho por Matias (Pttwnz)</p>
</div>
""", unsafe_allow_html=True)

# Capturar enter para enviar mensajes
if st.session_state.get('chat_input', ''):
    st.session_state.enter_pressed = st.session_state['chat_input'][-1] == '\n'
    if st.session_state.enter_pressed:
        send_message()  # Llamada a send_message cuando se presiona Enter                                                    