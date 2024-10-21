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
page = st.sidebar.radio("Navigation", ["Chat", "About the Bot", "Methodology", "Use Cases", "About Me!"])

# Function to load content from the specified websites
def load_website_content(urls):
    content = []
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            page_content = [p.get_text() for p in soup.find_all('p')]
            content.append(' '.join(page_content))
        except Exception as e:
            st.error(f"Error loading website content from {url}: {str(e)}")
    return ' '.join(content)

# List of URLs to scrape
urls = [
    "https://stackedhomes.com/editorial/october-2024-bto-launch-review-ultimate-guide-to-choosing-the-best-unit/#gs.g7fu57",
    "https://blog.seedly.sg/october-2024-bto/",
    "https://www.mynicehome.gov.sg/sales-launches/october-2024-sales-launch/",
    "https://www.straitstimes.com/singapore/housing/prime-and-plus-hdb-flats-in-oct-bto-launch-to-come-with-6-to-9-per-cent-subsidy-clawback-clause"
]

st.session_state.content_data = load_website_content(urls)

bto_keywords = ["BTO", "Build-To-Order", "application", "process", "flat", "ballot", "housing"]

def classify_topic(user_input, website_content):
    user_input_lower = user_input.lower()
    if any(keyword in user_input_lower for keyword in bto_keywords):
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
        Where necessary, use tables to clearly indicate the information.

        Here's some context information from the article:
        {website_content}

        Previous conversation:
        {' '.join([msg.content for msg in chat_history])}

        Respond to the following user query about BTO or Singapore housing:
        {sanitized_input}

        Your response should follow this structure:
        Direct answer to the query (3-4 sentences)
        Additional relevant information (4-5 sentences, over 2 paragraphs. use bullet points if it's easier to understand)
        Add table if necessary
        {additional_info_message}
        """
    else:
        prompt = f"""
        You are an AI assistant specialized in Singapore's BTO (Build-To-Order) launches.
        The user has asked a question that is not related to BTO or Singapore housing.

        User query: {sanitized_input}

        Respond with the following structure:
        Polite acknowledgment that the query is not about BTO or Singapore housing
        Brief explanation of what BTO is
        Suggestion for a BTO-related question the user could ask instead
        {additional_info_message}
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


elif page == "About the Bot":
    st.title("About the Bot")
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
    - Automated suggestion generation for relevant user queries
    """)

elif page == "Methodology":
    st.title("Methodology")
    st.write(""" 
    The methodology for building this prototype consists of several key components:

    1. **Data Collection**: Using web scraping techniques to gather data from credible websites related to the October 2024 BTO launch.
    
    2. **Natural Language Processing**: Employing language models to understand user queries and provide meaningful responses.
    
    3. **User Interaction**: Building a user-friendly interface to facilitate conversation and information retrieval.

    4. **Evaluation and Iteration**: Continually evaluating the assistant's performance and making iterative improvements based on user feedback.
    """)
    st.image("flowchart.png")

elif page == "Use Cases":
    st.title("Use Cases")
    st.write("""
    This chatbot prototype focuses on providing users with information about Singapore's Build-To-Order (BTO) housing schemes, specifically the upcoming October 2024 launch. Here are two clear use cases for this language model (LLM) chatbot:

    **Use Case 1: Information Retrieval and User Guidance**
    Objective: To provide accurate and timely information about the BTO application process, financing options, and other related queries.
    Scenario: A user interested in applying for a BTO flat can interact with the chatbot to learn about:
    The steps involved in the application process.
    Eligibility criteria for different types of flats.
    Financial options and subsidies available for BTO applicants.
    Functionality: The chatbot can deliver concise answers, reference credible sources, and even generate follow-up questions based on the user's input. It can also clarify complex terms and procedures, guiding users through their queries effectively.

    **Use Case 2: User Engagement and Proactive Suggestions**
    Objective: To enhance user experience by offering relevant suggestions and encouraging further inquiries about BTO-related topics.
    Scenario: While using the chatbot, a user might express interest in a specific aspect of BTO flats, such as the location of new launches or financing options. The chatbot can:
    Suggest related questions to explore, keeping the conversation dynamic.
    Generate new suggestions based on the user's previous interactions and interests.
    Functionality: This engagement strategy helps maintain user interest, encourages deeper exploration of the topic, and makes the chatbot a valuable tool for potential BTO applicants, providing a more interactive experience.
    Overall, these use cases demonstrate the chatbot's ability to serve as both an informational resource and an engaging conversational partner, tailored to the specific needs of users interested in BTO housing in Singapore.
    """
    )

# Profile Page
elif page == "About Me!":
    st.title("Malcolm Ang's Profile")
    st.image("mario.jpg", caption="Malcolm (Zacchaeus) Ang", width=200, use_column_width=False)

    # Professional Overview
    st.subheader("Professional Overview")
    st.write("""
    Hello, I'm Malcolm (Zacchaeus) Ang, a recent graduate with a Master of Science in Applied Analytics from Columbia University, and I bring over a decade of experience as a Logistics Officer in the Singapore Armed Forces. My journey in logistics and analytics has been both enriching and transformative, as I've had the opportunity to work on complex supply chain challenges in various capacities.
    """)

    # Professional Experience
    st.subheader("Professional Experience")
    st.write("""
    ### Singapore Armed Forces
    As a Logistics Officer for over **10 years**, I have developed expertise in:
    - **Transportation Management**: Coordinating and optimizing the movement of goods and resources.
    - **Supply Chain Logistics**: Streamlining processes to enhance efficiency and reduce costs.
    - **Finance Operations**: Overseeing budgeting and financial planning for logistics initiatives.

    My ability to work collaboratively with diverse teams has allowed me to contribute to mission-critical operations successfully.
    """)

    # Skills and Certifications
    st.subheader("Skills and Certifications")
    st.write("""
    I have developed a wide range of skills throughout my career, including:
    - **Data Analytics**: Proficient in using tools like Python, R, and Excel for data analysis.
    - **Project Management**: Experienced in managing logistics projects from inception to completion.
    - **Leadership**: Proven track record in leading teams and fostering collaborative environments.

    ### Certifications
    - **Data Visualization for Data Analysis and Analytics**
    - **Excel Supply Chain Analysis: Solving Transportation Problems**

    These skills and certifications enhance my ability to deliver results and drive innovation in logistics operations.
    """)

    # Passion for Innovation
    st.subheader("Passion for Innovation")
    st.write("""
    I am genuinely passionate about leveraging data analytics to drive operational efficiency and strategic decision-making. In today's fast-paced world, effective logistics is crucial not only for military success but also for businesses seeking competitive advantages. I aim to bridge the gap between logistics operations and analytical insights, transforming data into actionable strategies that enhance performance.
    """)

    # Looking Forward
    st.subheader("Looking Forward")
    st.write("""
    As I embark on the next chapter of my career, I am eager to apply my skills in a dynamic organization that values innovation and growth. I am excited about opportunities to collaborate on projects that challenge the status quo and drive significant impact.

    If you are interested in connecting or discussing potential collaborations, feel free to reach out through my contact information below!
    """)

    # Contact Information
    st.subheader("Contact Information")
    st.write("""
    - **LinkedIn**: [linkedin.com/in/malcolmzacc](https://www.linkedin.com/in/malcolmzacc)
    """)

    # Add a personal touch
    st.write("""
    ### Personal Interests
    In my spare time, I enjoy watching Broadway shows. The energy of live performances and the creativity involved in storytelling through music and dance inspire me. I believe that the arts can teach us valuable lessons about collaboration and innovation, principles that I strive to bring into my professional life.
    """)

# git add app.py; git commit -m "remove picture"; git push origin main