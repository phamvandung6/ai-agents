from typing import Annotated

from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda, RunnableSerializable
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph

from src.agents.admission_agent.vector_store import AdmissionVectorStore
from src.core.settings import settings


class AgentState(MessagesState, total=False):
    """State for admission agent.

    `total=False` is PEP589 specs for TypedDict.
    documentation: https://typing.readthedocs.io/en/latest/spec/typeddict.html#totality
    """

    context: Annotated[dict, "Retrieved context from vector store"]


BASE_CONTEXT = """
Thông tin cơ bản về các ngành đào tạo:

1. TOÁN HỌC (QHT01):
- Tổ hợp xét tuyển: A00, A01, D07, D08
- Điểm chuẩn 2024: 34.45/40 (Điểm Toán x2 + Hai môn còn lại)
- Học phí: ~1.640.000 VNĐ/tháng
- Có 2 hệ: Chuẩn và CNKHTN (Cử nhân Khoa học Tài năng)

2. TOÁN TIN (QHT02):
- Tổ hợp xét tuyển: A00, A01, D07, D08
- Điểm chuẩn 2024: 34.45/40 (Điểm Toán x2 + Hai môn còn lại)
- Học phí: ~2.700.000 VNĐ/tháng
- Định hướng: Tính toán khoa học và Tin học

3. KHOA HỌC MÁY TÍNH VÀ THÔNG TIN (QHT98):
- Tổ hợp xét tuyển: A00, A01, D07, D08
- Điểm chuẩn 2024: 34.70/40 (Điểm Toán x2 + Hai môn còn lại)
- Học phí: ~3.700.000 VNĐ/tháng
- Định hướng: Phát triển phần mềm và trí tuệ nhân tạo

4. KHOA HỌC DỮ LIỆU (QHT93):
- Tổ hợp xét tuyển: A00, A01, D07, D08
- Điểm chuẩn 2024: 35.00/40 (Điểm Toán x2 + Hai môn còn lại)
- Học phí: ~1.640.000 VNĐ/tháng
- Định hướng: Khoa học máy tính, Thống kê và Toán ứng dụng

Lưu ý chung:
- Thời gian đào tạo: 4 năm
- Mã trường: QHT
- Các tổ hợp xét tuyển:
  + A00: Toán, Lý, Hóa
  + A01: Toán, Lý, Anh
  + D07: Toán, Hóa, Anh
  + D08: Toán, Sinh, Anh
"""


ADMISSION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Bạn là trợ lý tư vấn tuyển sinh của Khoa Toán - Cơ - Tin học, Trường Đại học Khoa học Tự nhiên, ĐHQGHN.
Nhiệm vụ của bạn là trả lời các câu hỏi về tuyển sinh của thí sinh và phụ huynh.

{base_context}

Hãy sử dụng thông tin trong context để trả lời chi tiết hơn. Nếu không có thông tin trong context bổ sung, hãy trả lời dựa trên thông tin cơ bản ở trên.
Trả lời ngắn gọn, chính xác và thân thiện.

Context bổ sung: {context}""",
        ),
        ("user", "{message}"),
    ],
)


def wrap_model(model: ChatGoogleGenerativeAI) -> RunnableSerializable[AgentState, AIMessage]:
    """Wrap the model to handle state properly."""
    preprocessor = RunnableLambda(
        lambda state: {
            "base_context": BASE_CONTEXT,
            "context": "\n".join(state.get("context", {}).get("relevant_docs", [])),
            "message": state["messages"][-1].content if state["messages"] else "",
        },
        name="StatePreprocessor",
    )
    return preprocessor | ADMISSION_PROMPT | model


async def retrieve_context(state: AgentState) -> AgentState:
    """Retrieve relevant context from vector store."""
    vector_store = AdmissionVectorStore()

    # Get the last user message
    last_message = state["messages"][-1]
    if last_message.type != "human":
        return state

    # Search for relevant documents
    docs = await vector_store.similarity_search(last_message.content)

    # Update state with retrieved context
    return {
        **state,
        "context": {
            "relevant_docs": [doc.page_content for doc in docs],
            "sources": [doc.metadata for doc in docs],
        },
    }


async def generate_response(state: AgentState, config: RunnableConfig) -> AgentState:
    """Generate response based on context and conversation history."""
    model = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.7,
        convert_system_message_to_human=True,
    )
    model_runnable = wrap_model(model)
    response = await model_runnable.ainvoke(state, config)

    return {"messages": [response]}


# Define the graph
agent = StateGraph(AgentState)

# Add nodes
agent.add_node("retrieve_context", retrieve_context)
agent.add_node("generate_response", generate_response)

# Set entry point
agent.set_entry_point("retrieve_context")

# Add edges
agent.add_edge("retrieve_context", "generate_response")
agent.add_edge("generate_response", END)

# Compile the agent
admission_agent = agent.compile(
    checkpointer=MemorySaver(),
)
