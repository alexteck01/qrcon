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
    return ora

# ---------------------------------------------------------
# SALVA NOTE
# ---------------------------------------------------------
@app.route("/salva_note", methods=["POST"])
def salva_note():
    id_oggetto = request.form.get("id")
    testo_note = request.form.get("note", "")

    salva_su_supabase(id_oggetto, {"note": testo_note})

    return f"""
<pre>
Note salvate correttamente per {id_oggetto}.
<a href="/scan?id={id_oggetto}&noevent=1">⬅ Torna indietro</a>
</pre>
"""

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
@app.route("/")
def home():
    return "QRCON server attivo"

# ---------------------------------------------------------
# SCAN → registra IN/OUT
# ---------------------------------------------------------
@app.route("/scan")
def scan():
    id_oggetto = request.args.get("id")
    noevent = request.args.get("noevent")

    storico = carica_da_supabase(id_oggetto)

    # Se noevent=1 → NON registriamo IN/OUT
    if noevent == "1":
        if storico["eventi"]:
            evento, ora = storico["eventi"][-1]
        else:
            evento, ora = "Nessun evento", ""
    else:
        # registra IN/OUT normalmente
        evento = determina_evento(storico)
        ora = registra_evento(id_oggetto, storico, evento)

    eventi = storico["eventi"]
    note_correnti = storico["note"]
    storico_testo = "<br>".join([f"{e[0]} – {e[1]}" for e in eventi])

    return f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">

<div class="container">
    <div class="box">
        <div class="title">Ale</div>
        Evento registrato: <b>{evento}</b><br>
        {ora}<br>
    </div>
</div>

<form action="/salva_note" method="POST">
    <input type="hidden" name="id" value="{id_oggetto}">
    
<div class= "container"> 
      <span class="arrow" style="transition:0.2s;">▶</span> Checklist
  <br>
      Libretto<br>
      Licenza<br>
      assicurazione<br>
      Vignetta svizzera<br>
</div>

    <div class="container">
        <div class="box">
            <div class="title">📝Segnalazioni</div>
            <textarea name="note" rows="10" style="width:85%;">{note_correnti}</textarea>
        </div>
    </div>

    <div class="container">
        <button type="submit">Salva</button>
    </div>
</form>
<div class="container">
    <div class="box">
        <div class="title">📜Storico</div>
        {storico_testo}
    </div>
</div>
"""

# ---------------------------------------------------------
# QRCON → mostra storico e note
# ---------------------------------------------------------
@app.route("/qrcon")
def qrcon():
    id_oggetto = request.args.get("id")

    storico = carica_da_supabase(id_oggetto)
    eventi = storico["eventi"]
    note_correnti = storico["note"]

    storico_testo = "<br>".join([f"{e[0]} – {e[1]}" for e in eventi])

    return f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">

<div class="container">
    <div class="box">
        <div class="title">Storico</div>
        {storico_testo}
    </div>
</div>

<form action="/salva_note" method="POST">
    <input type="hidden" name="id" value="{id_oggetto}">

    <div class="container">
        <div class="box">
            <div class="title">Checklist</div>
            assicurazione: 12/1/27<br>
            Licenza - OK<br>
            Libretto - OK<br>
            Libretto: OK<br>
            Vignetta svizzera: 31/1/27<br>
        </div>
    </div>

    <div class="container">
        <div class="box">
            <div class="title">Segnalazioni</div>
            <textarea name="note" rows="8">{note_correnti}</textarea>
        </div>
    </div>

    <div class="container">
        <button type="submit">Salva</button>
    </div>
</form>
"""

# ---------------------------------------------------------
# AVVIO SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
