import streamlit as st
import subprocess
import json
import os

# Load config file
CONFIG_FILE = "tools_config.json"
with open(CONFIG_FILE) as f:
    TOOL_CONFIG = json.load(f)

st.set_page_config(page_title="BitByBharat Tool Launcher", layout="centered")
st.title("🧠 BitByBharat – AI Tools Launcher")
st.markdown("Select a tool below and run it from a browser.")

# Tool selector
tool_keys = list(TOOL_CONFIG.keys())
selected_tool = st.selectbox("Select a Tool", tool_keys)

tool_data = TOOL_CONFIG[selected_tool]
st.header(f"🔧 {tool_data['label']}")

if st.button("🚀 Run This Tool"):
    script_path = os.path.join(selected_tool, tool_data["entry_point"])
    with st.spinner(f"Running `{tool_data['entry_point']}`..."):
        try:
            result = subprocess.run(["python", script_path], check=True)
            st.success("✅ Tool completed successfully!")

            # 🔄 Show result JSON if it exists
            result_file = f"logs/{selected_tool}_ui_result.json"
            if os.path.exists(result_file):
                with open(result_file, "r") as f:
                    data = json.load(f)

                st.subheader("📊 Run Summary:")

                if data.get("tool") == "quora_scraper":
                    st.markdown(f"**Keywords Processed:** {data.get('total_keywords', '?')}")
                elif data.get("tool") == "content_radar":
                    st.markdown(f"**Category:** {data.get('category', 'N/A')}")

                st.markdown(f"✅ **Items Added to Notion:** {len(data['added'])}")
                st.markdown(f"🔁 **Duplicates Skipped:** {data.get('skipped', 0)}")

                if data["added"]:
                    st.subheader("📬 Notion Entries Added:")
                    for item in data["added"]:
                        st.markdown(f"- [{item['title']}]({item['url']})")

        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error running `{script_path}`: {e}")
