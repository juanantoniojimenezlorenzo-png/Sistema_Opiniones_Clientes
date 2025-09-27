import os
import pandas as pd
import pyodbc
import uuid

# -----------------------------
# NORMALIZAR IdProducto
# -----------------------------
def normalizar_idproducto(valor):
    """
    Convierte IdProducto a formato P###:
    - 6  -> P006
    - '6' -> P006
    - 'P006' -> P006
    - 'p6' -> P006
    """
    if pd.isna(valor):
        return None
    v = str(valor).strip().upper()
    if v.startswith('P'):
        num = ''.join([c for c in v if c.isdigit()])
        return f'P{int(num):03d}' if num.isdigit() else v
    else:
        try:
            return f'P{int(v):03d}'
        except:
            return None

# -----------------------------
# EXTRAER DATOS
# -----------------------------
def extraer_datos(rutas_archivos):
    datos = {}
    for nombre, ruta in rutas_archivos.items():
        try:
            df = pd.read_csv(ruta)
            datos[nombre] = df
            print(f" Archivo '{ruta}' extraído correctamente.")
        except Exception as e:
            print(f" Error al leer {ruta}: {e}")
            datos[nombre] = pd.DataFrame()
    return datos

# -----------------------------
# TRANSFORMAR Y VALIDAR DATOS
# -----------------------------

import pandas as pd
import uuid

# -----------------------------
# TRANSFORMAR Y VALIDAR DATOS
# -----------------------------

def normalizar_idcliente(valor):
    """Convierte IdCliente a formato C### o C##."""
    if pd.isna(valor):
        return None
    v = str(valor).strip().upper()
    if v.startswith('C'):
        return v
    try:
        return f'C{int(v)}'
    except:
        return v # Devuelve el valor original si no es un número

def transformar_y_validar(datos_crudos):
    
    # 1. DataFrames base y normalización de IDs
    df_productos = datos_crudos.get('products', pd.DataFrame()).copy()
    df_clientes = datos_crudos.get('clients', pd.DataFrame()).copy()
    df_fuentes = datos_crudos.get('fuente_datos', pd.DataFrame()).copy()
    
    # Normalizar IDs de Maestras
    if not df_productos.empty:
        df_productos['IdProducto'] = df_productos['IdProducto'].apply(normalizar_idproducto)
    if not df_clientes.empty:
        df_clientes['IdCliente'] = df_clientes['IdCliente'].apply(normalizar_idcliente)

    # 2. Preparación de DataFrames de Opiniones
    df_surveys = datos_crudos.get('surveys', pd.DataFrame()).copy()
    df_web = datos_crudos.get('web_reviews', pd.DataFrame()).copy()
    df_social = datos_crudos.get('social_comments', pd.DataFrame()).copy()

    # Función de clasificación para comentarios sociales
    def clasificar_sentimiento(comentario):
        comentario = str(comentario).lower()
        if 'excelente' in comentario or 'perfecto' in comentario or 'me encanta' in comentario or 'gran calidad' in comentario:
            return 'Positiva'
        elif 'mala calidad' in comentario or 'no funciona' in comentario or 'pésima' in comentario or 'insatisfecho' in comentario:
            return 'Negativa'
        return 'Neutra'

    # ESQUEMA DE UNIFICACIÓN
    columnas_finales = ['IdOpinion', 'IdCliente', 'IdProducto', 'Fecha', 'Comentario', 
                        'Puntaje', 'Clasificación', 'IdFuente', 'TipoFuente']

    opiniones_procesadas = []

    # 2.1 Surveys (Encuestas)
    if not df_surveys.empty:
        if 'PuntajeSatisfaccion' in df_surveys.columns:
            df_surveys.rename(columns={'PuntajeSatisfaccion': 'Puntaje'}, inplace=True)
        df = df_surveys.copy()
        df['Puntaje'] = pd.to_numeric(df['Puntaje'], errors='coerce')
        df['IdProducto'] = df['IdProducto'].apply(normalizar_idproducto)
        df['IdCliente'] = df['IdCliente'].apply(normalizar_idcliente)
        df['Clasificación'] = df.get('Clasificación', None)
        df['IdFuente'] = df.get('IdFuente', 'F002')
        df['TipoFuente'] = 'Survey'
        opiniones_procesadas.append(df.reindex(columns=columnas_finales))

    # 2.2 Web Reviews
    if not df_web.empty:
        df = df_web.rename(columns={'IdReview': 'IdOpinion', 'Rating': 'Puntaje'}).copy()
        df['Puntaje'] = pd.to_numeric(df['Puntaje'], errors='coerce')
        df['IdProducto'] = df['IdProducto'].apply(normalizar_idproducto)
        df['IdCliente'] = df['IdCliente'].apply(normalizar_idcliente)
        df['Clasificación'] = df['Puntaje'].apply(lambda x: 'Positiva' if x >= 4 else ('Neutra' if x == 3 else 'Negativa'))
        df['IdFuente'] = df.get('IdFuente', 'F001')
        df['TipoFuente'] = 'Web'
        opiniones_procesadas.append(df.reindex(columns=columnas_finales))

    # 2.3 Social Comments
    if not df_social.empty:
        df = df_social.rename(columns={'IdComment': 'IdOpinion'}).copy()
        df['Puntaje'] = None
        df['IdProducto'] = df['IdProducto'].apply(normalizar_idproducto)
        df['IdCliente'] = df['IdCliente'].apply(normalizar_idcliente)
        df['Clasificación'] = df['Comentario'].apply(clasificar_sentimiento)
        df['IdFuente'] = df.get('IdFuente', 'F005')
        df['TipoFuente'] = 'Red Social'
        opiniones_procesadas.append(df.reindex(columns=columnas_finales))

    # 3. Unificación y Limpieza Final
    if not opiniones_procesadas:
        df_opiniones = pd.DataFrame(columns=columnas_finales)
    else:
        df_opiniones = pd.concat(opiniones_procesadas, ignore_index=True)

    if not df_opiniones.empty:
        # Generar IdOpinion faltantes
        missing_ids = [str(uuid.uuid4()) for _ in range(df_opiniones['IdOpinion'].isna().sum())]
        df_opiniones.loc[df_opiniones['IdOpinion'].isna(), 'IdOpinion'] = missing_ids

        # Convertir fechas
        df_opiniones['Fecha'] = pd.to_datetime(df_opiniones['Fecha'], errors='coerce').dt.date

        # Reemplazar NaN por None
        df_opiniones = df_opiniones.where(pd.notna(df_opiniones), None)

        # Validación de Integridad
        registros_iniciales = len(df_opiniones)
        
        # Filtrar registros críticos
        df_opiniones.dropna(subset=['IdOpinion', 'IdProducto', 'Fecha', 'IdCliente'], inplace=True)

        # Validar IdProducto en productos
        productos_validos = df_productos['IdProducto'].dropna().unique()
        df_opiniones = df_opiniones[df_opiniones['IdProducto'].isin(productos_validos)]

        # Validar IdCliente en clientes
        clientes_validos = df_clientes['IdCliente'].dropna().unique()
        df_opiniones = df_opiniones[df_opiniones['IdCliente'].isin(clientes_validos)]

        # Validar IdFuente en fuentes
        fuentes_validas = df_fuentes['IdFuente'].dropna().unique()
        df_opiniones = df_opiniones[df_opiniones['IdFuente'].isin(fuentes_validas)]

        registros_descartados = registros_iniciales - len(df_opiniones)
        if registros_descartados > 0:
            print(f" {registros_descartados} registros descartados por fallar la validación (FK o Nulos).")

    datos_transformados = {
        'Productos': df_productos,
        'Clientes': df_clientes,
        'Fuentes': df_fuentes,
        'Opiniones': df_opiniones
    }

    print(" Transformación, estandarización y validación completadas.")
    print(f"Total Opiniones preparadas: {len(df_opiniones)}")
    return datos_transformados


# -----------------------------
# LIMPIAR TABLA 
# -----------------------------
def limpiar_tabla(nombre_tabla, conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute(f"DELETE FROM {nombre_tabla};")
        conexion.commit()
        print(f" Tabla '{nombre_tabla}' limpiada exitosamente (DELETE).")
    except Exception as e:
        print(f" Error al limpiar tabla '{nombre_tabla}': {e}")
    finally:
        cursor.close()

# -----------------------------
# CARGA DE DATOS EN SQL SERVER
# -----------------------------
def cargar_datos(datos_transformados, cadena_conexion):
    registros = {}
    try:
        with pyodbc.connect(cadena_conexion) as conn:
            # Limpiar tablas en orden respetando FK
            for tabla in ['Opiniones', 'Fuentes', 'Clientes', 'Productos']:
                limpiar_tabla(tabla, conn)

            # Insertar datos
            for tabla in ['Productos', 'Clientes', 'Fuentes', 'Opiniones']:
              df = datos_transformados.get(tabla, pd.DataFrame())
              if df.empty:
                 print(f" DataFrame para '{tabla}' está vacío. No hay registros para cargar.")
                 registros[tabla] = 0
              else:
                 
                df = df.astype(object).where(pd.notna(df), None)

                columnas = ", ".join(df.columns)
                placeholders = ", ".join(["?"] * len(df.columns))
                query = f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})"
                cursor = conn.cursor()
                for row in df.itertuples(index=False, name=None):
                  cursor.execute(query, row)
                conn.commit()
                cursor.close()
                registros[tabla] = len(df)
                print(f" Carga en '{tabla}': {len(df)} registros.")

    except Exception as e:
        print(f" Error general en cargar_datos: {e}")

    return registros

