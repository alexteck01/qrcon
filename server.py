import requests
from flask import Flask, request, redirect, render_template_string
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- CONFIGURAZIONE ---
SUPABASE_URL = "https://uqcjspndheidokixwrqb.supabase.co/rest/v1/storico"
SUPABASE_KEY = "sb_publishable_5TO_BNQMyBjG_Om8uKgkmA_wuOlEjxS"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def get_ora_italia():
    return datetime.now(pytz.timezone("Europe/Rome"))

def ottieni_dati(id_oggetto):
    res = requests.get(f"{SUPABASE_URL}?id_oggetto=eq.{id_oggetto}&order=created_at.desc", headers=HEADERS).json()
    eventi = [r['dati'] for r in res if 'evento' in r.get('dati', {})]
    note = next((r['dati']['note'] for r in res if 'note' in r.get('dati', {})), "")
    return eventi, note

@app.route("/scan")
def scan():
    id_oggetto = request.args.get("id")
    if not id_oggetto: return "ID mancante", 400

    eventi, note = ottieni_dati(id_oggetto)
    ora_attuale = get_ora_italia()
    
    # --- LOGICA AUTOMATICA CON BLOCCO DUPLICATI (10 SECONDI) ---
    registra = True
    if eventi:
        # Recupera l'ora dell'ultimo evento
        ultimo_ts = datetime.strptime(eventi[0]['timestamp'], "%d/%m/%Y – %H:%M:%S")
        ultimo_ts = pytz.timezone("Europe/Rome").localize(ultimo_ts)
        # Se sono passati meno di 10 secondi, NON registrare (è un pre-caricamento del browser)
        if (ora_attuale - ultimo_ts).total_seconds() < 10:
            registra = False

    if registra:
        nuovo_tipo = "OUT" if (eventi and eventi[0].get("evento") == "IN") else "IN"
        payload = {"id_oggetto": id_oggetto, "dati": {"evento": nuovo_tipo, "timestamp": ora_attuale.strftime("%d/%m/%Y – %H:%M:%S")}}
        requests.post(SUPABASE_URL, headers=HEADERS, json=payload)
        eventi, _ = ottieni_dati(id_oggetto) # Aggiorna la lista dopo l'inserimento

    storico_html = "".join([f"<div style='border-bottom:1px solid #eee; padding:5px 0;'><b>{e['evento']}</b> - {e['timestamp']}</div>" for e in eventi[:10]])

    return render_template_string(f"""
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f4f4f9; }}
            .box {{ background: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            textarea {{ width: 100%; box-sizing: border-box; padding: 10px; margin-top: 10px; border-radius: 5px; border: 1px solid #ccc; }}
            button {{ background: #28a745; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; margin-top: 10px; font-weight: bold; }}
        </style>

        <div class="box">
            <h3>📍 Ultimo Movimento</h3>
            <p style="font-size: 1.5rem; color: #007bff; margin: 0;"><b>{{{{evento_attuale}}}}</b></p>
            <small>{{{{ora_attuale}}}}</small>
        </div>

        <div class="box">
            <h3>📜 Storico</h3>
            {storico_html}
        </div>

        <div class="box">
            <h3>📝 Note</h3>
            <form action="/salva_note" method="POST">
                <input type="hidden" name="id" value="{id_oggetto}">
                <textarea name="note" rows="4">{note}</textarea>
                <button type="submit">SALVA NOTE</button>
            </form>
        </div>
    """, evento_attuale=eventi[0]['evento'] if eventi else "Nessuno", ora_attuale=eventi[0]['timestamp'] if eventi else "")

@app.route("/salva_note", methods=["POST"])
def salva_note():
    id_oggetto = request.form.get("id")
    testo = request.form.get("note")
    payload = {"id_oggetto": id_oggetto, "dati": {"note": testo}}
    requests.post(SUPABASE_URL, headers=HEADERS, json=payload)
    return redirect(f"/scan?id={id_oggetto}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
