"""Autenticación mediante RUT + Supabase Auth, solo en servidor Streamlit.

Los propietarios NO reciben una contraseña basada en el RUT. Una invitación
confirmada por correo les permite escogerla. El correo no aparece en login.
"""
import os
import re
import streamlit as st
from supabase import create_client
from supabase.lib.client_options import ClientOptions


def secret(name):
    try:
        return str(st.secrets[name])
    except Exception:
        return os.environ.get(name, "")


def normalize_rut(value):
    clean = re.sub(r"[^0-9kK]", "", str(value)).upper()
    if not re.fullmatch(r"[0-9]{1,8}[0-9K]", clean):
        raise ValueError("Ingresa un RUT válido.")
    number, dv = str(int(clean[:-1])), clean[-1]
    total = sum(int(c) * mult for c, mult in zip(reversed(number), (2, 3, 4, 5, 6, 7) * 2))
    calc = 11 - (total % 11)
    expected = "0" if calc == 11 else "K" if calc == 10 else str(calc)
    if dv != expected:
        raise ValueError("El dígito verificador del RUT no es correcto.")
    return f"{number}-{dv}"


def _client(key):
    url = secret("SUPABASE_URL")
    if not url or not key:
        raise RuntimeError("Configura SUPABASE_URL y las claves en Secrets.")
    return create_client(url, key, options=ClientOptions(
        auto_refresh_token=False, persist_session=False,
    ))


def public_client():
    return _client(secret("SUPABASE_PUBLISHABLE_KEY"))


def admin_client():
    # Server-only: nunca devolver la clave sb_secret_* al navegador.
    return _client(secret("SUPABASE_SERVICE_ROLE_KEY"))


def clear_session():
    for key in ("auth_access", "auth_refresh", "auth_profile", "auth_uid",
                "pending_first_login", "reservation_review", "selected_reservation"):
        st.session_state.pop(key, None)
    st.session_state.page = "Inicio"


def sign_in(rut, password, lookup_email_and_profile, complete_invite):
    """Autentica el RUT; registra etapas técnicas sin divulgar datos privados.

    Los mensajes LOGIN_DIAG se escriben SOLO en los logs del servidor Streamlit.
    El navegador sigue mostrando errores genéricos de autenticación.
    Estos diagnósticos son temporales y se pueden retirar tras la reparación.
    """
    try:
        rut = normalize_rut(rut)
    except ValueError:
        print("LOGIN_DIAG: RUT_FORMATO_INVALIDO", flush=True)
        raise

    try:
        profile = lookup_email_and_profile(rut)
    except Exception as exc:
        print(f"LOGIN_DIAG: ERROR_CONSULTA_PERFIL tipo={type(exc).__name__}", flush=True)
        raise ValueError("No se pudo verificar el acceso.") from None

    if not profile:
        print("LOGIN_DIAG: PERFIL_NO_ENCONTRADO", flush=True)
        raise ValueError("Credenciales incorrectas o cuenta no habilitada.")
    if not profile.get("is_active"):
        print("LOGIN_DIAG: PERFIL_INACTIVO", flush=True)
        raise ValueError("Credenciales incorrectas o cuenta no habilitada.")

    try:
        response = public_client().auth.sign_in_with_password({
            "email": profile["login_email"], "password": password,
        })
    except Exception as exc:
        # Nunca escribir RUT, email, contraseña, claves ni contenido de errores
        # externos en los logs. Solo la clase y metadatos acotados.
        code = getattr(exc, "code", None)
        code = str(code) if code is not None else "SIN_CODIGO"
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", code):
            code = "NO_DISPONIBLE"
        status = getattr(exc, "status", None)
        status = str(status) if isinstance(status, int) else "SIN_ESTADO"
        print(
            f"LOGIN_DIAG: AUTH_ERROR tipo={type(exc).__name__} "
            f"codigo={code} estado={status}", flush=True,
        )
        raise ValueError("Credenciales incorrectas o cuenta no habilitada.") from None

    if not response.user or not response.session:
        print("LOGIN_DIAG: AUTH_SIN_SESION", flush=True)
        raise ValueError("Cuenta no habilitada.")
    if str(response.user.id) != str(profile["user_id"]):
        print("LOGIN_DIAG: AUTH_USUARIO_NO_COINCIDE_PERFIL", flush=True)
        raise ValueError("Cuenta no habilitada.")

    if profile.get("must_change_password"):
        if (len(password) < 12 or password == rut.split("-")[0] or
                not getattr(response.user, "email_confirmed_at", None)):
            print("LOGIN_DIAG: INVITACION_PENDIENTE", flush=True)
            raise ValueError("Completa primero la invitación recibida por correo.")
        try:
            complete_invite(str(response.user.id))
            profile = lookup_email_and_profile(rut)
        except Exception as exc:
            print(f"LOGIN_DIAG: ERROR_FINALIZAR_INVITACION tipo={type(exc).__name__}", flush=True)
            raise ValueError("No se pudo finalizar la activación.") from None
        if not profile or profile.get("must_change_password"):
            print("LOGIN_DIAG: INVITACION_NO_FINALIZADA", flush=True)
            raise ValueError("No se pudo finalizar la activación.")

    st.session_state.auth_access = response.session.access_token
    st.session_state.auth_refresh = response.session.refresh_token
    st.session_state.auth_uid = str(response.user.id)
    st.session_state.auth_profile = dict(profile)
    print("LOGIN_DIAG: AUTENTICACION_CORRECTA", flush=True)
    return True


def current_profile(lookup_by_uid):
    token = st.session_state.get("auth_access")
    if not token:
        return None
    client = public_client()
    try:
        user = client.auth.get_user(token).user
    except Exception:
        refresh = st.session_state.get("auth_refresh")
        if not refresh:
            clear_session()
            return None
        try:
            response = client.auth.refresh_session(refresh)
            token = response.session.access_token
            st.session_state.auth_access = token
            st.session_state.auth_refresh = response.session.refresh_token
            user = client.auth.get_user(token).user
        except Exception:
            clear_session()
            return None
    if not user:
        clear_session()
        return None
    profile = lookup_by_uid(str(user.id))
    if not profile or not profile.get("is_active") or profile.get("must_change_password"):
        clear_session()
        return None
    st.session_state.auth_uid = str(user.id)
    st.session_state.auth_profile = dict(profile)
    return dict(profile)


def change_password(new_password):
    if len(new_password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")
    client = public_client()
    client.auth.set_session(st.session_state["auth_access"],
                            st.session_state["auth_refresh"])
    client.auth.update_user({"password": new_password})
    clear_session()


def invite_owner(email, name):
    """Envía invitación por email usando plantilla predeterminada Invite user."""
    app_url = secret("PUBLIC_APP_URL").strip()
    if not app_url.startswith("https://"):
        raise ValueError("Configura PUBLIC_APP_URL con la URL https de Streamlit.")
    response = admin_client().auth.admin.invite_user_by_email(
        email.strip().lower(),
        {"redirect_to": app_url, "data": {"full_name": name}},
    )
    if not response.user:
        raise RuntimeError("Supabase no devolvió un usuario de la invitación.")
    return str(response.user.id)


def delete_auth_user(uid):
    return admin_client().auth.admin.delete_user(uid)


def send_password_recovery(email):
    app_url = secret("PUBLIC_APP_URL").strip()
    if not app_url.startswith("https://"):
        raise ValueError("Configura PUBLIC_APP_URL.")
    public_client().auth.reset_password_for_email(email.strip().lower(),
        {"redirect_to": app_url})
