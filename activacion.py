"""Formulario web que consume el enlace predeterminado de invitación Supabase.

Funciona sin editar Email Templates. Solo publica SUPABASE_URL y la clave
publishable; NO envía jamás la clave secreta o la URL de PostgreSQL al navegador.
"""
import json
import streamlit as st
import acceso


def render_activation():
    url = json.dumps(acceso.secret("SUPABASE_URL"))
    key = json.dumps(acceso.secret("SUPABASE_PUBLISHABLE_KEY"))
    # Streamlit 1.52+ admite JavaScript explícito en st.html; el fragmento URL
    # con tokens nunca es enviado al servidor ni movido a query params.
    html = r'''
    <div id="rut-activation" style="display:none;position:fixed;inset:0;z-index:10000;
        background:rgba(22,19,25,.86);align-items:center;justify-content:center;padding:18px">
      <div style="background:#fff;border-radius:18px;max-width:440px;width:100%;padding:28px;
          color:#29232e;font:15px/1.5 system-ui,sans-serif">
        <h2 style="margin:0 0 10px;color:#b83272">Configura tu contraseña</h2>
        <p id="rut-activation-message" style="margin:0 0 16px">Tu correo ha sido verificado. Elige una contraseña personal.</p>
        <form id="rut-activation-form">
          <label for="rut-new-pass">Nueva contraseña (12 caracteres o más)</label>
          <input id="rut-new-pass" type="password" autocomplete="new-password" minlength="12"
              required style="display:block;width:100%;padding:10px;margin:7px 0 14px;border:1px solid #ccc;border-radius:7px"/>
          <label for="rut-repeat-pass">Confirmar contraseña</label>
          <input id="rut-repeat-pass" type="password" autocomplete="new-password" minlength="12"
              required style="display:block;width:100%;padding:10px;margin:7px 0 16px;border:1px solid #ccc;border-radius:7px"/>
          <button id="rut-activation-btn" type="submit"
              style="display:block;width:100%;background:#b83272;color:#fff;border:0;border-radius:8px;padding:11px;cursor:pointer">
            Guardar contraseña</button>
        </form>
        <p id="rut-activation-error" role="alert" style="color:#b42318;font-size:13px"></p>
      </div>
    </div>
    <script>
    (function () {
      const hash = new URLSearchParams(location.hash.replace(/^#/, ""));
      const mode = hash.get("type");
      const token = hash.get("access_token");
      const root = document.getElementById("rut-activation");
      if (!token || !["invite", "recovery"].includes(mode)) return;
      root.style.display = "flex";
      const error = document.getElementById("rut-activation-error");
      const message = document.getElementById("rut-activation-message");
      if (mode === "recovery") message.textContent = "Establece una nueva contraseña para recuperar tu acceso.";
      // El token permanece solo en la memoria de esta pestaña y sale de la barra de direcciones.
      history.replaceState(null, "", location.pathname + location.search);
      document.getElementById("rut-activation-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        error.textContent = "";
        const pw = document.getElementById("rut-new-pass").value;
        const repeat = document.getElementById("rut-repeat-pass").value;
        if (pw.length < 12) { error.textContent = "Utiliza al menos 12 caracteres."; return; }
        if (pw !== repeat) { error.textContent = "Las contraseñas no coinciden."; return; }
        const btn = document.getElementById("rut-activation-btn");
        btn.disabled = true;
        btn.textContent = "Guardando…";
        try {
          const response = await fetch(__SUPABASE_URL__ + "/auth/v1/user", {
            method: "PUT",
            headers: {"apikey": __PUBLIC_KEY__, "Authorization": "Bearer " + token,
                "Content-Type": "application/json"},
            body: JSON.stringify({"password": pw}),
          });
          if (!response.ok) throw Error("El enlace expiró o la contraseña no cumple los requisitos.");
          document.getElementById("rut-activation-form").style.display = "none";
          message.textContent = "Contraseña guardada. Ya puedes iniciar sesión con tu RUT y la nueva contraseña.";
          const back = document.createElement("button");
          back.textContent = "Ir al inicio de sesión";
          back.style.cssText = "background:#b83272;color:white;border:0;border-radius:8px;padding:12px;width:100%;cursor:pointer";
          back.onclick = () => location.reload();
          root.querySelector("div").appendChild(back);
        } catch (e) {
          error.textContent = e.message || "No se pudo guardar. Solicita un nuevo enlace de invitación.";
          btn.disabled = false;
          btn.textContent = "Guardar contraseña";
        }
      });
    })();
    </script>
    '''
    html = html.replace("__SUPABASE_URL__", url).replace("__PUBLIC_KEY__", key)
    st.html(html, unsafe_allow_javascript=True)
