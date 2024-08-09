import streamlit as st
import ollama

st.title("Local LLM Chat")

# Allow the user to select a model
if "model" not in st.session_state:
    st.session_state["model"] = ""

models = [model["name"] for model in ollama.list()["models"]]
st.session_state["model"] = st.selectbox("Select Model", models)

user_input = st.text_input("Enter your prompt:")

if user_input:
    # Example with non-streaming response (commented out)
    response = ollama.generate(
        model=st.session_state["model"], prompt=user_input, stream=False
    )
    st.write(response["response"])


    # # Example with streaming response
    # st.write("Generating response...")

    # # Example with streaming response
    # response_placeholder = st.empty()
    # response_text = ""

    # for token in ollama.generate(
    #     model=st.session_state["model"], prompt=user_input, stream=True
    # ):
    #     response_text += token["response"]
    #     response_placeholder.markdown(response_text)

    # st.write("\nResponse complete.")
