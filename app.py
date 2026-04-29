import os
import smtplib
from email.message import EmailMessage
from flask import Flask, jsonify, request
from mssql_python import connect

app = Flask(__name__)

def enviar_correo_alerta(asunto, mensaje, destino):
    email_remitente = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")

    msg = EmailMessage()
    msg.set_content(mensaje)
    msg['Subject'] = asunto
    msg['From'] = email_remitente
    msg['To'] = destino

    try:
        # Usamos el puerto 587 que suele estar abierto en Render
        # Agregamos un timeout explícito para que no se quede colgado
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.set_debuglevel(1) # Esto imprimirá info en tus logs de Render
        server.starttls() # Cifrado obligatorio para el puerto 587
        server.login(email_remitente, email_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"LOG DE ERROR SMTP: {str(e)}")
        raise e

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    port = os.getenv("DB_PORT", "1433")

    if not server:
        raise ValueError("Falta DB_SERVER")
    if not database:
        raise ValueError("Falta DB_DATABASE")
    if not username:
        raise ValueError("Falta DB_USERNAME")
    if not password:
        raise ValueError("Falta DB_PASSWORD")

    connection_string = (
        f"Server=tcp:{server},{port};"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Authentication=SqlPassword;"
    )

    return connect(connection_string)


@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API Flask funcionando correctamente en Render"
    })


@app.route("/test-db")
def test_db():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE()")
        row = cursor.fetchone()

        return jsonify({
            "success": True,
            "server_date": str(row[0])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# 🔥 ENDPOINT CORREGIDO
@app.route("/productos")
def listar_productos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ✅ AQUÍ ESTÁ LA CLAVE (agregamos stock y version)
        cursor.execute("""
            SELECT TOP 20 
                id, 
                nombre, 
                precio, 
                stock, 
                version, 
                imagen_url
            FROM productos
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "nombre": row[1],
                "precio": float(row[2]) if row[2] is not None else 0,
                "stock": int(row[3]) if row[3] is not None else 0,
                "version": str(row[4]) if row[4] is not None else "",
                "imagen_url": row[5],
            })

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error al consultar productos",
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()




@app.route("/enviar-alerta", methods=["POST"])
def enviar_alerta():
    try:
        data = request.get_json(force=True)
        destino = data.get("to")
        asunto = data.get("subject")
        mensaje = data.get("message")

        if not all([destino, asunto, mensaje]):
            return jsonify({"success": False, "error": "Faltan datos"}), 400

        enviar_correo_alerta(asunto, mensaje, destino)
        
        return jsonify({"success": True, "message": "Correo enviado con Gmail"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))