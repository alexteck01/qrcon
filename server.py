import json
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------------------------
# CONFIGURAZIONE SUPABASE
# ---------------------------------------------------------
SUPABASE_URL = "https://uqcjspndheidokixwrqb.supabase.co"
SUPABASE_KEY = "sb_publishable_5TO_BNQMyBjG_Om8uKgkmA_wuOlEjxS"
SUPABASE_TABLE = "storico"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ---------------------------------------------------------
# SALVA SU SUPABASE
# ---------------------------------------------------------
def salva_su_supabase(id_oggetto, dati):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    payload = {"id_oggetto": id_oggetto, "dati": dati}
    return requests.post(url, headers=headers, json=payload).json()

# ---------------------------------------------------------
# CARICA DA SUPABASE
# ---------------------------------------------------------
def carica_da_supabase(id_oggetto):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?id_oggetto=eq.{id_oggetto}&select=*&order=created_at.asc"
    righe = requests.get(url, headers=headers).json()

    if not righe:
        return {"eventi": [], "note": ""}

    eventi = []
    note = ""

    for r in righe:
        dati = r["dati"]
        if isinstance(dati, str):
            try:
                dati = json.loads(dati)
            except:
                continue

        if "evento" in dati and "timestamp" in dati:
            eventi.append((dati["evento"], dati["timestamp"]))

        if "note" in dati:
            note = dati["note"]

    return {"eventi": eventi, "note": note}

# ---------------------------------------------------------
# DETERMINA IN/OUT
# ---------------------------------------------------------
def determina_evento(storico):
    if not storico["eventi"]:
        return "IN"
    return "IN" if storico["eventi"][-1][0] == "OUT" else "OUT"

# ---------------------------------------------------------
# REGISTRA EVENTO
# ---------------------------------------------------------
def registra_evento(id_oggetto, storico, evento):
    ora = datetime.now().strftime("%d/%m/%Y – %H:%M:%S")
    salva_su_supabase(id_oggetto, {"evento": evento, "timestamp": ora})
    storico["eventi"].append((evento, ora))
    return ora

# ---------------------------------------------------------
# SALVA NOTE
# ---------------------------------------------------------
@app.route("/salva_note", methods=["POST"])
def salva_note():
    id_oggetto = request.form.get("id")
    testo_note = request.form.get("note", "")

    storico = carica_da_supabase(id_oggetto)
    storico["note"] = testo_note

    salva_su_supabase(id_oggetto, storico)

    return f"""
<pre>
Note salvate correttamente per {id_oggetto}.
<a href="/qrcon?id={id_oggetto}">⬅ Torna indietro</a>
</pre>
"""

# ---------------------------------------------------------
# PAGINA PRINCIPALE
# ---------------------------------------------------------
@app.route("/qrcon")
def qrcon():
    id_oggetto = request.args.get("id", "Sconosciuto")

    storico = carica_da_supabase(id_oggetto)
    evento = determina_evento(storico)
    ora = registra_evento(id_oggetto, storico, evento)

    eventi = storico["eventi"]
    storico_testo = ''.join(f"{ev} – {ts}\n" for ev, ts in reversed(eventi))
    note_correnti = storico["note"]

    return f"""
<style>
.summary-arrow {{
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
}}

details summary::marker {{
    display: none;
}}

details[open] .arrow {{
    transform: rotate(90deg);
}}
</style>

<pre>
────────────────────────────────────
            v11 – {evento}
────────────────────────────────────

🟢 {evento} registrata
{ora}

────────────────────────────────────
📜 inizio/fine

{storico_testo}
────────────────────────────────────
</pre>

<form action="/salva_note" method="POST">
<input type="hidden" name="id" value="{id_oggetto}">

<details style="margin-bottom:15px;">
  <summary class="summary-arrow">
      <span class="arrow" style="transition:0.2s;">▶</span> Checklist
  </summary>

  <br>

  <div style="font-size:16px; line-height:1.6; margin-left:20px;">
      Scadenza assicurazione<br>
      Scadenza revisione<br>
      Scadenza bollo<br>
      Vignetta svizzera<br>
       Licenza<br>
  </div>

</details>

<pre>
📝 Segnalazioni
</pre>

<textarea name="note" rows="8" cols="40">{note_correnti}</textarea><br><br>

<button type="submit">💾 Salva</button>
</form>

<pre>
────────────────────────────────────
</pre>
"""

# ---------------------------------------------------------
# AVVIO SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
