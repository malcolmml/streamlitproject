import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import requests
from bs4 import BeautifulSoup
import re
from utility import check_password

load_dotenv()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "suggestions" not in st.session_state:
    st.session_state.suggestions = [
        "Tell me about the October 2024 BTO launch",
        "What are the financing options for BTO?",
        "How does the BTO application process work?",
    ]

# Streamlit Page Configuration
st.set_page_config(page_title="Ask Me Anything about October BTO Bot", page_icon="🤔")

# Do not continue if check_password is not True.
if not check_password():
    st.stop()

# Add the disclaimer using st.expander
with st.expander("IMPORTANT NOTICE"):
    st.write("""
    **IMPORTANT NOTICE:** This web application is a prototype developed for educational purposes only.
    The information provided here is **NOT** intended for real-world usage and should not be relied upon for making any decisions,
    especially those related to financial, legal, or healthcare matters.

    Furthermore, please be aware that the LLM may generate inaccurate or incorrect information.
    You assume full responsibility for how you use any generated output.

    **Always consult with qualified professionals** for accurate and personalized advice.
    """)

# Create a navigation menu with pages
page = st.sidebar.selectbox("Navigation", ["Chat", "About Us", "Methodology"])

# Function to load content from the specified website
def load_website_content():
    url = "https://stackedhomes.com/editorial/october-2024-bto-launch-review-ultimate-guide-to-choosing-the-best-unit/#gs.g7fu57"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content = [p.get_text() for p in soup.find_all('p')]
        return ' '.join(content)
    except Exception as e:
        st.error(f"Error loading website content: {str(e)}")
        return None

st.session_state.content_data = load_website_content()

def classify_topic(user_input, website_content):
    user_input_lower = user_input.lower()
    website_content_lower = website_content.lower()

    if user_input_lower in website_content_lower:
        return "BTO_RELATED"
    for sentence in website_content.split('.'):
        if user_input_lower in sentence.lower():
            return "BTO_RELATED"

    prompt = f"""
    Classify the following user input as either 'BTO_RELATED' or 'OFF_TOPIC':
    
    User Input: {user_input}
    
    If the input is related to Singapore's BTO (Build-To-Order) launches, housing options, financing, locations, or any aspect of Singapore's public housing system, classify it as 'BTO_RELATED'.
    Otherwise, classify it as 'OFF_TOPIC'."""
    
    classification = get_completion(prompt).strip()
    return classification

# Access the OpenAI API key
openai_api_key = st.secrets["general"]["OPENAI_API_KEY"]


def sanitize_input(user_input):
    sanitized = re.sub(r'ignore .* prompt', '', user_input, flags=re.IGNORECASE)
    sanitized = re.sub(r'forget .* instruction', '', sanitized, flags=re.IGNORECASE)
    return sanitized

def get_completion(prompt):
    llm = ChatOpenAI(openai_api_key=openai_api_key)
    response = llm.invoke(prompt)
    return response.content

def get_response(user_input, chat_history, website_content):
    sanitized_input = sanitize_input(user_input)
    topic_classification = classify_topic(sanitized_input, website_content)
    
    # This is the additional message with the link
    additional_info_message = """
    For more detailed information on BTO launches and related topics, please visit the official HDB website: [HDB Official Website](https://homes.hdb.gov.sg/home/landing).
    """
    
    if topic_classification == 'BTO_RELATED':
        prompt = f"""
        You are an AI assistant specialized in Singapore's BTO (Build-To-Order) launches, particularly the October 2024 launch.
        Your role is to provide accurate and helpful information about BTO housing options, application processes, financing, and related topics.

        Here's some context information from the article:
        {website_content}

        Previous conversation:
        {' '.join([msg.content for msg in chat_history])}

        Respond to the following user query about BTO or Singapore housing:
        {sanitized_input}

        Your response should follow this structure:
        1. Direct answer to the query (3-4 sentences)
        2. Additional relevant information (4-5 sentences, over 2 paragraphs. use bullet points if it's easier to understand)
        3. {additional_info_message}
        """
    else:
        prompt = f"""
        You are an AI assistant specialized in Singapore's BTO (Build-To-Order) launches.
        The user has asked a question that is not related to BTO or Singapore housing.

        User query: {sanitized_input}

        Respond with the following structure:
        1. Polite acknowledgment that the query is not about BTO or Singapore housing
        2. Brief explanation of what BTO is
        3. Suggestion for a BTO-related question the user could ask instead
        4. {additional_info_message}
        """
    
    return get_completion(prompt)


def generate_new_suggestions(current_topic):
    prompt = f"""
    <Instruction>
    Based on the current topic of conversation: "{current_topic}"
    Generate 3 relevant follow-up questions or prompts that a user might want to ask next.
    </Instruction>

    Create 3 concise and diverse questions or prompts related to the topic above.
    These should cover different aspects of the topic and encourage further exploration.

    Remember, you are generating questions about BTO launches in Singapore, specifically the October 2024 launch.
    Format your response as a Python list of strings.
    """

    response = get_completion(prompt)
    try:
        return eval(response)
    except:
        return [
            "What are the upcoming BTO launches in Singapore?",
            "How does the balloting process work for BTO flats?",
            "What are the eligibility criteria for applying for a BTO flat in Singapore?"
        ]

# Page Logic

if page == "Chat":
    st.title("Ask Me Anything About October BTO Bot")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message("Human" if isinstance(message, HumanMessage) else "AI"):
            st.markdown(message.content)

    # Display clickable suggestions
    st.write("Suggested questions:")
    clicked_suggestion = None
    for suggestion in st.session_state.suggestions:
        if st.button(suggestion):
            clicked_suggestion = suggestion  # Store the clicked suggestion

    # Process either the clicked suggestion or user input from chat box
    if clicked_suggestion:
        user_input = clicked_suggestion
    else:
        user_input = st.chat_input("Your message")

    if user_input:
        sanitized_input = sanitize_input(user_input)
        
        st.session_state.chat_history.append(HumanMessage(sanitized_input))

        with st.chat_message("Human"):
            st.markdown(sanitized_input)

        with st.chat_message("AI"):
            ai_response = get_response(sanitized_input, st.session_state.chat_history, st.session_state.content_data)
            st.markdown(ai_response)
        
        st.session_state.chat_history.append(AIMessage(ai_response))

        st.session_state.suggestions = generate_new_suggestions(sanitized_input)

        st.rerun()

elif page == "About Us":
    st.title("About Us")
    st.write("""
    ### Project Scope:
    This project is a conversational assistant prototype that focuses on providing users with insights and information about Singapore's Build-To-Order (BTO) housing schemes, particularly the October 2024 launch.

    ### Objectives:
    - Provide up-to-date information on BTO housing
    - Offer assistance regarding financing options, application processes, and other BTO-related queries
    - Enable interactive conversations with users to guide them through the BTO process

    ### Data Sources:
    The primary data source is publicly available information from credible sources such as:
    - Stacked Homes Editorial on BTO Launches
    - Official government websites

    ### Features:
    - Intelligent chatbot interface
    - Automated suggestion generation for follow-up questions
    - Classification of user queries as BTO-related or not
    """)

elif page == "Methodology":
    st.title("Methodology")
    st.write("""
    ### Data Flow and Implementation:
    The application leverages multiple technologies and data sources to process user queries. The key components include:
    
    - **Chat Interface**: Built with Streamlit for easy interaction.
    - **Natural Language Processing (NLP)**: Powered by an LLM via LangChain OpenAI for query understanding and generation of responses.
    - **Content Scraping**: Retrieves up-to-date content from trusted websites to answer BTO-related questions.

    ### Flowchart:
    The following is an illustration of the workflow for the two primary use cases of the application: 
    1. User asks a general query
    2. User asks for BTO-related information
    """)
    
    st.image("flowchart.png")  # Replace with the path to your flowchart image
