import requests
from flask import Flask, request, redirect, render_template_string
from datetime import datetime
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
    try:
        res = requests.get(f"{SUPABASE_URL}?id_oggetto=eq.{id_oggetto}&order=created_at.desc", headers=HEADERS).json()
        eventi = [r['dati'] for r in res if 'evento' in r.get('dati', {})]
        note = next((r['dati']['note'] for r in res if 'note' in r.get('dati', {})), "")
        return eventi, note
    except:
        return [], ""

@app.route("/scan")
def scan():
    id_oggetto = request.args.get("id")
    # Aggiungiamo questo parametro per capire se stiamo solo visualizzando (dopo il salvataggio note)
    solo_visualizza = request.args.get("noevent") 
    
    if not id_oggetto: return "ID mancante", 400

    eventi, note = ottieni_dati(id_oggetto)
    ora_attuale = get_ora_italia()
    
    # --- LOGICA AUTOMATICA (Solo se noevent NON è presente) ---
    registra = False
    if not solo_visualizza:
        registra = True
        if eventi:
            ultimo_ts = datetime.strptime(eventi[0]['timestamp'], "%d/%m/%Y – %H:%M:%S")
            ultimo_ts = pytz.timezone("Europe/Rome").localize(ultimo_ts)
            # Se sono passati meno di 10 secondi, è un duplicato
            if (ora_attuale - ultimo_ts).total_seconds() < 10:
                registra = False

    if registra:
        nuovo_tipo = "OUT" if (eventi and eventi[0].get("evento") == "IN") else "IN"
        payload = {"id_oggetto": id_oggetto, "dati": {"evento": nuovo_tipo, "timestamp": ora_attuale.strftime("%d/%m/%Y – %H:%M:%S")}}
        requests.post(SUPABASE_URL, headers=HEADERS, json=payload)
        eventi, _ = ottieni_dati(id_oggetto)

    storico_html = "".join([f"<div style='border-bottom:1px solid #eee; padding:5px 0;'><b>{e['evento']}</b> - {e['timestamp']}</div>" for e in eventi[:10]])

    return render_template_string(f"""
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/style.css">
        
        <div class="box center">
            <h3 style="margin:0;">📍 Stato Attuale</h3>
            <p class="status-val"><b>{{{{evento_attuale}}}}</b></p>
            <small>{{{{ora_attuale}}}}</small>
        </div>

       # ... dentro la funzione scan() ...

       # Creiamo le righe dello storico una sotto l'altra
       storico_testo = "".join([
           f'<div class="storico-item"><b>{e["evento"]}</b> <span>{e["timestamp"]}</span></div>' 
           for e in eventi[:10]
])

       return render_template_string
       <div class="container">
           <div class="box">
               <div class="title">📜 Storico</div>
               <div class="storico-list">
                   {storico_testo}
               </div>
           </div>
       </div>

        <div class="box">
            <h3 style="margin-top:0;">📝 Note</h3>
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
    # Fondamentale: aggiungiamo &noevent=1 per non far scattare il cambio IN/OUT
    return redirect(f"/scan?id={id_oggetto}&noevent=1")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
