import os
import tempfile
import time

import openai
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from models.files import File
from models.settings import CommonsDep
from utils.file import compute_sha1_from_content


async def process_audio(commons: CommonsDep, file: File, enable_summarization: bool, user, user_openai_api_key):

    temp_filename = None
    file_sha = ""
    dateshort = time.strftime("%Y%m%d-%H%M%S")
    file_meta_name = f"audiotranscript_{dateshort}.txt"

    # use this for whisper
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if user_openai_api_key:
        openai_api_key = user_openai_api_key

    try:
        upload_file = file.file
        with tempfile.NamedTemporaryFile(delete=False, suffix=upload_file.filename) as tmp_file:
            await upload_file.seek(0)
            content = await upload_file.read()
            tmp_file.write(content)
            tmp_file.flush()
            tmp_file.close()

            temp_filename = tmp_file.name

            with open(tmp_file.name, "rb") as audio_file:
                transcript = openai.Audio.transcribe("whisper-1", audio_file)

        file_sha = compute_sha1_from_content(transcript.text.encode("utf-8"))
        file_size = len(transcript.text.encode("utf-8"))

        chunk_size = 500
        chunk_overlap = 0

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        texts = text_splitter.split_text(transcript.text.encode("utf-8"))

        docs_with_metadata = [Document(page_content=text, metadata={"file_sha1": file_sha, "file_size": file_size, "file_name": file_meta_name,
                                    "chunk_size": chunk_size, "chunk_overlap": chunk_overlap, "date": dateshort}) for text in texts]

        commons.documents_vector_store.add_documents(docs_with_metadata)

    finally:
        if temp_filename and os.path.exists(temp_filename):
             os.remove(temp_filename)
