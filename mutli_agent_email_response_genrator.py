from typing import Annotated
from typing_extensions import TypedDict 
from langgraph.graph import StateGraph, START, END 
from langgraph.graph.message import add_messages 
import getpass
import os
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import PromptTemplate 
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.schema import Document

from langchain.schema import Document 
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict
from typing import List 

import getpass
import os
from dotenv import load_dotenv
from traceback import format_exc


# Load environment variables from the .env file
# load_dotenv()

# if "GROQ_API_KEY" not in os.environ:
#     os.environ["GROQ_API_KEY"] =  os.getenv("GROQ_API_KEY")

# if "TAVILY_API_KEY" not in os.environ:
#     os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        initial_email: email
        email_category: email category
        draft_email: LLM generation
        final_email: LLM generation
        research_info: list of documents
        info_needed: whether to add search info
        num_steps: number of steps
    """
    initial_email : str 
    email_category : str 
    draft_email : str 
    final_email : str 
    final_email : str 
    research_info : List[str]
    info_needed : bool 
    num_steps : int 
    draft_email_feedback : dict 

class EmailReplyGenerator:

    def __init__(self):
        self.web_search_tool = TavilySearchResults(k=1)

        self.GROQ_LLM = ChatGroq(model="llama3-70b-8192",
            temperature=0.4,
            max_tokens=None,
            timeout=None,
            max_retries=2)

    def write_markdown_file(self,content, filename):
    
        """Writes the given content as a markdown file to the local directory.

        Args:
            content: The string content to write to the file.
            filename: The filename to save the file as.
        """
        with open(f"{filename}.md", "w") as f:
            f.write(content)


    def categorize_email(self, state):

        """
        This agent is geting email body as an input and classify its category in the given options. and return single word response
        """

        try:
            print("---CATEGORIZING INITIAL EMAIL---")
            initial_email = state['initial_email']
            num_steps = int(state['num_steps'])
            num_steps += 1

            prompt = """
                You are a Email Categorizer Agent You are a master at understanding what a customer wants when they write an email and are able to categorize it in a useful way
                    Conduct a comprehensive analysis of the email provided and categorize into one of the following categories:
                        price_equiry - used when someone is asking for information about pricing \
                        customer_complaint - used when someone is complaining about something \
                        product_enquiry - used when someone is asking for information about a product feature, benefit or service but not about pricing \\
                        customer_feedback - used when someone is giving feedback about a product \
                        off_topic when it doesnt relate to any other category \


                            Output a single cetgory only from the types ('price_equiry', 'customer_complaint', 'product_enquiry', 'customer_feedback', 'off_topic') \
                            eg:
                            'price_enquiry' \

                    EMAIL CONTENT:\n\n {initial_email} \n\n
                    """
            prmpt_template = PromptTemplate(
                template = prompt,
                input_variables=["initial_email"]
            )
            email_category_generator = prmpt_template | self.GROQ_LLM | StrOutputParser()
            result = email_category_generator.invoke({"initial_email": initial_email})
            self.write_markdown_file(result, "email_category")

            return {"email_category": result, "num_steps":num_steps} 
        
        except Exception as e:
            print(f"Error : {format_exc()}")
            return {"email_category": '', "num_steps":num_steps} 

    def research_router(self,state):
        """
        Do research for generating proper
        """
        try:
            print("---ROUTE TO RESEARCH---")
            initial_email = state["initial_email"]
            email_category = state["email_category"]
            
            prompt  = """
            You are an expert at reading the initial email and routing web search or directly to a draft email. \n

                Use the following criteria to decide how to route the email: \n\n

                If the initial email only requires a simple response
                Just choose 'draft_email'  for questions you can easily answer, prompt engineering, and adversarial attacks.
                If the email is just saying thank you etc then choose 'draft_email'

                You do not need to be stringent with the keywords in the question related to these topics. Otherwise, use research-info.
                Give a binary choice 'research_info' or 'draft_email' based on the question. Return the a JSON with a single key 'router_decision' and
                no premable or explaination. use both the initial email and the email category to make your decision
                Email to route INITIAL_EMAIL : {initial_email} \n
                EMAIL_CATEGORY: {email_category} \n
                """ 
            research_router_prompt = PromptTemplate(template=prompt,
                    imput_variables = ["initial_email, email_category"]
                    )
            research_router_engine = research_router_prompt | self.GROQ_LLM | JsonOutputParser()
            router = research_router_engine.invoke({"initial_email": initial_email, "email_category":email_category})
            
            print(router['router_decision'])
            if router['router_decision'] == 'research_info':
                print("---ROUTE EMAIL TO RESEARCH INFO---")
                return "research_info"
            elif router['router_decision'] == 'draft_email':
                print("---ROUTE EMAIL TO DRAFT EMAIL---")
                return "draft_email"
            
        except Exception as e:
            print(f"Errror : {e}")
            return "draft_email"
    

    def research_info_search(self, state):
        """
        Get data from internet
        """
        try:
            
            print("---RESEARCH INFO SEARCHING---")
            initial_email = state["initial_email"]
            email_category = state["email_category"]
            num_steps = state['num_steps']
            num_steps += 1

            prompt = """
            You are a master at working out the best keywords to search for in a web search to get the best info for the customer.

            given the INITIAL_EMAIL and EMAIL_CATEGORY. Work out the best keywords that will find the best
            info for helping to write the final email.

            Return a JSON with a single key 'keywords' with no more than 3 keywords and no premable or explaination.
                INITIAL_EMAIL: {initial_email} \n
                EMAIL_CATEGORY: {email_category} \n
            """ 
            search_keyword_prompt = PromptTemplate(
                template=prompt,
                input_variables=["initial_email","email_category"]
            )
            search_keyword_chain = search_keyword_prompt | self.GROQ_LLM | JsonOutputParser()
            response = search_keyword_chain.invoke({"initial_email": initial_email, "email_category":email_category})
            keywords = response['keywords']
            full_searches = []
            for keyword in keywords[:1]:
                print(keyword)
                temp_docs = self.web_search_tool.invoke({"query": keyword})
                web_results = "\n".join([d["content"] for d in temp_docs])
                web_results = Document(page_content=web_results)
            if full_searches is not None:
                full_searches.append(web_results)
            else:
                full_searches = [web_results]   
            return {"research_info": full_searches, "num_steps":num_steps}
        
        except Exception as e:
            print(f"Error : {e}")
            {"research_info": [], "num_steps":num_steps}

    def draft_email_writer(self, state):
        """
        Write draft email
        """
        try:
            print("---DRAFT EMAIL WRITER---")
            ## Get the state
            initial_email = state["initial_email"]
            email_category = state["email_category"]
            research_info = state["research_info"]
            num_steps = state['num_steps']
            num_steps += 1

            prompt = """
                You are the Email Writer Agent take the INITIAL_EMAIL below  from a human that has emailed our company email address, the email_category \
                    that the categorizer agent gave it and the research from the research agent and \
                    write a helpful email in a thoughtful and friendly way.

                    If the customer email is 'off_topic' then ask them questions to get more information.
                    If the customer email is 'customer_complaint' then try to assure we value them and that we are addressing their issues.
                    If the customer email is 'customer_feedback' then try to assure we value them and that we are addressing their issues.
                    If the customer email is 'product_enquiry' then try to give them the info the researcher provided in a succinct and friendly way.
                    If the customer email is 'price_equiry' then try to give the pricing info they requested.

                    You never make up information that hasn't been provided by the research_info or in the initial_email.
                    Always sign off the emails in appropriate manner and from Uxair the Resident Manager.

                    Return the email a JSON with a single key 'email_draft' and no premable or explaination.
                    
                    INITIAL_EMAIL: {initial_email} \n
                    EMAIL_CATEGORY: {email_category} \n
                    RESEARCH_INFO: {research_info} \n
                """
            draft_writer_prompt = PromptTemplate(template=prompt, input_variables=["initial_email","email_category","research_info"])
            draft_writer_chain = draft_writer_prompt | self.GROQ_LLM | JsonOutputParser()
            draft_email = draft_writer_chain.invoke({"initial_email": initial_email, "email_category":email_category,"research_info":research_info})
            return  {"draft_email": draft_email, "num_steps":num_steps}
        except Exception as e:
            print(f"Error : {e}")
            return  {"draft_email": "", "num_steps":num_steps} 
    
    def route_to_rewrite(self, state):
        """
        Email confirmation.
        """
        try:
            print("---ROUTE TO REWRITE---")
            initial_email = state["initial_email"]
            email_category = state["email_category"]
            draft_email = state["draft_email"]

            prompt = """
                You are an expert at evaluating the emails that are draft emails for the customer and deciding if they
            need to be rewritten to be better. \n

            Use the following criteria to decide if the DRAFT_EMAIL needs to be rewritten: \n\n

            If the INITIAL_EMAIL only requires a simple response which the DRAFT_EMAIL contains then it doesn't need to be rewritten.
            If the DRAFT_EMAIL addresses all the concerns of the INITIAL_EMAIL then it doesn't need to be rewritten.
            If the DRAFT_EMAIL is missing information that the INITIAL_EMAIL requires then it needs to be rewritten.

            Give a binary choice 'rewrite' (for needs to be rewritten) or 'no_rewrite' (for doesn't need to be rewritten) based on the DRAFT_EMAIL and the criteria.
            Return the a JSON with a single key 'router_decision' and no premable or explaination. \n

            INITIAL_EMAIL: {initial_email} \n
            EMAIL_CATEGORY: {email_category} \n
            DRAFT_EMAIL: {draft_email} \n
            """ 
            rewrite_router_prompt = PromptTemplate(template=prompt, input_variables=["initial_email","email_category","draft_email"])
            rewrite_router = rewrite_router_prompt | self.GROQ_LLM | JsonOutputParser()
            router = rewrite_router.invoke({"initial_email": initial_email, "email_category":email_category, "draft_email":draft_email})
            print(router)
            print(router['router_decision'])
            if router['router_decision'] == 'rewrite':
                print("---ROUTE TO ANALYSIS - REWRITE---")
                return "rewrite"
            elif router['router_decision'] == 'no_rewrite':
                print("---ROUTE EMAIL TO FINAL EMAIL---")
                return "no_rewrite"
        
        except Exception as e:
            print(f"Error : {e}")
            return None 
    
    def analyze_draft_email(self, state):
        
        print("---DRAFT EMAIL ANALYZER---")
        ## Get the state
        initial_email = state["initial_email"]
        email_category = state["email_category"]
        draft_email = state["draft_email"]
        print(f"draft_email --> {draft_email}")
        research_info = state["research_info"]
        num_steps = state['num_steps']
        num_steps += 1
        
        prompt = """ 
        You are the Quality Control Agent read the INITIAL_EMAIL below  from a human that has emailed \
            our company email address, the email_category that the categorizer agent gave it and the \
            research from the research agent and write an analysis of how the email.

            Check if the DRAFT_EMAIL addresses the customer's issued based on the email category and the \
            content of the initial email.\n

            Give feedback of how the email can be improved and what specific things can be added or change\
            to make the email more effective at addressing the customer's issues.

            You never make up or add information that hasn't been provided by the research_info or in the initial_email.

            Return the analysis a JSON with a single key 'draft_analysis' and no premable or explaination.    
            
            INITIAL_EMAIL: {initial_email} \n\n
            EMAIL_CATEGORY: {email_category} \n\n
            RESEARCH_INFO: {research_info} \n\n
            DRAFT_EMAIL: {draft_email} \n\n
        """
        draft_analysis_prompt = PromptTemplate(template=prompt, input_variables=["initial_email","email_category","research_info"])
        draft_analysis_chain = draft_analysis_prompt | self.GROQ_LLM | JsonOutputParser()
        draft_email_feedback = draft_analysis_chain.invoke({"initial_email": initial_email,
                                    "email_category":email_category,
                                    "research_info":research_info,
                                    "draft_email": draft_email})
        # self.write_markdown_file(str(draft_email_feedback), "draft_email_feedback")

        return {"draft_email_feedback": draft_email_feedback, "num_steps":num_steps}


    def rewrite_email(self, state):

        try:
            print("---ReWRITE EMAIL ---")
            ## Get the state
            initial_email = state.get("initial_email")
            email_category = state.get("email_category")
            draft_email = state.get("draft_email")
            research_info = state.get("research_info")
            draft_email_feedback = state.get("draft_email_feedback")
            num_steps = state.get('num_steps')
            num_steps += 1
            prompt = """ 
            
                You are the Final Email Agent read the email analysis below from the QC Agent \
                and use it to rewrite and improve the draft_email to create a final email.


                You never make up or add information that hasn't been provided by the research_info or in the initial_email.

                Return the final email as JSON with a single key 'final_email' which is a string and no premable or explaination.  
                EMAIL_CATEGORY: {email_category} \n\n
                RESEARCH_INFO: {research_info} \n\n
                DRAFT_EMAIL: {draft_email} \n\n
                DRAFT_EMAIL_FEEDBACK: {email_analysis} \n\n 
            """
            
            rewrite_email_prompt = PromptTemplate(template=prompt, input_variables=["initial_email", "email_category", "research_info",
                        "email_analysis", "draft_email"])
            rewrite_chain = rewrite_email_prompt | self.GROQ_LLM | JsonOutputParser()
            final_email = rewrite_chain.invoke({"initial_email": initial_email,
                                    "email_category":email_category,
                                    "research_info":research_info,
                                    "draft_email": draft_email,
                                    "email_analysis":draft_email_feedback})
            # write_markdown_file(str(final_email), "final_email")

            return  {"final_email": final_email['final_email'], "num_steps":num_steps}
        
        except Exception as e:
            print(f"Error : {e}")
            return {"final_email": '', "num_steps":num_steps}

    def no_rewrite(self, state):
        print("---NO REWRITE EMAIL ---")
        ## Get the state
        draft_email = state.get("draft_email", None)
        num_steps = state.get('num_steps')
        num_steps += 1

        # write_markdown_file(str(draft_email), "final_email")
        return {"final_email": draft_email, "num_steps":num_steps}



    def state_printer(self, state):
        """print the state"""
        print("---STATE PRINTER---")
        print(f"Initial Email: {state.get('initial_email')} \n" )
        print(f"Email Category: {state.get('email_category')} \n")
        print(f"Draft Email: {state.get('draft_email')} \n" )
        print(f"Final Email: {state.get('final_email')} \n" )
        print(f"Research Info: {state.get('research_info')} \n")
        print(f"Info Needed: {state.get('info_needed')} \n")
        print(f"Num Steps: {state.get('num_steps')} \n")
        return 

    def generate_final_response(self, EMAIL):

        workflow = StateGraph(GraphState)
        workflow.add_node("categorize_email", self.categorize_email)
        workflow.add_node("research_info_search", self.research_info_search)
        workflow.add_node("state_printer", self.state_printer)
        workflow.add_node("draft_email_writer", self.draft_email_writer)

        workflow.add_node("analyze_draft_email", self.analyze_draft_email)
        workflow.add_node("rewrite_email", self.rewrite_email)
        workflow.add_node("no_rewrite", self.no_rewrite)
        workflow.set_entry_point("categorize_email")
        workflow.add_conditional_edges(
            "categorize_email",
            self.research_router,
            {
                "research_info" : "research_info_search",
                "draft_email" : "draft_email_writer"
            },
        )
        workflow.add_edge("research_info_search", "draft_email_writer")
        workflow.add_conditional_edges(
            "draft_email_writer",
            self.route_to_rewrite,
            {
                "rewrite" : "analyze_draft_email",
                "no_rewrite" : "no_rewrite"
            },
        )
        workflow.add_edge("analyze_draft_email", "rewrite_email")
        workflow.add_edge("no_rewrite", "state_printer")
        workflow.add_edge("rewrite_email", "state_printer")
        workflow.add_edge("state_printer", END)
        app = workflow.compile()

        inputs = {"initial_email": EMAIL,"research_info": None, "num_steps":0}

        output = app.invoke(inputs)
        for index, value in output['final_email'].items():
            return value

# if __name__ == "__main__":
   

    # print(output['final_email'][])
# email = """
# HI there, \n
# I am emailing to say that the resort weather was way to cloudy and overcast. \n
# I wanted to write a song called 'Here comes the sun but it never came'

# What should be the weather in Arizona in April?

# I really hope you fix this next time.

# Thanks,
# Geor
# """
# obj = EmailReplyGenerator()
# email_response = obj.generate_final_response(email)
# print(email_response)
