# ---------- IMPORT LIBRARIES ---------- #
from kafka.consumer import KafkaConsumer
import dotenv
import os
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import boto3
import psycopg2


# ---------- IMPLEMENT NECESSARY CONFIGURATIONS ---------- #
dotenv.load_dotenv()

DB_URI     = os.environ.get('DB_URI') 
TOPIC      = os.environ.get('KAFKA_TOPIC')
IP_ADDRESS = os.environ.get('IP_ADDRESS')

sns = boto3.client("sns", region_name="us-east-1", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))
arn = os.environ.get("SNS_ARN")

conn = psycopg2.connect(DB_URI)

class State(BaseModel):
    logs: str
    logs_status: str
    logs_summary: str

def tool_router(state: State):
    return state.logs_status

llm = ChatOpenAI(model="gpt-4", api_key=os.environ.get("OPENAI_API_KEY"))

# ---------- SETUP KAFKA CONSUMER ---------- #
def setup_consumer(IP_ADDRESS):
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=[f'{IP_ADDRESS}:9092'],
        group_id=f"{TOPIC}-group",
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: x.decode('utf-8')
    )


# ---------- RUN AGENT TO EVALUATE LOGS ---------- #
def evaluate_logs(state: State):
    system_prompt = """ 
        Your task is to evaluate the provided logs and determine if they are good or bad.
        A log is considered "GOOD" if it indicates normal operation without errors or issues.
        A log is considered "BAD" if it contains errors, warnings, or any indication of issues that need attention.
        Respond with either GOOD or BAD with no additional text or anything else.
    """
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a log evaluation agent. {system_prompt}"),
        ("human", "{logs}")
    ])

    chain = prompt | llm

    response = chain.invoke(
        {"logs": state.logs},
    )

    result = response.content.strip().upper()
    state.logs_status = result
    return state


# ---------- SEND NOTIFICATION IF LOGS ARE BAD ---------- #
def send_notification(state: State):
    sns.publish(
        TopicArn=arn,
        Message=f"Bad logs detected:\n{state.logs}",
        Subject="LogSentinel Alert: Bad Logs Detected"
    )

    return state


# ---------- RUN AGENT TO SUMMARIZE LOGS ---------- #
def process_logs(state: State):
    system_prompt = """ 
        Your task is to process the provided logs and give an overall summary of the logs.
        This summary should include key events, errors, or any significant information that can help in understanding the logs.
        Respond with a concise summary of the logs.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a log processing/summarizing agent. {system_prompt}"),
        ("human", "{logs}")
    ])

    chain = prompt | llm

    response = chain.invoke(
        {"logs": state.logs},
    )

    result = response.content.strip()
    state.logs_summary = result
    return state


# ---------- SAVE STATUS OF LOGS TO DB ---------- #
def save_to_database(state: State):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs_table (log_entry, status, summary) VALUES (%s, %s, %s)",
        (state.logs, state.logs_status, state.logs_summary)
    )
    conn.commit()
    cursor.close()
    return state


# ---------- DEFINE LANGGRAPH GRAPH ---------- #
def define_langgraph_workflow():
    builder = StateGraph(State)
    builder.add_node("evaluate_logs",     evaluate_logs)
    builder.add_node("process_logs",      process_logs)
    builder.add_node("send_notification", send_notification)
    builder.add_node("save_to_database",  save_to_database)

    builder.add_edge(START, "evaluate_logs")
    builder.add_conditional_edges("evaluate_logs", tool_router, {"GOOD": "process_logs", "BAD": "send_notification"})
    builder.add_edge("send_notification", "process_logs")
    builder.add_edge("process_logs", "save_to_database")
    builder.add_edge("save_to_database", END)

    graph = builder.compile()
    with open("graph.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    return graph


# ---------- COLLECT RECORDS IN 5 SEC INTERVALS, AND SENT TO AGENT ---------- #
def batch_process_messages(consumer, graph):
    while True:
        records = consumer.poll(timeout_ms=2000, max_records=5)
        logs_str = ""
        for record in records.values():
            for message in record:
                print(message.value)
                logs_str += message.value + "\n"

        print(f"Received logs: {logs_str}")
        if logs_str:
            state = State(logs=logs_str, logs_status="", logs_summary="")
            graph.invoke(state)


if __name__ == "__main__":
    graph    = define_langgraph_workflow()
    consumer = setup_consumer(IP_ADDRESS)
    batch_process_messages(consumer, graph)
