import os
import yaml
import tempfile
import streamlit as st
from pathlib import Path
import config.conf as conf
import streamlit_authenticator as stauth
from dotenv import load_dotenv
load_dotenv()

def get_config():
    with open(Path(conf.CONFIG_DIR, "creds.yaml")) as file:
        config = yaml.safe_load(file)
    return config

def apply_css(file):
    CSS_FILE = Path(conf.CSS_DIR, file)
    with open(CSS_FILE) as f:
        css = f.read()
    st.markdown(f'<style>{css}</style>', unsafe_allow_html = True)