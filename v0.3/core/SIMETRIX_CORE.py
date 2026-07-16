import os
import ollama

class Core:
    def __init__(self, model: str):
        self.model = model
        self.system_message = (
            "You are SIMETRIX, a precise, logical and efficient coding agent. "
            "You analyze problems, plan steps, and generate clean, functional code. "
            "If tools are available, you use them. You explain clearly and concisely."
        )

    # -----------------------------
    # Create file + AI-generated content
    # -----------------------------
    def createfile_with_ai(self, path: str, description: str) -> str:
        if os.path.exists(path):
            return f"[Error] File already exists: {path}"

        prompt = (
            f"Create the full content for the file '{path}'. "
            f"Description of the desired content: {description}. "
            f"Generate only the pure file content, without explanations and without specifying which programming language it is. "
            f"Generate code without Markdown code blocks (`python` and ```)."
        )

        try:
            # AI generates content
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_message},
                    {"role": "user", "content": prompt}
                ]
            )

            content = response['message']['content']

            # Create file + save content
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

            return f"[OK] File created and content generated: {path}"

        except Exception as e:
            return f"[Error while creating with AI] {e}"

    # -----------------------------
    # Read file
    # -----------------------------
    def readfile(self, path: str) -> str:
        if not os.path.exists(path):
            return f"[Error] File or path does not exist: {path}"

        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            return f"[Error while reading] {e}"

    # -----------------------------
    # Write file
    # -----------------------------
    def writefile(self, path: str, content: str) -> str:
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            return f"[OK] File successfully written: {path}"
        except Exception as e:
            return f"[Error while writing] {e}"

    # -----------------------------
    # Streaming
    # -----------------------------
    def stream(self, prompt: str):
        try:
            stream = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_message},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )

            for token in stream:
                content = token["message"]["content"]
                print(content, end="", flush=True)

            print()

        except Exception as e:
            print(f"[LLM-Error] {e}")
