import json
import requests
from flask import Flask, request
from datetime import datetime
import pytz

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
    roma = pytz.timezone("Europe/Rome")
    ora = datetime.now(roma).strftime("%d/%m/%Y – %H:%M:%S")
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
@app.route("/")
def home():
    return "QRCON server attivo"
@app.route("/qrcon")
def qrcon():
    id_oggetto = request.args.get("id")

    storico = carica_da_supabase(id_oggetto)
    eventi = storico["eventi"]
    note_correnti = storico["note"]

    # testo storico formattato
    storico_testo = "\n".join([f"{e[0]} – {e[1]}" for e in eventi])

    # determina IN/OUT
    evento = determina_evento(storico)

    # registra evento
    ora = registra_evento(id_oggetto, storico, evento)

    return f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">


<style>
    body {{
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
        background: #f2f2f2;
        width: 100%;
    }}
    .container {{
        width: 100%;
        padding: 16px;
        box-sizing: border-box;
    }}

    .box {{
        background: white;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 18px;
        width: 100%;
        box-sizing: border-box;
        font-size: 18px;
        line-height: 1.4;
    }}

    .title {{
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 10px;
    }}

    textarea {{
        width: 100%;
        box-sizing: border-box;
        font-size: 17px;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #ccc;
        resize: vertical;
    }}

    button {{
        width: 100%;
        padding: 16px;
        font-size: 20px;
        background: #007aff;
        color: white;
        border: none;
        border-radius: 10px;
        cursor: pointer;
        font-weight: 600;
    }}

    button:active {{
        background: #0051a8;
    }}
</style>
<div class="container">
    <div class="box">
        <div class="title">QRCON</div>
        🟢 Evento registrato<br>
        {ora}
    </div>

    <div class="box">
        <div class="title">📜 Storico</div>
        {storico_testo.replace("\\n", "<br>")}
    </div>

    <form action="/salva_note" method="POST">
        <input type="hidden" name="id" value="{id_oggetto}">

        <div class="box">
            <div class="title">Checklist</div>
            Scadenza assicurazione<br>
            Scadenza revisione<br>
            Scadenza bollo<br>
            Vignetta svizzera<br>
            Licenza - OK<br>
            Libretto - OK<br>
        </div>

        <div class="box">
            <div class="title">Segnalazioni</div>
            <textarea name="note" rows="8">{note_correnti}</textarea>
        </div>

        <button type="submit">💾 Salva</button>
    </form>
</div>
"""

# ---------------------------------------------------------
# AVVIO SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
