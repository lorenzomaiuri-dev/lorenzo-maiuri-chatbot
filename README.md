# 🤖 Lorenzo Maiuri — Intelligent Chatbot (Multi-Agent, ReAct-based)

This repository contains the backend code for the AI assistant integrated into my personal website — a **modular, multi-agent chatbot** that uses Google's **Gemini** model through **LlamaIndex**, implements the **ReAct (Reasoning + Acting) pattern**, and dynamically invokes real tools via function calling.

---

## ✨ Overview

The assistant is designed to:

- 💬 Respond only to questions about me, my work, and services
- 🧠 Reason step-by-step using **ReAct pattern**
- 🧰 Execute tool calls defined in the backend (e.g. send notifications, track leads)
- 🔁 Maintain memory and chat history in **MongoDB**
- 🧩 Give back response in structured output for frontend parsing and triggering custom actions
- ⚙️ Be extensible with multiple agents or capabilities in the future

Currently, a single **primary agent** handles requests, but the architecture is fully ready for **multi-agent workflows** and **tool orchestration**.

---

## 🧠 Technologies

| Layer       | Tech Used |
|-------------|-----------|
| LLM         | [Gemini](https://ai.google.dev/gemini-api/docs) |
| Framework   | [LlamaIndex](https://www.llamaindex.ai/) |
| Pattern     | ReAct (Reasoning + Acting) |
| DB          | MongoDB Atlas |
| Runtime     | Python 3.11+, FastAPI |
| Tool Calls  | Custom tool interfaces with automatic dispatching |

---

## 🔧 Features

- 🔄 **Session-based memory** (`chatId`-scoped conversation persistence)
- 🧩 **Tool calling** (e.g. `sendEmailToOwner`, `linkToSection:services`)
- 🤔 **Agent "thought" logging** (transparent reasoning step)
- 🔌 **Modular design**: you can add agents, tools, RAG pipelines
- 🔐 **OpenAI-compatible function calling** interface (Gemini backend)