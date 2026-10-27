
import os, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","CHAVE-ALTERAR-EM-PRODUCAO")
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,"site.db"); UP=os.path.join(BASE,"uploads")
os.makedirs(UP,exist_ok=True)

DEFAULT={
"nome":"Associação Comunitária Suassuna","slogan":"Unidos pela nossa comunidade.",
"cnpj":"65.616.761/0001-18",
"endereco":"R DO GIRASSOL COM. CDOR. EDSON OLIVEIRA SILVA, nº 328, AP 007 BL. D, Muribequinha, Jaboatão dos Guararapes-PE, CEP 54.353-355",
"telefone":"(81) 9720-2209","email":"associacaohabitacionalsuassuna@gmail.com",
"instagram":"","facebook":"","whatsapp":"558197202209",
"historia":"A Associação Comunitária Suassuna atua para fortalecer a participação comunitária, a união dos moradores e o desenvolvimento de iniciativas de interesse coletivo."
}
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 c=conn(); c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY,title TEXT,summary TEXT,content TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,title TEXT,event_date TEXT,location TEXT,description TEXT);
CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY,title TEXT,filename TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);""")
 if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone():
  c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",("admin",generate_password_hash("1234")))
 for k,v in DEFAULT.items(): c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)",(k,v))
 c.commit(); c.close()
def site():
 c=conn(); r={x["key"]:x["value"] for x in c.execute("SELECT * FROM settings")}; c.close(); return r
@app.context_processor
def context(): return {"site":site()}
def auth(f):
 @wraps(f)
 def w(*a,**kw):
  if not session.get("admin"): return redirect(url_for("login"))
  return f(*a,**kw)
 return w

@app.route("/")
def home():
 c=conn(); n=c.execute("SELECT * FROM news ORDER BY id DESC LIMIT 3").fetchall(); e=c.execute("SELECT * FROM events ORDER BY id LIMIT 3").fetchall(); g=c.execute("SELECT * FROM gallery ORDER BY id DESC LIMIT 6").fetchall(); c.close()
 return render_template("home.html",news=n,events=e,gallery=g)
@app.route("/<page>")
def public(page):
 allowed={"associacao":"A Associação","projetos":"Projetos","noticias":"Notícias","eventos":"Eventos","galeria":"Galeria","documentos":"Documentos","contato":"Contato"}
 if page not in allowed: return redirect(url_for("home"))
 data={}
 c=conn()
 if page=="noticias": data["items"]=c.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
 if page=="eventos": data["items"]=c.execute("SELECT * FROM events ORDER BY event_date").fetchall()
 if page=="galeria": data["items"]=c.execute("SELECT * FROM gallery ORDER BY id DESC").fetchall()
 c.close(); return render_template("page.html",title=allowed[page],page=page,**data)

@app.route("/uploads/<filename>")
def uploads(filename): return send_from_directory(UP,filename)

@app.route("/admin/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  c=conn(); u=c.execute("SELECT * FROM users WHERE username=?",(request.form["username"],)).fetchone(); c.close()
  if u and check_password_hash(u["password_hash"],request.form["password"]):
   session["admin"]=u["id"]; return redirect(url_for("dashboard"))
  flash("Usuário ou senha inválidos.","error")
 return render_template("admin/login.html")
@app.route("/admin/sair")
def logout(): session.clear(); return redirect(url_for("login"))
@app.route("/admin")
@auth
def dashboard():
 c=conn(); counts=[c.execute("SELECT COUNT(*) FROM "+x).fetchone()[0] for x in ("news","events","gallery")]; c.close()
 return render_template("admin/dashboard.html",counts=counts)
@app.route("/admin/configuracoes",methods=["GET","POST"])
@auth
def settings_admin():
 if request.method=="POST":
  c=conn()
  for k in DEFAULT: c.execute("UPDATE settings SET value=? WHERE key=?",(request.form.get(k,"").strip(),k))
  c.commit(); c.close(); flash("Informações atualizadas.","success")
 return render_template("admin/settings.html")
@app.route("/admin/senha",methods=["GET","POST"])
@auth
def password():
 if request.method=="POST":
  c=conn(); u=c.execute("SELECT * FROM users WHERE id=?",(session["admin"],)).fetchone()
  if not check_password_hash(u["password_hash"],request.form["current"]): flash("Senha atual incorreta.","error")
  elif len(request.form["new"])<6: flash("Use pelo menos 6 caracteres.","error")
  elif request.form["new"]!=request.form["confirm"]: flash("As novas senhas não conferem.","error")
  else: c.execute("UPDATE users SET password_hash=? WHERE id=?",(generate_password_hash(request.form["new"]),u["id"])); c.commit(); flash("Senha alterada.","success")
  c.close()
 return render_template("admin/password.html")

@app.route("/admin/noticias",methods=["GET","POST"])
@auth
def news_admin():
 c=conn()
 if request.method=="POST":
  c.execute("INSERT INTO news(title,summary,content) VALUES(?,?,?)",(request.form["title"],request.form["summary"],request.form["content"])); c.commit(); flash("Notícia publicada.","success")
 items=c.execute("SELECT * FROM news ORDER BY id DESC").fetchall(); c.close()
 return render_template("admin/list.html",kind="Notícias",items=items,action="news")
@app.route("/admin/noticias/excluir/<int:i>",methods=["POST"])
@auth
def news_delete(i):
 c=conn(); c.execute("DELETE FROM news WHERE id=?",(i,)); c.commit(); c.close(); return redirect(url_for("news_admin"))

@app.route("/admin/eventos",methods=["GET","POST"])
@auth
def events_admin():
 c=conn()
 if request.method=="POST":
  c.execute("INSERT INTO events(title,event_date,location,description) VALUES(?,?,?,?)",(request.form["title"],request.form["date"],request.form["location"],request.form["description"])); c.commit(); flash("Evento cadastrado.","success")
 items=c.execute("SELECT * FROM events ORDER BY event_date").fetchall(); c.close()
 return render_template("admin/list.html",kind="Eventos",items=items,action="events")
@app.route("/admin/eventos/excluir/<int:i>",methods=["POST"])
@auth
def event_delete(i):
 c=conn(); c.execute("DELETE FROM events WHERE id=?",(i,)); c.commit(); c.close(); return redirect(url_for("events_admin"))

@app.route("/admin/galeria",methods=["GET","POST"])
@auth
def gallery_admin():
 c=conn()
 if request.method=="POST":
  f=request.files.get("photo")
  if f and f.filename:
   ext=os.path.splitext(f.filename)[1].lower()
   if ext in {".jpg",".jpeg",".png",".webp"}:
    name=secure_filename(os.urandom(8).hex()+"_"+f.filename); f.save(os.path.join(UP,name)); c.execute("INSERT INTO gallery(title,filename) VALUES(?,?)",(request.form["title"],name)); c.commit(); flash("Foto adicionada.","success")
   else: flash("Formato inválido.","error")
 items=c.execute("SELECT * FROM gallery ORDER BY id DESC").fetchall(); c.close()
 return render_template("admin/gallery.html",items=items)
@app.route("/admin/galeria/excluir/<int:i>",methods=["POST"])
@auth
def gallery_delete(i):
 c=conn(); x=c.execute("SELECT filename FROM gallery WHERE id=?",(i,)).fetchone()
 if x:
  p=os.path.join(UP,x["filename"])
  if os.path.exists(p): os.remove(p)
  c.execute("DELETE FROM gallery WHERE id=?",(i,)); c.commit()
 c.close(); return redirect(url_for("gallery_admin"))

init()
if __name__=="__main__": app.run(debug=True)
