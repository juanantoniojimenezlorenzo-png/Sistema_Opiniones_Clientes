import os
from funciones_etl import extraer_datos, transformar_y_validar, cargar_datos
import pyodbc
import pandas as pd


def ejecutar_pipeline():
    """Función principal para coordinar la ejecución completa del Proceso ETL."""

    # ------------------------------------------------------------------
    # CONEXIÓN A SQL SERVER EXPRESS 
    # ------------------------------------------------------------------
    CONFIG_SQL = {
        'driver': '{ODBC Driver 17 for SQL Server}',  
        'servidor': r'LAPTOP-3H52QU1M\SQLEXPRESS',    
        'base_datos': 'OpinionesClientes',
        'trusted_connection': 'yes'  
    }

    # Cadena de conexión
    CADENA_CONEXION = (
        f"DRIVER={CONFIG_SQL['driver']};"
        f"SERVER={CONFIG_SQL['servidor']};"
        f"DATABASE={CONFIG_SQL['base_datos']};"
        f"Trusted_Connection={CONFIG_SQL['trusted_connection']};"
    )

    # Rutas absolutas
    RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
    rutas_archivos = {
        'clients': os.path.join(RUTA_BASE, 'data', 'clients.csv'),
        'products': os.path.join(RUTA_BASE, 'data', 'products.csv'),
        'fuente_datos': os.path.join(RUTA_BASE, 'data', 'fuente_datos.csv'),
        'social_comments': os.path.join(RUTA_BASE, 'data', 'social_comments.csv'),
        'surveys': os.path.join(RUTA_BASE, 'data', 'surveys_part1.csv'),
        'web_reviews': os.path.join(RUTA_BASE, 'data', 'web_reviews.csv')
    }
    os.makedirs(os.path.join(RUTA_BASE, 'data'), exist_ok=True)

    print("--- Iniciando Proceso ETL para SQL Server ---")

    # 1. Extracción de Datos
    datos_crudos = extraer_datos(rutas_archivos)

    # 2. Transformación y Validación
    datos_transformados = transformar_y_validar(datos_crudos)

    # Vista previa de Opiniones antes de cargar
    if 'Opiniones' in datos_transformados:
        print("\nVista previa de Opiniones transformadas:")
        print(datos_transformados['Opiniones'].head())
        print("Cantidad de registros Opiniones:",
              len(datos_transformados['Opiniones']))
    else:
        print("No existe la clave 'Opiniones' en datos_transformados")

    # 3. Carga de Datos en SQL Server
    registros = cargar_datos(datos_transformados, CADENA_CONEXION)

    # 4. Resumen
    print("\n--- Resumen de la Carga de Registros ---")
    for tabla, count in registros.items():
        print(f"Tabla {tabla}: {count} filas cargadas.")

    print("\n--- El proceso ETL ha finalizado exitosamente. ---")

    # Preview opcional de Opiniones
    if 'Opiniones' in registros and registros['Opiniones'] > 0:
        try:
            with pyodbc.connect(CADENA_CONEXION) as conn:
                print("\n--- Resultado (SELECT TOP 5 de la tabla Opiniones) ---")
                df_preview = pd.read_sql("SELECT TOP 5 * FROM Opiniones", conn)
                print(df_preview.to_markdown(index=False))
        except Exception as e:
            print(f"No se pudo mostrar el preview: {e}")


if __name__ == "__main__":
    ejecutar_pipeline()
