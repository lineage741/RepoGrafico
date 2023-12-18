from helper.openai_api import text_complition
from helper.twilio_api import send_message
from datetime import datetime
#from flask import render_template 

from flask import Flask, request, render_template,jsonify, redirect, url_for
from dotenv import load_dotenv
import os
#import mysql.connector
import pyodbc
#import matplotlib.pyplot as plt
import plotly.express as px

load_dotenv()

app = Flask(__name__, static_url_path='/static')

# Archivo para almacenar los mensajes en tiempo real
CHAT_LOG_FILE = "chat_log.txt"

# Configuración de la base de datos SQL Server
DB_SERVER = os.getenv("DB_SERVER")
#DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# conexión para SQL Server
DB_CONNECTION_STRING = f"DRIVER={{SQL Server}};SERVER={DB_SERVER};UID={DB_USER};DATABASE={DB_DATABASE};Trusted_Connection=yes"

def create_connection():
    return pyodbc.connect(DB_CONNECTION_STRING)

@app.route('/', methods=['GET', 'POST'])
def real_time_chart():
    try:
        # Conectar a la base de datos
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()

        #Verificar si se ha enviado un formulario con la cantidad seleccionada
        if request.method == 'POST':
            cantidad_seleccionada = int(request.form['cantidad'])
            filtro_seleccionado = request.form['filtro']
        else:
            # Valor predeterminado al cargar la página por primera vez
            cantidad_seleccionada = 16
            filtro_seleccionado = 'producto'

        # Consulta SQL para obtener los productos más vendidos (usando la cantidad seleccionada)
        if filtro_seleccionado == 'categoria':
            query = """
            SELECT c.nombre AS categoria, SUM(dv.cantidad) as total_vendido
            FROM categoria c
            JOIN producto p ON c.id_categoria = p.id_categoria
            LEFT JOIN detalleventa dv ON p.id_producto = dv.id_producto
            GROUP BY c.nombre
            ORDER BY total_vendido DESC;
            """
        elif filtro_seleccionado == 'marca':
            query = """
            SELECT p.marca as filtro, SUM(dv.cantidad) as total_vendido
            FROM producto p
            JOIN detalleventa dv ON p.id_producto = dv.id_producto
            GROUP BY p.marca
            ORDER BY total_vendido DESC
            """
        else:
            query = f"""
            SELECT TOP {cantidad_seleccionada} p.nombre, SUM(dv.cantidad) as total_vendido,p.marca, c.nombre
            FROM producto p
            JOIN detalleventa dv ON p.id_producto = dv.id_producto
            join categoria c on p.id_categoria = c.id_categoria
            GROUP BY p.nombre,p.marca, c.nombre
            ORDER BY total_vendido DESC
            """
        cursor.execute(query)
        result = cursor.fetchall()

        # Extraer datos de la consulta
        labels = [row[0] for row in result]  # Nombres de productos
        data = [row[1] for row in result]    # Cantidad vendida de cada producto

    finally:
        # Cerrar la conexión a la base de datos
        cursor.close()
        connection.close()

    # Crear un gráfico interactivo con Plotly Express
    fig = px.bar(x=labels, y=data, labels={'y': 'Cantidad Vendida'}, title=f'Ventas por {filtro_seleccionado.capitalize()}',
                 text=data, height=800, range_y=[0,5000],
                 category_orders={"x": labels},
                 color=labels)

    # Configuración adicional para el diseño del gráfico
    fig.update_traces(texttemplate='%{text}', textposition='outside')

    # Ajustar la separación entre las barras
    fig.update_layout(bargap=0.5)

    # Configurar el eje y con límite máximo de 1500
    fig.update_yaxes(range=[0, 5000])

    # Inclinar los nombres de los productos de manera vertical
    fig.update_layout(xaxis_tickangle=-45)

    # Ajustar el tamaño del eje y
    fig.update_yaxes(tickvals=list(range(0, 5000, 200)))

    # Modificar la información que se muestra al pasar el puntero
    hovertemplate_custom = '<b>%{x}</b><br>Total Vendido: %{y}'
    fig.update_traces(hovertemplate=hovertemplate_custom)

    # Modificar el título de la leyenda
    fig.update_layout(legend_title_text=f' {filtro_seleccionado.capitalize()}')

    # Convertir el gráfico a HTML y devolverlo como respuesta
    chart_html = fig.to_html(full_html=False)

    # Mostrar el gráfico en el navegador
    return render_template('real_time_chart.html', plot=chart_html, filtro_seleccionado=filtro_seleccionado)

@app.route('/ventas_diarias', methods=['GET', 'POST'])
def ventas_diarias_chart():
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()

        if request.method == 'POST':
            # Aquí puedes agregar lógica para manejar los filtros si es necesario
            #cantidad_seleccionada = int(request.form['cantidad'])
            filtro_seleccionado = request.form['filtro']

            if filtro_seleccionado == 'ventas_diarias':
                return redirect(url_for('ventas_diarias_chart'))
            elif filtro_seleccionado == 'ventas_mensuales':
                return redirect(url_for('ventas_mensuales_chart'))

        query = """
        SELECT fecha, SUM(dv.cantidad) AS total_venta_por_dia
        FROM notaventa n
        INNER JOIN detalleventa dv ON dv.id_venta = n.id_venta
        GROUP BY fecha
        ORDER BY fecha;
        """
        cursor.execute(query)
        result = cursor.fetchall()

        labels = [row[0] for row in result]  # Fechas
        data = [row[1] for row in result]    # Cantidad vendida por día

    finally:
        cursor.close()
        connection.close()

    # Crear un gráfico de línea para ventas diarias
    fig = px.line(x=labels, y=data, labels={'y': 'Cantidad Vendida'}, title='Ventas Diarias',
                  line_shape="linear", height=600)

    # Configuración adicional para el diseño del gráfico
    # ...

    chart_html = fig.to_html(full_html=False)
    return render_template('ventas_diarias_chart.html', plot=chart_html)

@app.route('/ventas_mensuales', methods=['GET', 'POST'])
def ventas_mensuales_chart():
    try:
        connection = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = connection.cursor()

        if request.method == 'POST':
            # Aquí puedes agregar lógica para manejar los filtros si es necesario
            pass

        query = """
        SELECT FORMAT(n.fecha, 'yyyy-MM') AS mes, SUM(dv.cantidad) AS total_venta_por_mes
        FROM notaventa n
        INNER JOIN detalleventa dv ON dv.id_venta = n.id_venta
        GROUP BY FORMAT(n.fecha, 'yyyy-MM')
        ORDER BY FORMAT(n.fecha, 'yyyy-MM');
        """
        cursor.execute(query)
        result = cursor.fetchall()

        labels = [row[0] for row in result]  # Meses
        data = [row[1] for row in result]    # Cantidad vendida por mes

    finally:
        cursor.close()
        connection.close()

    # Crear un gráfico de línea para ventas mensuales
    fig = px.line(x=labels, y=data, labels={'y': 'Cantidad Vendida'}, title='Ventas Mensuales',
                  line_shape="linear", height=600)

    # Configuración adicional para el diseño del gráfico
    # ...

    chart_html = fig.to_html(full_html=False)
    return render_template('ventas_mensuales_chart.html', plot=chart_html)

@app.route('/twilio/receiveMessage', methods=['POST'])
def receive_message():
    try:
        # Extraer parámetros entrantes de Twilio
        message_body = request.form['Body']
        sender_id = request.form['From']

        # Obtener respuesta de OpenAI
        result = text_complition(message_body)
        if result['status'] == 1:
            response = result['response']

            # Enviar respuesta a Twilio
            send_message(sender_id, response)

            # Guardar mensajes en el archivo de registro
            log_message = f"{sender_id}: {message_body}\nChatbot: {response}\n\n"
            append_to_chat_log(log_message)

            # Guardar mensajes en la base de datos
            save_to_database(sender_id, message_body, response)

    except Exception as e:
        # Manejar excepciones e imprimir para depuración
        print(f"Error: {str(e)}")

    return 'OK', 200

def append_to_chat_log(message):
    # Obtener la fecha y hora actual
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Añadir el mensaje al archivo de registro con la fecha y hora
    with open(CHAT_LOG_FILE, 'a', encoding='utf-8') as chat_log:
        chat_log.write(f"{timestamp} - {message}")

def save_to_database(sender_id, message_body, response):
    try:
        # Obtener la fecha y hora actual
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Conectar a la base de datos
        with create_connection() as db_connection:
            db_cursor = db_connection.cursor()

            # Insertar el mensaje en la base de datos con la fecha y hora
            insert_query = "INSERT INTO mensajes (sender_id, pregunta, respuesta, fecha_hora) VALUES (?, ?, ?, ?)"
            values = (sender_id, message_body, response, timestamp)
            db_cursor.execute(insert_query, values)
            db_connection.commit()
    except Exception as e:
        # Manejar excepciones e imprimir para depuración
        print(f"Error en la base de datos: {str(e)}")
    finally:
        # Cerrar el cursor y la conexión
        db_cursor.close()

if __name__ == "__main__":
    # Crear el archivo de registro si no existe
    if not os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'w') as chat_log:
            chat_log.write("Chat Log:\n\n")
