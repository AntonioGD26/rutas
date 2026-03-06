# Usa una imagen oficial de Python como base
FROM python:3.10-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia primero el archivo de dependencias para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación al contenedor
COPY . .

# Expone el puerto en el que Streamlit se ejecutará (por defecto 8501)
EXPOSE 8501

# Comando para ejecutar la aplicación
# Ajusta "main.py" si tu archivo principal tiene otro nombre
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]