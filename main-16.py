from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
import datetime
import json
import os
import ast
import operator

Window.clearcolor = (0.055, 0.055, 0.055, 1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
CHAT_FILE = os.path.join(BASE_DIR, "chat_history.json")
EXPORT_FILE = os.path.join(BASE_DIR, "sina_ai_chat.txt")


def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


memory = load_json(MEMORY_FILE, {})
chat_history = load_json(CHAT_FILE, [])

if not isinstance(memory, dict):
    memory = {}
if not isinstance(chat_history, list):
    chat_history = []


def save_memory():
    save_json(MEMORY_FILE, memory)


def save_chat():
    save_json(CHAT_FILE, chat_history)


def clean_text(text):
    if not isinstance(text, str):
        text = str(text)
    result = []
    for char in text:
        code = ord(char)
        if char == "\n":
            result.append("\n")
        elif char == "\t":
            result.append("    ")
        elif 32 <= code <= 126:
            result.append(char)
        else:
            result.append("?")
    return "".join(result)


operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def calculate_expression(expression):
    try:
        expression = expression.strip()
        if not expression or len(expression) > 100:
            return None

        tree = ast.parse(expression, mode="eval")

        def calculate(node):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    if abs(node.value) > 1000000000:
                        raise ValueError
                    return node.value
                raise ValueError

            if isinstance(node, ast.UnaryOp):
                value = calculate(node.operand)
                if isinstance(node.op, ast.USub):
                    return -value
                if isinstance(node.op, ast.UAdd):
                    return value
                raise ValueError

            if isinstance(node, ast.BinOp):
                left = calculate(node.left)
                right = calculate(node.right)
                operation = operators.get(type(node.op))
                if operation is None:
                    raise ValueError
                if abs(right) > 1000000000:
                    raise ValueError
                result = operation(left, right)
                if abs(result) > 1000000000000:
                    raise ValueError
                return result

            raise ValueError

        result = calculate(tree.body)
        if isinstance(result, float):
            result = round(result, 8)
        return str(result)

    except Exception:
        return None


def ai_answer(text):
    original = clean_text(text.strip())
    t = original.lower()

    if t in ["hi", "hello", "hey", "salam"]:
        return "Hello.\nWelcome to Sina AI.\nHow can I help you?"

    if "who are you" in t or "what are you" in t:
        return "I am Sina AI, your personal offline AI assistant."

    if t.startswith("my name is "):
        name = original[len("my name is "):].strip()
        if name:
            memory["name"] = name
            save_memory()
            return "Nice to meet you, " + name + "."

    if t in ["what is my name", "whats my name"]:
        name = memory.get("name")
        if name:
            return "Your name is " + str(name) + "."
        return "You have not told me your name yet."

    if t == "time" or "what time" in t:
        return "Current time: " + datetime.datetime.now().strftime("%H:%M:%S")

    if t == "date" or t == "today" or "today's date" in t or "todays date" in t:
        return "Today's date: " + datetime.datetime.now().strftime("%Y-%m-%d")

    if t.startswith("calculate "):
        result = calculate_expression(original[len("calculate "):].strip())
        if result is not None:
            return "Result: " + result
        return "I could not calculate that."

    allowed = "0123456789+-*/().% "
    if (any(s in original for s in ["+", "*", "/", "%"])
            and all(c in allowed for c in original)):
        result = calculate_expression(original)
        if result is not None:
            return "Result: " + result

    if t == "memory" or "what do you remember" in t:
        if not memory:
            return "My memory is currently empty."
        lines = [str(k) + ": " + str(v) for k, v in memory.items()]
        return "What I remember:\n" + "\n".join(lines)

    if t in ["help", "commands", "what can you do"]:
        return (
            "I can help with:\n\n"
            "- Time and date\n"
            "- Calculations\n"
            "- Remembering your name\n"
            "- Chat history\n"
            "- Copying answers\n"
            "- Exporting chat\n"
            "- Searching chat\n"
            "- Chat statistics\n"
            "- Suggestions"
        )

    if "suggest" in t or "idea" in t:
        return (
            "Try these:\n\n"
            "1. What time is it?\n"
            "2. What is today's date?\n"
            "3. Calculate 25*4+10\n"
            "4. My name is Sina\n"
            "5. What is my name?\n"
            "6. What do you remember?\n"
            "7. What can you do?"
        )

    if "thank" in t or "thanks" in t:
        return "You are welcome."

    if t == "bye" or "goodbye" in t:
        return "Goodbye. See you soon."

    return (
        "I received your message:\n\n" + original +
        "\n\nI am an offline assistant, so my built-in knowledge is limited."
    )


class Panel(BoxLayout):
    def __init__(self, bg=(0.10, 0.10, 0.10, 1), radius=14, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bg)
            self.background = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[radius]
            )
        self.bind(pos=self.update_background, size=self.update_background)

    def update_background(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size


class Message(BoxLayout):
    def __init__(self, text, user=False, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            padding=(12, 10),
            spacing=8,
            **kwargs
        )

        safe_text = clean_text(text)
        lines = safe_text.count("\n") + 1
        self.height = max(75, 42 * lines)

        panel = Panel(
            bg=(0.12, 0.12, 0.12, 1) if user else (0.075, 0.075, 0.075, 1),
            size_hint_x=0.95,
            padding=(16, 10)
        )

        label = Label(
            text=safe_text,
            font_size=22,
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle"
        )
        panel.add_widget(label)

        if user:
            self.add_widget(Label(text="", size_hint_x=0.05))
            self.add_widget(panel)
        else:
            self.add_widget(panel)
            self.add_widget(Label(text="", size_hint_x=0.05))


class SinaAI(App):
    def build(self):
        self.last_answer = ""
        self.root_box = BoxLayout(
            orientation="vertical",
            padding=8,
            spacing=6
        )
        self.chat_page()
        return self.root_box

    def chat_page(self):
        self.root_box.clear_widgets()

        top = BoxLayout(size_hint_y=0.11, spacing=8, padding=(5, 5))

        title = Label(
            text="Sina AI",
            font_size=30,
            bold=True,
            color=(1, 1, 1, 1)
        )

        new_button = Button(text="New Chat", size_hint_x=0.25, font_size=18)
        new_button.bind(on_press=self.new_chat)

        settings = Button(text="Settings", size_hint_x=0.25, font_size=18)
        settings.bind(on_press=self.settings)

        top.add_widget(title)
        top.add_widget(new_button)
        top.add_widget(settings)

        self.chat = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=2,
            padding=(0, 5)
        )
        self.chat.bind(minimum_height=self.chat.setter("height"))

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.scroll.add_widget(self.chat)

        if not chat_history:
            self.add_message(
                "Hello.\nWelcome to Sina AI.\nHow can I help you?",
                False
            )
        else:
            for item in chat_history:
                if isinstance(item, dict):
                    self.add_message(
                        item.get("text", ""),
                        item.get("user", False),
                        save=False
                    )

        bottom = Panel(
            bg=(0.12, 0.12, 0.12, 1),
            size_hint_y=0.12,
            padding=(7, 7),
            spacing=7
        )

        self.input = TextInput(
            hint_text="Message",
            multiline=False,
            font_size=22,
            foreground_color=(1, 1, 1, 1),
            background_color=(0.16, 0.16, 0.16, 1),
            cursor_color=(1, 1, 1, 1),
            padding=(12, 10)
        )
        self.input.bind(on_text_validate=self.send)

        send = Button(text="Send", size_hint_x=0.25, font_size=20)
        send.bind(on_press=self.send)

        bottom.add_widget(self.input)
        bottom.add_widget(send)

        self.root_box.add_widget(top)
        self.root_box.add_widget(self.scroll)
        self.root_box.add_widget(bottom)

    def add_message(self, text, user=False, save=True):
        safe_text = clean_text(text)
        self.chat.add_widget(Message(safe_text, user))

        if save:
            chat_history.append({"text": safe_text, "user": user})
            save_chat()

        if not user:
            self.last_answer = safe_text

        Clock.schedule_once(self.scroll_bottom, 0.05)

    def scroll_bottom(self, dt):
        try:
            self.scroll.scroll_y = 0
        except Exception:
            pass

    def send(self, btn):
        try:
            text = self.input.text.strip()
            if not text:
                return

            text = clean_text(text)
            self.add_message(text, True)
            self.add_message(ai_answer(text), False)
            self.input.text = ""

        except Exception:
            self.add_message("An internal error occurred.", False)

    def new_chat(self, btn):
        global chat_history
        chat_history = []
        save_chat()
        self.last_answer = ""
        self.chat_page()

    def settings(self, btn):
        self.root_box.clear_widgets()

        title = Label(
            text="Settings",
            font_size=30,
            bold=True,
            size_hint_y=0.15
        )

        buttons = [
            ("Copy Last Answer", self.copy_last_answer),
            ("Export Chat", self.export_chat),
            ("Search Chat", self.search_chat),
            ("Chat Statistics", self.show_statistics),
            ("Clear Chat", self.clear_chat),
            ("Clear Memory", self.clear_memory),
            ("Show Suggestions", self.show_suggestions),
        ]

        self.root_box.add_widget(title)

        for text, callback in buttons:
            b = Button(text=text, font_size=20)
            b.bind(on_press=callback)
            self.root_box.add_widget(b)

        back = Button(text="Back", font_size=20)
        back.bind(on_press=lambda x: self.chat_page())
        self.root_box.add_widget(back)

    def copy_last_answer(self, btn):
        try:
            if not self.last_answer:
                self.chat_page()
                self.add_message("There is no answer to copy.")
                return

            Clipboard.copy(self.last_answer)
            self.chat_page()
            self.add_message("Last answer copied.")
        except Exception:
            self.chat_page()
            self.add_message("Copy failed.")

    def export_chat(self, btn):
        try:
            with open(EXPORT_FILE, "w", encoding="utf-8") as file:
                for item in chat_history:
                    if not isinstance(item, dict):
                        continue
                    sender = "You" if item.get("user", False) else "Sina AI"
                    file.write(
                        sender + ":\n" +
                        clean_text(item.get("text", "")) +
                        "\n\n"
                    )

            self.chat_page()
            self.add_message("Chat exported successfully.")
        except Exception:
            self.chat_page()
            self.add_message("Export failed.")

    def search_chat(self, btn):
        self.root_box.clear_widgets()

        title = Label(
            text="Search Chat",
            font_size=30,
            bold=True,
            size_hint_y=0.15
        )

        search_input = TextInput(
            hint_text="Search",
            multiline=False,
            font_size=22
        )

        results = Label(
            text="Enter a word and press Search.",
            font_size=20,
            halign="left",
            valign="top"
        )
        results.size_hint_y = 0.55

        search_button = Button(text="Search", font_size=20)
        back = Button(text="Back", font_size=20)

        def do_search(instance):
            query = clean_text(search_input.text.strip().lower())

            if not query:
                results.text = "Please enter a search word."
                return

            matches = []

            for item in chat_history:
                if not isinstance(item, dict):
                    continue

                message = clean_text(item.get("text", ""))

                if query in message.lower():
                    sender = "You" if item.get("user", False) else "Sina AI"
                    matches.append(sender + ": " + message)

            if matches:
                results.text = "Results:\n\n" + "\n\n".join(matches[-20:])
            else:
                results.text = "No matching messages found."

        search_button.bind(on_press=do_search)
        back.bind(on_press=lambda x: self.settings(None))

        self.root_box.add_widget(title)
        self.root_box.add_widget(search_input)
        self.root_box.add_widget(search_button)
        self.root_box.add_widget(results)
        self.root_box.add_widget(back)

    def show_statistics(self, btn):
        user_count = 0
        ai_count = 0

        for item in chat_history:
            if not isinstance(item, dict):
                continue
            if item.get("user", False):
                user_count += 1
            else:
                ai_count += 1

        total = user_count + ai_count

        self.chat_page()
        self.add_message(
            "Chat Statistics:\n\n"
            "Total messages: " + str(total) + "\n"
            "Your messages: " + str(user_count) + "\n"
            "Sina AI messages: " + str(ai_count) + "\n"
            "Memory items: " + str(len(memory))
        )

    def clear_chat(self, btn):
        global chat_history
        chat_history = []
        save_chat()
        self.last_answer = ""
        self.chat_page()

    def clear_memory(self, btn):
        memory.clear()
        save_memory()
        self.chat_page()

    def show_suggestions(self, btn):
        self.chat_page()
        self.add_message(
            "Try these:\n\n"
            "1. What time is it?\n"
            "2. What is today's date?\n"
            "3. Calculate 25*4+10\n"
            "4. My name is Sina\n"
            "5. What is my name?\n"
            "6. What do you remember?\n"
            "7. What can you do?"
        )


if __name__ == "__main__":
    SinaAI().run()
