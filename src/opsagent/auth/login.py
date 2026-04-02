"""Componente de login/signup para Streamlit con Supabase."""

import os
import streamlit as st


def _get_supabase_client():
    """Crear cliente Supabase."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def login_required() -> bool:
    """True si Supabase esta configurado y se requiere login."""
    return bool(os.environ.get("SUPABASE_URL")) and bool(os.environ.get("SUPABASE_KEY"))


def is_logged_in() -> bool:
    """True si hay un token valido en session_state."""
    return "access_token" in st.session_state and st.session_state["access_token"]


def get_access_token() -> str | None:
    """Obtener el access_token del usuario actual."""
    return st.session_state.get("access_token")


def show_login_page() -> None:
    """Mostrar formulario de login/signup. Detiene la app si no se autentica."""
    st.title("OpsAgent")
    st.caption("Diagnostico operativo con IA para PyMEs industriales")

    client = _get_supabase_client()
    if client is None:
        st.error("Supabase no configurado. Verifica SUPABASE_URL y SUPABASE_KEY.")
        st.stop()

    tab_login, tab_signup = st.tabs(["Iniciar sesion", "Crear cuenta"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Contrasena", type="password")
            submitted = st.form_submit_button("Iniciar sesion", use_container_width=True)

            if submitted and email and password:
                try:
                    result = client.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state["access_token"] = result.session.access_token
                    st.session_state["user_email"] = result.user.email
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al iniciar sesion: {e}")

    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Contrasena", type="password", key="signup_password")
            submitted = st.form_submit_button("Crear cuenta", use_container_width=True)

            if submitted and new_email and new_password:
                try:
                    result = client.auth.sign_up({"email": new_email, "password": new_password})
                    if result.session:
                        st.session_state["access_token"] = result.session.access_token
                        st.session_state["user_email"] = result.user.email
                        st.rerun()
                    else:
                        st.success("Cuenta creada. Revisa tu email para confirmar.")
                except Exception as e:
                    st.error(f"Error al crear cuenta: {e}")


def show_user_sidebar() -> None:
    """Mostrar info del usuario y boton logout en el sidebar."""
    email = st.session_state.get("user_email", "Usuario")
    st.sidebar.caption(f"Sesion: {email}")
    if st.sidebar.button("Cerrar sesion", use_container_width=True):
        st.session_state.pop("access_token", None)
        st.session_state.pop("user_email", None)
        st.session_state.pop("result", None)
        st.rerun()
