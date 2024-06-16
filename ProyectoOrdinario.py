import mysql.connector
import random
import requests
from datetime import datetime, timedelta

def conectar_bd():
    config = {
        'user': 'root',
        'password': '',
        'host': '127.0.0.1',
        'database': 'ordinario'
    }
    try:
        conn = mysql.connector.connect(**config)
        print("¡Conexión exitosa!")
        return conn
    except mysql.connector.Error as err:
        print(f"Error de conexión: {err}")
        return None
conexion = conectar_bd()

# Configuración de SMSMasivos
SMSMASIVOS_API_KEY = '7d39156e61a13d0ce7ee4c5930123b08531e2b9c'
SMSMASIVOS_API_URL = 'https://api.smsmasivos.com.mx/sms/send'

def enviar_sms(numero_telefono, mensaje):
    try:
        data = {
            'message': mensaje,
            'numbers': numero_telefono,
            'country_code': '52',  # Código de país de México
        }
        headers = {
            'apikey': SMSMASIVOS_API_KEY,
        }
        response = requests.post(url=SMSMASIVOS_API_URL, data=data, headers=headers)
        if response.status_code == 200:
            print(f"Mensaje enviado a {numero_telefono}.")
        else:
            print(f"Error al enviar el mensaje: {response.text}")
    except Exception as e:
        print(f"Error al enviar el mensaje: {e}")

def loguearse(cursor):
    nombre = input("Ingresa tu nombre: ")
    contrasena = input("Ingresa tu contraseña: ")
    query = "SELECT * FROM usuarios WHERE nombre = %s AND contrasena = %s"
    cursor.execute(query, (nombre, contrasena))
    usuario = cursor.fetchone() #se obtiene el resultado de la consulta
    if usuario:  # Aqui si encontramos el user,se imprime el mensaje y la información del usuario
        print("¡Login exitoso!")
        return usuario
    else:
        print("Nombre o contraseña incorrectos.")
        return None

def crear_operacion(cursor, conn, usuario): # ocupamos el cursor de base de datos, la conexión a BD "CONN", y al usuario logeado ya.
    tipo_operacion = input("Ingresa el tipo de operación: ")
    descripcion = input("Ingresa la descripción de la operación: ")
    query = "INSERT INTO Operaciones_Bancarias (tipo_operacion, descripcion, id_usuario, fecha_hora_inicio, estatus) VALUES (%s, %s, %s, NOW(), 'PENDIENTE')" #aqui agregamos los valores y el tiempo NOW y por defecto el 'pendiente'
    cursor.execute(query, (tipo_operacion, descripcion, usuario[0])) #agregamos el tip, descripcion y el id del usuario 
    conn.commit() #se confirma la transaccion
    print("¡Operación creada exitosamente!")

def agregar_numero_telefonico(cursor, conn, usuario):
    numero_telefonico = input("Ingresa tu número de teléfono: ")
    query = "UPDATE usuarios SET numero_telefonico = %s WHERE id_usuario = %s" #actualizamos la base
    cursor.execute(query, (numero_telefonico, usuario[0])) #aqui pasamos el numero y el id del usuario logeado el campo[0] de la tabla es id
    conn.commit()#se confirma la transaccion
    print("¡Número telefónico agregado exitosamente!")

def generar_token(cursor, conn, usuario):
     # Generamos un numero entero aleatorio y lo pasamos a CADENA DE TEXTO con el STR, el token es de 6 digitos
    token = str(random.randint(100000, 999999))
    query = "UPDATE usuarios SET token = %s, fecha_generacion_token = NOW() WHERE id_usuario = %s"#ponemos la fecha NOW, el token generado donde el id_usuario sea al logeado
    cursor.execute(query, (token, usuario[0]))
    conn.commit()#se confirma la transaccion
    print("Token generado y enviado al número de teléfono registrado.")
    if usuario[3]:  # Nos aseguramos de que el número de teléfono está presente
        enviar_sms(usuario[3], f"Tu token es: {token}") #aqui llamamos la funcion de enviar el sms ya echa
    else:
        print("No se ha registrado un número de teléfono para este usuario.")
        
def validar_token(cursor, conn, usuario):
    token = input("Ingresa el token que se envió a tu teléfono: ")
    #aqui obtenemos los datos del token del usuario.
    query = "SELECT token, fecha_generacion_token, validez_token_minutos FROM usuarios WHERE id_usuario = %s"
    cursor.execute(query, (usuario[0],))
    resultado = cursor.fetchone()  # Pasamos la info. que es token, fecha de generación y validez en minutos.
    if resultado: #si hubo un resulatado
        token_bd, fecha_generacion_token, validez_token_minutos = resultado  # Extramos por aparte los resultados de la consulta.
            # Vemos si el token de la BD coincide con el token ingresado.
        if token_bd and token_bd == token:
            # Aqui calculamos la fecha y hora en que el token expira, sumando la duración de validez (en minutos) a la fecha y hora en que el token fue generado.
            fecha_expiracion = fecha_generacion_token + timedelta(minutes=validez_token_minutos)
            
            # comparamos si la hora de ahora es menor o igual a la fecha de expiracion.
            if datetime.now() <= fecha_expiracion:
                # Si el token es válido, actualiza el estatus de las operaciones bancarias del usuario a 'VALIDADO' y registra la fecha y hora de validación.
                print("¡Token válido!")
                query = "UPDATE Operaciones_Bancarias SET estatus = 'VALIDADO', fecha_hora_validacion = NOW() WHERE id_usuario = %s AND estatus = 'PENDIENTE'"
                cursor.execute(query, (usuario[0],))
                conn.commit()
            else:
                # Si el token ha expirado, cancela la operación bancaria y actualiza el estatus a 'CANCELADO' con la fecha y hora de validación.
                print("El token ha expirado. La operación se ha cancelado.")
                query = "UPDATE Operaciones_Bancarias SET estatus = 'CANCELADO', fecha_hora_validacion = NOW() WHERE id_usuario = %s AND estatus = 'PENDIENTE'"
                cursor.execute(query, (usuario[0],))
                conn.commit()
        else:
            # Si el token es incorrecto, damos una segunda oportunidad
            print("Token incorrecto. Intenta nuevamente.")
            token = input("Ingresa el token que se envió a tu teléfono: ")
            
            # Vuelve a comprobar si el token ingresado por el usuario es correcto y no ha expirado.
            if token_bd and token_bd == token:
                fecha_expiracion = fecha_generacion_token + timedelta(minutes=validez_token_minutos)
                if datetime.now() <= fecha_expiracion:
                    # Hacemos lo mismo que arriba
                    print("¡Token válido!")
                    query = "UPDATE Operaciones_Bancarias SET estatus = 'VALIDADO', fecha_hora_validacion = NOW() WHERE id_usuario = %s AND estatus = 'PENDIENTE'"
                    cursor.execute(query, (usuario[0],))
                    conn.commit()
                else:
                    # Si el token ha expirado, cancela la operación bancaria y actualiza el estatus a 'CANCELADO' con la fecha y hora de validación.
                    print("El token ha expirado. La operación se ha cancelado.")
                    query = "UPDATE Operaciones_Bancarias SET estatus = 'CANCELADO', fecha_hora_validacion = NOW() WHERE id_usuario = %s AND estatus = 'PENDIENTE'"
                    cursor.execute(query, (usuario[0],))
                    conn.commit()
            else:
                # Si el token es incorrecto por segunda vez, cancela la operación bancaria y actualiza el estatus a 'CANCELADO' con la fecha y hora de validación.
                print("Token incorrecto. La operación se ha cancelado.")
                query = "UPDATE Operaciones_Bancarias SET estatus = 'CANCELADO', fecha_hora_validacion = NOW() WHERE id_usuario = %s AND estatus = 'PENDIENTE'"
                cursor.execute(query, (usuario[0],))
                conn.commit()



def mostrar_menu():
    print("\n--- Menú para operaciones ---")
    print("1. Logearse al sistema")
    print("2. Crear una operación")
    print("3. Agregar Número Telefónico")
    print("4. Generar Token")
    print("5. Validar Token")
    print("6. Salir")

usuario_logueado = None #aqui ponemos la variable por defecto que ningun usuario a ingresado
cursor = conexion.cursor()
while True: #si hay una conexion con la base de datos comienza el bucle
    mostrar_menu()
    opcion = input("Elige una opción: ")

    if opcion == "1":
        usuario_logueado = loguearse(cursor) #Aqui si se inicia sesion bien, la información del usuario se asigna a la variable usuario_logueado.
    elif opcion == "2" and usuario_logueado:
        crear_operacion(cursor, conexion, usuario_logueado)
    elif opcion == "3" and usuario_logueado:
        agregar_numero_telefonico(cursor, conexion, usuario_logueado)
    elif opcion == "4" and usuario_logueado:
        generar_token(cursor, conexion, usuario_logueado)
    elif opcion == "5" and usuario_logueado:
        validar_token(cursor, conexion, usuario_logueado)
    elif opcion == "6":
        print("Saliendo del sistema :)")
        break
    else:
        print("Opción no válida o requieres estar logueado.")

cursor.close()
conexion.close()