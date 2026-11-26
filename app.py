"""The IPEDS Research Companion, version 2. Run: streamlit run app.py

The page is version 1's (page/ui.py, page/components.py, page/styles.css, .streamlit/config.toml), with its data
calls rewired to version 2's question path (path/answer.py). The page only displays what that path returns.
"""
from page.ui import main

main()
