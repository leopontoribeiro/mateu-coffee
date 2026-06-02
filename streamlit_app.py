import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pytz
import json
import time

st.set_page_config(
    page_title="Mateu Coffee | Extracao",
        page_icon="",
            layout="wide",
                initial_sidebar_state="collapsed"
                )

                st.title("Mateu Coffee")
                st.markdown("## Engenharia de Extracao")
                st.divider()
                st.success("Aplicacao v1.1 em execucao no Streamlit Cloud")
                st.info("Conectando ao banco de dados PostgreSQL...")

                try:
                    conn = st.connection("postgresql", type="sql")
                        st.success("Conexao com banco de dados estabelecida!")
                        except Exception as e:
                            st.error(f"Erro ao conectar: {str(e)}")
                                st.info("Certifique-se de que as credenciais estao configuradas no Streamlit Secrets.")
