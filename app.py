#Import necessary libaries
import streamlit as st
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationEntityMemory
from langchain.chains.conversation.prompt import ENTITY_MEMORY_CONVERSATION_TEMPLATE
from langchain_community.chat_models import ChatOpenAI
import speech_recognition as sr
from gtts import gTTS
from io import BytesIO
import base64

#Set Streamlit page configuration

st.set_page_config(page_title="ChatBot🤖", layout="centered")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

#Initialize session states

if "generated" not in st.session_state:
    st.session_state["generated"] = []
if "past" not in st.session_state:
    st.session_state["past"] = []
if "input" not in st.session_state:
    st.session_state["input"] = ""
if "stored_session" not in st.session_state:
    st.session_state["stored_session"] = []

#Define function to get user input(text of speech)
def get_text():
    """
    Get the user input text or use speech recognition for either English or Vietnamese.
    Return:
        (str): The text entered or spoken by user 
        (str): The language choice for speech recognition ('English' or 'Vietnamese')
    """
    #Get input from the user throught text
    input_text = st.text_input(
        "You: ",
        st.session_state["input"],
        key="input",
        placeholder="Your AI assistant is here! Ask me anything ...",
        label_visibility="hidden",
    )

    #Add option to use voice
    # Add option to use voice
    use_voice = st.checkbox("Use voice input")
    
    if use_voice:
        language_choice = st.radio("Choose language for speech recognition:", ("English", "Vietnamese"))
        
        if st.button("Start Recording"):
            r = sr.Recognizer()
            with sr.Microphone() as source:
                st.write("Listening...")
                audio = r.listen(source)
                
            try:
                if language_choice == "English":
                    input_text = r.recognize_google(audio, language="en-US")
                else:
                    input_text = r.recognize_google(audio, language="vi-VN")
                st.write(f"You said: {input_text}")
            except sr.UnknownValueError:
                st.write("Sorry, I couldn't understand that.")
            except sr.RequestError:
                st.write("Sorry, there was an error with the speech recognition service.")

    return input_text, language_choice if use_voice else "English"

#Define function to convert text to speech and play it
def text_to_speech(text, language):
    """
    Convert text to speech and play it.
    
    Args:
        text (str): The text to be converted to speech.
        language (str): The language of the text ('English' or 'Vietnamese').
    """
    tts = gTTS(text=text, lang='en' if language == 'English' else 'vi', slow=False)
    audio_file = BytesIO() #use BytesIO to save audio as byte data
    tts.write_to_fp(audio_file) 
    audio_file.seek(0) # reset file pointer to begining
    
    # Encode the audio file as base64 to play in Streamlit
    audio_bytes = audio_file.getvalue()
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True) # Insert audio into the page

# set up the Streamlit app layout
st.title("🤖 ChatBot 🤖")
MODEL = st.sidebar.selectbox(label='Model', options=['gpt-3.5-turbo', 'text-davinci-003', 'text-davinci-002'])

# Ask the user to enter their OpenAI API key
API_O = st.text_input(
    "blue:[Enter your OpenAI API-KEY: ]",
    placeholder="Paste your OpenAI API-KEY here:",
    type="password",
)

# Session state storage would be ideal

if API_O:
    # Create an OpenAI instance
    llm = ChatOpenAI(temperature=0, openai_api_key = API_O, model_name = MODEL, verbose= False)

    # Create a ConversationEntityMemory object if not already created
    if "entity_memory" not in st.session_state:
        st.session_state.entity_memory = ConversationEntityMemory(llm=llm)

    #Create the ConversationChain object with the specified configuration
    Conversation = ConversationChain(
        llm= llm,
        prompt = ENTITY_MEMORY_CONVERSATION_TEMPLATE,
        memory = st.session_state.entity_memory,
    )
else:
    st.markdown(
        """ 
        ```        
        - 1. Enter API Key + Hit enter  
        - 2. Ask anything via the text input widget
        ```
        """
    )
    st.sidebar.warning(
        "API key required to try this app. The API key is not stored in any form."
    )

#Get user input(text or speech) and language choice
user_input, lang_choice = get_text()

#Generate the output using the ConversationChain object and user input, and add the input/ouput to sesstion
if user_input:
    output = Conversation.run(input=user_input)
    st.session_state.past.append(user_input)
    st.session_state.generated.append(output)

    # Display the text response
    st.success(f"Chatbot: {output}")

    # choose language for response based on input language
    if lang_choice == "English":
        text_to_speech(output, language="en")
    else:
        text_to_speech(output, language="vn")

# Display the conversation history using an expander
with st.expander("Conversation History"):
    for i, (query, response) in enumerate(zip(st.session_state.past, st.session_state.generated)):
        st.info(f"You: {query}")
        st.success(f"Chatbot: {response}")
        if i < len(st.session_state.past) - 1:
            st.write("---")

