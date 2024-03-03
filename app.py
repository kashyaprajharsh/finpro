import re
import os
import json
import calendar
import streamlit as st
from streamlit_chat import message
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain,HypotheticalDocumentEmbedder
from langchain_pinecone import PineconeVectorStore
from langchain_core.messages import AIMessage, HumanMessage

from dotenv import load_dotenv
from langkit import llm_metrics
from langkit import response_hallucination # alternatively use 'light_metrics'
import whylogs as why
from whylogs.experimental.core.udf_schema import udf_schema




import streamlit as st
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
os.environ["GOOGLE_API_KEY"] = st.secrets['GOOGLE_API_KEY']
os.environ["PINECONE_API_KEY"] = st.secrets['PINECONE_API_KEY']


def initialize_session_state():
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    if 'generated' not in st.session_state:
        st.session_state['generated'] = ["Hello! Ask me anything about 🦉"]

    if 'past' not in st.session_state:
        st.session_state['past'] = ["Hey! 🐼"]

def conversation_chat(query, chain, history):
    result = chain.invoke({"question": query, "chat_history": history})
    history.append((query, result["answer"]))
    return result["answer"]

def display_last_dict(history):
    chat_dict_list = [{'prompt': prompt, 'response': response} for prompt, response in history]

    if chat_dict_list:
        return chat_dict_list[-1]
    else:
        return None 
def display_metric(prompt_and_response):
    if prompt_and_response:
        schema = llm_metrics.init()
        schema = udf_schema()
        response_hallucination.init(llm=st.session_state.llm, num_samples=1)
        profile = why.log(prompt_and_response, schema=schema).profile()
        profview = profile.view()
        df = profview.to_pandas()
        selected_rows = df[df.index.str.startswith(('response.toxicity', 'response.sentiment_nltk', 'response.relevance_to_prompt','response.hallucination', 'prompt.toxicity', 'prompt.jailbreak_similarity'))]
        selected_columns = selected_rows[['distribution/max']] 
        return selected_columns
    else:
        return None



def display_chat_history(chain):
    reply_container = st.container()
    container = st.container()

    with container:
        with st.form(key='my_form', clear_on_submit=True):
            user_input = st.text_input("Question:", placeholder="Please ask question.", key='input')
            submit_button = st.form_submit_button(label='Send')

        if submit_button and user_input:
            with st.spinner('Generating response...'):
                output = conversation_chat(user_input, chain, st.session_state['history'])

            st.session_state['past'].append(user_input)
            st.session_state['generated'].append(output)

    if st.session_state['generated']:
        with reply_container:
            for i in range(len(st.session_state['generated'])):
                message(st.session_state["past"][i], is_user=True, key=str(i) + '_user',avatar_style='identicon')
                message(st.session_state["generated"][i], key=str(i), avatar_style='bottts')



embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="retrieval_document")

def extract_year_month_from_metadata(metadata):
    years_months = []
    for entry in metadata:
        match = re.search(r'(\w{3})(\d{2})', entry["source"])
        if match:
            month_abbreviation = match.group(1)
            year_short = match.group(2)

            month_mapping = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }

            month_numeric = month_mapping.get(month_abbreviation.lower())

            if month_numeric:
                year = '20' + year_short
                years_months.append((year, month_numeric))

    return years_months

def extract_year_from_path(path):
    # Extracts the year from the path (assumes the year is present in the path)
    match = re.search(r'(\d{2,4})', path)
    if match:
        return match.group(1)
    else:
        print(f"No year found in path: {path}")
        return None

def folder_selector():
    st.title("Select the Company and the earning calls")
    # Load metadata from the JSON file
    with open("D:\\finpro_gemni\\metadata.json", "r") as file:
        metadata = json.load(file)

    # Get unique companies
    unique_companies = list(set([os.path.basename(os.path.dirname(entry["source"])) for entry in metadata]))
    unique_companies.sort()

    # Create a dropdown for selecting the company
    selected_company = st.selectbox("Select a Company:", unique_companies,key="company_selector")

    # Filter metadata based on the selected company
    company_metadata = [entry for entry in metadata if entry["source"].startswith(os.path.join("E:\\earning_reports_copilot\\Concalls", selected_company))]

    years_months = extract_year_month_from_metadata(company_metadata)
    if years_months:
        # Get unique years
        unique_years = list(set([year for year, _ in years_months]))
        unique_years.sort(reverse=True)

        # Create a dropdown for selecting the year
        selected_year = st.selectbox("Select a Year:", unique_years, key="year_selector")

        # Filter years_months based on the selected year
        selected_years_months = [(year, month) for year, month in years_months if year == selected_year]
        # st.write(selected_years_months)

        if selected_years_months:
            # Get unique months for the selected year
            unique_months = list(set([calendar.month_name[int(month)] for _, month in selected_years_months]))
            unique_months.sort(reverse=True)

           
            selected_month = st.selectbox("Select Month:", unique_months, key="month_selector")
            selected_paths = []
            for entry in company_metadata:
                # Check for month abbreviation (case-insensitive) AND presence of both .pdf and .PDF extensions
                if (
                    (selected_month[:3].lower() in entry["source"].lower()) or
                    (selected_month[:3].upper() in entry["source"].lower()) and
                    (entry["source"].endswith(".pdf") or entry["source"].endswith(".PDF"))
                ):
                    # Extract filename without the date part using regular expression (improved approach)
                    filename_without_date = re.findall(r".*_([^\.]+)\.", entry["source"])[0]
                    
                    # Extract the year from the path
                    path_year = extract_year_from_path(entry["source"])
                    # print(f"Path: {entry['source']}, Extracted Year: {path_year}")
                    # print(path_year)
                    # print(selected_year[2:])

                    if (
                        filename_without_date in entry["source"].split("\\")[-1] and
                        path_year == selected_year[2:]
                    ):  
                        selected_paths.append(entry["source"])

            # print(f"Selected Paths: {selected_paths}")
            return selected_paths

    return []




def get_vectorstore():
    ret =PineconeVectorStore(embedding=embeddings,index_name="gemnivector")
    return ret

def get_conversation_cahin(path):
    st.session_state.llm = ChatGoogleGenerativeAI(
    model="gemini-1.0-pro-latest",
    temperature=0,
    top_p= 0.8,
    top_k= 8,
    max_output_tokens=2048,
    safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        convert_system_message_to_human=True
    )

    prompt_template = """
#CONTEXT #\
You are a tool called Finpro Chatbot. \
As a financial expert and business analyst, your primary responsibility is to extract relevant information from a specific knowledge base provided to you through the context.\
This involves analyzing financial data, market trends, and other relevant information to provide valuable insights and recommendations to your clients.\
You must have a strong understanding of the financial industry, including investment strategies, financial reporting standards, and regulatory requirements.\
Additionally, you should possess excellent analytical and problem-solving skills, as well as effective communication and presentation abilities to convey your findings to clients in a clear and concise manner.
#OBJECTIVE #\
* Answer questions based only on the given context.
* Question which is related to context provide answer for them.
* If the user requests sets of questions, provide them in bulleted form, labeled Q1, Q2, etc and always ensure that questions you give are related to knowledge base provided.
* If the user request for a summary give a detail summary in a professional tone.\
* Answer should always in english.
#STYLE #\
To truly succeed in finance, it's crucial to adopt the writing style of proven experts, such as financial analysts or business analysts. Their expertise and experience have been honed over time and can serve as an excellent guide for you to achieve the same level of success. So, make a confident decision to follow their writing style today.
#TONE #\
Professional
#AUDIENCE #\
Those who wish to gain insights about the Company by listening to their earnings calls.
#RESPONSE #\
Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
Context:\n {context}?\n
Question: \n{question}\n

Answer:

"""


    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"] )
    chain_type_kwargs = {"prompt": PROMPT}

    ret =get_vectorstore()
    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True, output_key='answer')
    
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=st.session_state.llm,
        chain_type='stuff',
        retriever = ret.as_retriever(search_type='similarity',search_kwargs={"k": 10,'filter': {"source": path[0]}}),
        memory=memory,
        combine_docs_chain_kwargs =chain_type_kwargs,
        return_source_documents=True
    )
    return conversation_chain




def get_response(user_input):
    response = st.session_state.conversation.invoke({'question': user_input})
    st.write(response)
    st.session_state.chat_history = response['chat_history']
    return response['answer']




def sampleQueries():
    # sample queries
    sample_queries = ["Give me bulleted list of 10 questions to understand financials of this company.",
                      "Give me a bulleted list of questions I should ask to understand this company better."]
    return sample_queries

def get_user_query():
    '''
    Get user query: user can choose from sample queries or can write their own.
    After query submit button is pressed, identify the query.
    '''
    user_query =""
    # Create the selectbox for sample queries
    sample_queries = sampleQueries()
    
    #with col1:
    selected_query = st.selectbox("Choose a sample query", sample_queries, 
                                  index=None,
                                  placeholder="Please Input your Query")
    # Create the text input for user-written query
    given_query = st.text_input("Or write your own query")
    submit=st.form_submit_button('Submit')

    # Create the submit button
    if submit:
        # Check if the user has written their own query
        if given_query:
            user_query = given_query
        elif selected_query:
            user_query = selected_query
        
        st.write("Looking into the report .... ")
    return(user_query)



def main():
    st.set_page_config(page_title="Finpro.ai - FinGainInsights",
                    page_icon=":moneybag:")
    initialize_session_state()
    load_dotenv()
    st.title("Finpro - EarningsWhisperer 💹")
   


    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(content="Hello, I am a Finpro - NiftyChat Navigator. How can I help you?"),
        ]

    with st.sidebar:
        st.header("")
        st.session_state.path = folder_selector()
    st.session_state.conversation= get_conversation_cahin(st.session_state.path)

    # Create the chain object
    chain = get_conversation_cahin(st.session_state.path)
    display_chat_history(chain)
    prompt_and_response=display_last_dict(st.session_state.history)
    st.write(display_metric(prompt_and_response))

    




if __name__ == "__main__":
    main()



    
