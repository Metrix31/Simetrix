from core import Core

core = Core(model="qwen3-coder:30b")

print("SIMETRIX v0.3 started. Commands: /exit, /readfile, /writefile, /create, /stream")

while True:
    user_input = input("> ").strip()

    # EXIT
    if user_input == "/exit":
        print("Shutting down SIMETRIX.")
        break

    # CREATEFILE WITH AI
    elif user_input == "/create":
        file_path = input("File path> ").strip()
        description = input("Describe the desired file content> ").strip()

        result = core.createfile_with_ai(file_path, description)
        print(result)
        continue

    # READFILE
    elif user_input == "/readfile":
        file_path = input("File path> ").strip()
        custom_prompt = input("Describe what SIMETRIX should do> ").strip()

        file_content = core.readfile(file_path)

        prompt = (
            f"{custom_prompt}\n\n"
            f"--- File content ({file_path}) ---\n"
            f"{file_content}"
        )

        core.stream(prompt)
        continue

    # WRITEFILE
    elif user_input == "/writefile":
        file_path = input("File path> ").strip()
        print("Enter the content. Finish with a single line 'END':")

        lines = []
        while True:
            line = input()
            if line == "END":
                break
            lines.append(line)

        content = "\n".join(lines)
        print(core.writefile(file_path, content))
        continue

    # NORMAL CHAT
    else:
        core.stream(user_input)
