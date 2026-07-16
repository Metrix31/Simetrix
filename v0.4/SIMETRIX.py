#!/usr/bin/env python3
from core import Core
import os
import sys


def print_help():
    help_text = """
SIMETRIX v0.4 - Commands:
  /exit          - Exits SIMETRIX
  /help          - Shows this help
  /readfile      - Reads a file and processes it with AI
  /writefile     - Writes content to a file
  /create        - Creates a file with AI-generated content
  /edit          - Edits an existing file using AI
  /append        - Appends content to a file
  /listfiles     - Lists files in the current directory
  /history       - Shows recent conversations
  /clear         - Clears the screen
  /model [name]  - Switches the AI model
  /system        - Shows system information
"""
    print(help_text)


def main():
    # Initialize Core with default model
    core = Core(model="qwen3-coder:30b")

    print("SIMETRIX v0.4 started. Use /help for commands")
    print(f"Active model: {core.model}")
    print("-" * 50)

    while True:
        try:
            user_input = input("SIMETRIX> ").strip()

            # EXIT
            if user_input == "/exit":
                print("Shutting down SIMETRIX. Goodbye!")
                break

            # HELP
            elif user_input == "/help":
                print_help()
                continue

            # CREATEFILE WITH AI
            elif user_input == "/create":
                file_path = input("File path> ").strip()
                if not file_path:
                    print("[Error] No file path provided")
                    continue

                description = input("Describe the desired file content> ").strip()
                if not description:
                    print("[Error] No description provided")
                    continue

                result = core.createfile_with_ai(file_path, description)
                print(result)
                continue

            # READFILE
            elif user_input == "/readfile":
                file_path = input("File path> ").strip()
                if not file_path:
                    print("[Error] No file path provided")
                    continue

                if not os.path.exists(file_path):
                    print(f"[Error] File not found: {file_path}")
                    continue

                custom_prompt = input("Describe what SIMETRIX should do (empty for direct output)> ").strip()

                file_content = core.readfile(file_path)

                if not custom_prompt:
                    print(f"\n--- Content of {file_path} ---")
                    print(file_content)
                    print("-" * 30)
                    continue

                prompt = (
                    f"{custom_prompt}\n\n"
                    f"--- File content ({file_path}) ---\n"
                    f"{file_content}"
                )

                print("\nAI response:")
                core.stream(prompt)
                continue

            # WRITEFILE
            elif user_input == "/writefile":
                file_path = input("File path> ").strip()
                if not file_path:
                    print("[Error] No file path provided")
                    continue

                print("Enter the content. Finish with a single line 'END':")

                lines = []
                while True:
                    line = input()
                    if line == "END":
                        break
                    lines.append(line)

                content = "\n".join(lines)
                result = core.writefile(file_path, content)
                print(result)
                continue

            # EDIT FILE WITH AI
            elif user_input == "/edit":
                file_path = input("File path> ").strip()
                if not file_path:
                    print("[Error] No file path provided")
                    continue

                if not os.path.exists(file_path):
                    print(f"[Error] File not found: {file_path}")
                    continue

                edit_instruction = input("What should be edited?> ").strip()
                if not edit_instruction:
                    print("[Error] No edit instruction provided")
                    continue

                result = core.edit_file_with_ai(file_path, edit_instruction)
                print(result)
                continue

            # APPEND TO FILE
            elif user_input == "/append":
                file_path = input("File path> ").strip()
                if not file_path:
                    print("[Error] No file path provided")
                    continue

                print("Enter the content to append. Finish with 'END':")
                lines = []
                while True:
                    line = input()
                    if line == "END":
                        break
                    lines.append(line)

                content = "\n".join(lines)
                result = core.append_to_file(file_path, content)
                print(result)
                continue

            # LIST FILES
            elif user_input == "/listfiles":
                files = core.list_files()
                print("\nAvailable files:")
                for f in files:
                    print(f"  {f}")
                print()
                continue

            # HISTORY
            elif user_input == "/history":
                history = core.get_history()
                if not history:
                    print("No conversations in history")
                    continue

                print("\nConversation history:")
                print("=" * 50)
                for i, entry in enumerate(history[-10:], 1):  # Last 10 entries
                    print(f"{i}. User: {entry['user'][:100]}...")
                    print(f"   AI: {entry['assistant'][:100]}...")
                    print("-" * 30)
                print()
                continue

            # CLEAR SCREEN
            elif user_input == "/clear":
                os.system('cls' if os.name == 'nt' else 'clear')
                continue

            # MODEL SWITCH
            elif user_input.startswith("/model"):
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    new_model = parts[1].strip()
                    if core.switch_model(new_model):
                        print(f"[OK] Model switched to: {new_model}")
                    else:
                        print(f"[Error] Model not available: {new_model}")
                else:
                    print(f"Active model: {core.model}")
                continue

            # SYSTEM INFO
            elif user_input == "/system":
                info = core.get_system_info()
                print(f"\nSystem information:")
                print(f"  Active model: {info['model']}")
                print(f"  Python version: {info['python_version']}")
                print(f"  Working directory: {info['working_dir']}")
                print(f"  Saved conversations: {info['history_count']}")
                print()
                continue

            # NORMAL CHAT
            elif user_input:
                print("\nAI response:")
                core.stream(user_input)
                print()

            # EMPTY INPUT
            else:
                continue

        except KeyboardInterrupt:
            print("\n\nUse /exit to quit")
            continue
        except EOFError:
            print("\nShutting down SIMETRIX...")
            break
        except Exception as e:
            print(f"[System error] {e}")
            continue


if __name__ == "__main__":
    main()
