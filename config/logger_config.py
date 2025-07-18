import logging
import sys
import codecs # Importamos la librería de codecs

def setup_logger():
    """Configura un logger profesional para la aplicación."""
    logger = logging.getLogger("QFC")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- LA CORRECCIÓN UNIVERSAL ESTÁ AQUÍ ---
    # En lugar de reconfigurar el handler, envolvemos el stream de salida (sys.stdout)
    # con un escritor que fuerza la codificación UTF-8.
    # Esto funciona en todas las versiones de Python.
    
    # Usamos un 'backslashreplace' para que, si un carácter es realmente imposible de mostrar,
    # no rompa el programa, sino que lo reemplace.
    utf8_writer = codecs.getwriter('utf-8')(sys.stdout.buffer, 'backslashreplace')
    
    stream_handler = logging.StreamHandler(utf8_writer)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # ----------------------------------------

    # (Opcional) Handler para un archivo, que ya es compatible
    # try:
    #     file_handler = logging.FileHandler("qfc_app.log", mode='a', encoding='utf-8')
    #     file_handler.setFormatter(formatter)
    #     logger.addHandler(file_handler)
    # except Exception as e:
    #     logger.warning(f"No se pudo crear el archivo de log: {e}")

    return logger

log = setup_logger()