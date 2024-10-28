# Import necessary libraries
import streamlit as st
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationEntityMemory
from langchain.chains.conversation.prompt import ENTITY_MEMORY_CONVERSATION_TEMPLATE
from langchain_community.chat_models import ChatOpenAI
import speech_recognition as sr
from gtts import gTTS
from io import BytesIO
import base64
from database_connection import DataConnection
import bcrypt
import pandas as pd

# Set Streamlit page configuration
st.set_page_config(page_title="ChatBot🤖", layout="centered")

hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Initialize session states
if "generated" not in st.session_state:
    st.session_state["generated"] = []
if "past" not in st.session_state:
    st.session_state["past"] = []
if "input" not in st.session_state:
    st.session_state["input"] = ""
if "stored_session" not in st.session_state:
    st.session_state["stored_session"] = []

# Initialize database connection
db = DataConnection()
db.create_tables()  # Create tables when the application starts

# Define chatbot name
CHATBOT_NAME = "Dế Mèn"

# Thêm phần giới thiệu thân thiện và nhiệt tình
def chatbot_welcome():
    st.title(f"Chào mừng bạn đến với {CHATBOT_NAME}! 🤖")
    st.write(f"""
    Xin chào các bạn! Tôi là {CHATBOT_NAME}, hôm nay tôi rất vinh dự được làm hướng dẫn viên du lịch của các bạn.
    Với đôi cánh khỏe khoắn và kinh nghiệm phiêu lưu qua nhiều miền đất lạ, tôi sẽ đón tiếp và hướng dẫn các bạn trong hành trình này.
    Nhiệm vụ của tôi là sắp xếp mọi việc thật chu đáo, từ chỗ ở, ăn uống, đến việc đi lại nghỉ ngơi, đảm bảo các bạn có một trải nghiệm du lịch tuyệt vời nhất.
    Nếu có bất kỳ tình huống phát sinh nào, đừng lo lắng! Tôi sẽ có cách giải quyết nhanh chóng và hợp lý.
    Chuyến hành trình của chúng ta sẽ đưa các bạn đến những địa điểm độc đáo, nơi mỗi nơi đều ẩn chứa những câu chuyện hấp dẫn và những bí mật ít ai biết đến.
    Tôi sẽ cùng các bạn khám phá từng điều kỳ thú và bí ẩn trong suốt chuyến đi này!
    """)
chatbot_welcome()

# Giao diện người dùng cho đăng nhập và đăng ký
st.subheader("Tạo tài khoản để bắt đầu hành trình cùng tôi nào!")
username = st.text_input("Username")
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Register"):
    if username and email and password:
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Check if user already exists
        if db.check_user_exists(username, email):
            st.error("Người dùng đã tồn tại. Hãy thử đăng nhập.")
        else:
            # Register user
            db.register_user(username, email, hashed_password.decode('utf-8'))
            st.success("Đăng ký thành công!")
    else:
        st.error("Vui lòng nhập đầy đủ thông tin.")

# Giao diện đăng nhập
st.subheader("Đăng nhập để tiếp tục chuyến hành trình!")
login_username = st.text_input("Tên đăng nhập", key="login_username")
login_password = st.text_input("Mật khẩu", type="password", key="login_password")

if st.button("Login"):
    if db.authenticate_user(login_username, login_password):
        st.success(f"Xin chào {login_username}, bạn đã đăng nhập thành công!")
        
        # After successful login, show import and export options
        st.subheader("Quản lý dữ liệu")

        # Import data
        st.subheader("Nhập dữ liệu")
        uploaded_file = st.file_uploader("Chọn file CSV", type="csv")
        if uploaded_file is not None:
            db.import_data(uploaded_file)
            st.success("Dữ liệu đã được nhập thành công!")

        # Export data
        st.subheader("Xuất dữ liệu")
        table_name = st.selectbox("Chọn bảng để xuất", ["Location", "User", "Review"])
        if st.button("Xuất"):
            export_file_path = f"{table_name}_data.csv"
            db.export_data(table_name, export_file_path)
            st.success(f"Dữ liệu đã xuất thành công đến {export_file_path}!")

# Get user input (text or speech)
def get_text():
    input_text = st.text_input(
        "You: ",
        st.session_state["input"],
        key="input",
        placeholder="Your AI assistant is here! Ask me anything ...",
        label_visibility="hidden",
    )

    use_voice = st.checkbox("Sử dụng giọng nói")
    
    if use_voice:
        language_choice = st.radio("Chọn ngôn ngữ cho nhận diện giọng nói:", ("English", "Vietnamese"))
        
        if st.button("Bắt đầu ghi âm"):
            r = sr.Recognizer()
            with sr.Microphone() as source:
                st.write("Đang nghe... Vui lòng nói.")
                audio = r.listen(source)
                try:
                    if language_choice == "English":
                        input_text = r.recognize_google(audio, language="en-US")
                    else:
                        input_text = r.recognize_google(audio, language="vi-VN")
                    st.write(f"Bạn nói: {input_text}")
                except sr.UnknownValueError:
                    st.write("Xin lỗi, tôi không thể nhận diện giọng nói.")
                except sr.RequestError as e:
                    st.write(f"Lỗi kết nối tới dịch vụ nhận diện giọng nói; {e}")

    return input_text, language_choice if use_voice else "English"

# Convert text to speech and play it
def text_to_speech(text, language):
    tts = gTTS(text=text, lang='en' if language == 'English' else 'vi', slow=False)
    audio_file = BytesIO()
    tts.write_to_fp(audio_file)
    audio_file.seek(0)
    
    audio_bytes = audio_file.getvalue()
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

# Get user input and language choice
user_input, lang_choice = get_text()

# Set up the chatbot model
MODEL = st.sidebar.selectbox(label='Model', options=['gpt-3.5-turbo', 'text-davinci-003', 'text-davinci-002'])
API_O = "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"

if API_O:
    llm = ChatOpenAI(temperature=0, openai_api_key=API_O, model_name=MODEL, verbose=False)

    if "entity_memory" not in st.session_state:
        st.session_state.entity_memory = ConversationEntityMemory(llm=llm)

    Conversation = ConversationChain(
        llm=llm,
        prompt=ENTITY_MEMORY_CONVERSATION_TEMPLATE,
        memory=st.session_state.entity_memory,
    )

# Generate the output using ConversationChain
if user_input:
    # Check if the user is asking for the chatbot's name
    if "tên" in user_input.lower() and "gì" in user_input.lower():
        if "bạn" in user_input.lower() or "của bạn" in user_input.lower():
            output = f"Tên của tôi là {CHATBOT_NAME}!"
        else:
            output = "Bạn có thể cho tôi biết tên của bạn không?"
    else:
        output = Conversation.run(input=user_input)

    st.session_state.past.append(user_input)
    st.session_state.generated.append(output)
    st.success(f"Chatbot: {output}")

    if lang_choice == "English":
        text_to_speech(output, language="en")
    else:
        text_to_speech(output, language="vi")

with st.expander("Lịch sử hội thoại"):
    for i, (query, response) in enumerate(zip(st.session_state.past, st.session_state.generated)):
        st.info(f"Bạn: {query}")
        st.success(f"Chatbot: {response}")
        if i < len(st.session_state.past) - 1:
            st.write("---")
