import os
import ollama
import sys
import platform
from typing import List, Dict


class Core:
    def __init__(self, model: str):
        self.model = model
        self.history: List[Dict[str, str]] = []
        self.system_message = (
            "You are SIMETRIX, a precise, logical and efficient coding agent. "
            "You analyze problems, plan steps, and generate clean, functional code. "
            "If tools are available, you use them. You explain clearly and concisely. "
            "Always respond in German unless the user explicitly requests another language."
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
            f"Generate only the pure file content, without explanations and without specifying the programming language. "
            f"Generate code without Markdown code blocks (`python` and ```)"
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

            content = response["message"]["content"]

            # Create file + save content
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

            # Add to history
            self.history.append({
                "user": f"CREATE FILE: {path} - {description}",
                "assistant": f"File created with content: {content[:100]}..."
            })

            return f"[OK] File created and content generated: {path}"

        except Exception as e:
            error_msg = f"[Error while creating with AI] {e}"
            self.history.append({
                "user": f"CREATE FILE: {path} - {description}",
                "assistant": error_msg
            })
            return error_msg

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

            self.history.append({
                "user": f"WRITE FILE: {path}",
                "assistant": f"File written with {len(content)} characters"
            })

            return f"[OK] File successfully written: {path}"
        except Exception as e:
            error_msg = f"[Error while writing] {e}"
            self.history.append({
                "user": f"WRITE FILE: {path}",
                "assistant": error_msg
            })
            return error_msg

    # -----------------------------
    # Append to file
    # -----------------------------
    def append_to_file(self, path: str, content: str) -> str:
        try:
            with open(path, "a", encoding="utf-8") as file:
                file.write(content)

            self.history.append({
                "user": f"APPEND TO FILE: {path}",
                "assistant": f"Content appended ({len(content)} characters)"
            })

            return f"[OK] Content appended to file: {path}"
        except Exception as e:
            error_msg = f"[Error while appending] {e}"
            self.history.append({
                "user": f"APPEND TO FILE: {path}",
                "assistant": error_msg
            })
            return error_msg

    # -----------------------------
    # Edit file with AI
    # -----------------------------
    def edit_file_with_ai(self, path: str, instruction: str) -> str:
        try:
            # Read current content
            current_content = self.readfile(path)
            if current_content.startswith("[Error]"):
                return current_content

            prompt = (
                f"Edit the following file according to the instruction.\n"
                f"Instruction: {instruction}\n\n"
                f"--- Current file content ({path}) ---\n"
                f"{current_content}\n"
                f"--- End of file content ---\n\n"
                f"Return the fully edited file content. "
                f"Only the new content, no explanations."
            )

            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_message},
                    {"role": "user", "content": prompt}
                ]
            )

            new_content = response["message"]["content"]

            # Write new content
            with open(path, "w", encoding="utf-8") as file:
                file.write(new_content)

            self.history.append({
                "user": f"EDIT FILE: {path} - {instruction}",
                "assistant": f"File edited. New content: {new_content[:100]}..."
            })

            return f"[OK] File edited: {path}"

        except Exception as e:
            error_msg = f"[Error while editing] {e}"
            self.history.append({
                "user": f"EDIT FILE: {path} - {instruction}",
                "assistant": error_msg
            })
            return error_msg

    # -----------------------------
    # Streaming
    # -----------------------------
    def stream(self, prompt: str):
        full_response = ""
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
                full_response += content

            print()

            # Add to history
            self.history.append({
                "user": prompt,
                "assistant": full_response
            })

        except Exception as e:
            error_msg = f"[LLM-Error] {e}"
            print(error_msg)
            self.history.append({
                "user": prompt,
                "assistant": error_msg
            })

    # -----------------------------
    # List files
    # -----------------------------
    def list_files(self) -> List[str]:
        try:
            files = []
            for item in os.listdir("."):
                if os.path.isfile(item):
                    files.append(item)
            return sorted(files)
        except Exception:
            return []

    # -----------------------------
    # Switch model
    # -----------------------------
    def switch_model(self, new_model: str) -> bool:
        try:
            # Check if model is available
            models = ollama.list()
            available_models = [m['name'] for m in models['models']]

            if new_model in available_models:
                self.model = new_model
                return True
            else:
                # Try pulling the model
                try:
                    ollama.pull(new_model)
                    self.model = new_model
                    return True
                except:
                    return False
        except Exception:
            return False

    # -----------------------------
    # Get history
    # -----------------------------
    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    # -----------------------------
    # System information
    # -----------------------------
    def get_system_info(self) -> Dict[str, str]:
        return {
            "model": self.model,
            "python_version": sys.version.split()[0],
            "working_dir": os.getcwd(),
            "history_count": len(self.history),
            "platform": platform.system(),
            "ollama_version": self._get_ollama_version()
        }

    def _get_ollama_version(self) -> str:
        try:
            import subprocess
            result = subprocess.run(['ollama', '--version'],
                                    capture_output=True, text=True)
            return result.stdout.strip() if result.stdout else "Unknown"
        except:
            return "Not available"
